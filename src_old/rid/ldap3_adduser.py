from ldap3 import MODIFY_REPLACE
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conn.ldap3_conn import get_connection, get_inspection_settings, get_ldap_settings

# ---------- 连接参数 ----------
BASE_DN = get_ldap_settings()['base_dn']
TARGET_OU = 'OU=' + get_inspection_settings().get('target_ou', 'YourOU') + ',' + BASE_DN

# ---------- 建立连接（LDAPS） ----------
conn = get_connection()
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
