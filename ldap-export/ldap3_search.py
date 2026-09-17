from ldap3 import Server, Connection, ALL, NTLM
from dotenv import load_dotenv
import os

load_dotenv()
user = os.environ['LDAP_USER']
password = os.environ['LDAP_PASS']

server = Server('ldap://192.168.254.10',get_info=ALL)

conn = Connection(
    server,
    user=user,
    password=password,
    authentication=NTLM,
    auto_bind=True
)

conn.search(
    search_base='DC=qy,DC=net',
    search_filter='(objectClass=user)',
    attributes=['sAMAccountName', 'displayName', 'distinguishedName', 'mail']
)

for entry in conn.entries:
    # print(entry.distinguishedName)
    # print('  登录名:', entry.sAMAccountName)
    # print('  显示名:', entry.displayName)
    print(entry)
