from ldap3 import Server, Connection, ALL, NTLM
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
user = os.environ['LDAP_USER']
password = os.environ['LDAP_PASS']

server = Server('ldap://192.168.254.10', get_info=ALL)
conn = Connection(server, user=user, password=password,
                  authentication=NTLM, auto_bind=True)

BASE = 'DC=qy,DC=net'

# ---------- 检查 1：密码永不过期 ----------
conn.search(
    search_base=BASE,
    search_filter='(&(objectClass=user)(objectCategory=person)'
                  '(userAccountControl:1.2.840.113556.1.4.803:=65536))',
    attributes=['sAMAccountName', 'displayName']
)
print(f'密码永不过期账户: {len(conn.entries)}')
for e in conn.entries:
    print(' ', e.sAMAccountName)