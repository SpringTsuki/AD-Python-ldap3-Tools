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
    search_base='CN=Policies,CN=System,DC=qy,DC=net',
    search_filter='(displayName=Policy-User)',
    attributes=['displayName', 'distinguishedName', 'gPCFileSysPath', 'gPCFunctionalityVersion', 'flags']
)

for entry in conn.entries:
    print(entry)
