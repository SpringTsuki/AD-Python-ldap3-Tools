from ldap3 import Server, Connection, ALL, NTLM, MODIFY_REPLACE
import os

# ---------- 连接参数 ----------
DC_IP = '192.168.254.10'
BASE_DN = 'DC=qy,DC=net'
TARGET_OU = 'OU=YourOU,' + BASE_DN   # 改成你实际要放用户的 OU

USER = os.environ['LDAP_USER']       # QYNET\Administrator
PWD  = os.environ['LDAP_PASS']

# ---------- 建立连接（LDAPS） ----------
server = Server(f'ldaps://{DC_IP}', get_info=ALL)
conn = Connection(server, user=USER, password=PWD,
                  authentication=NTLM, auto_bind=True)
print('绑定成功:', conn.bound)

# ---------- 1. 创建用户 ----------
new_cn = 'Test User'
new_dn = f'CN={new_cn},{TARGET_OU}'
sam    = 'testuser01'
upn    = 'testuser01@qy.net'
initial_pwd = 'P@ssw0rd123!'

attrs = {
    'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
    'cn': new_cn,
    'sAMAccountName': sam,
    'userPrincipalName': upn,
    'displayName': new_cn,
    'givenName': 'Test',
    'sn': 'User',
}

conn.add(new_dn, attributes=attrs)
print('创建结果:', conn.result['description'], conn.result['result'])

# ---------- 2. 设置密码 ----------
conn.extend.microsoft.modify_password(new_dn, initial_pwd)
print('设密码结果:', conn.result['description'], conn.result['result'])

# ---------- 3. 启用账户 ----------
conn.modify(new_dn, {'userAccountControl': [(MODIFY_REPLACE, [512])]})
print('启用结果:', conn.result['description'], conn.result['result'])

# ---------- 4. 加入组 ----------
group_dn = 'CN=Domain Admins,CN=Users,' + BASE_DN   # 改成你的目标组
conn.modify(group_dn, {'member': [(MODIFY_REPLACE, [new_dn])]})
print('加组结果:', conn.result['description'], conn.result['result'])

conn.unbind()