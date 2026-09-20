import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conn.ldap3_conn import get_connection, get_ldap_settings

BASE = get_ldap_settings()['base_dn']
conn = get_connection()

conn.search(
    search_base=f'CN=Policies,CN=System,{BASE}',
    search_filter='(displayName=Policy-User)',
    attributes=['displayName', 'distinguishedName', 'gPCFileSysPath', 'gPCFunctionalityVersion', 'flags']
)

for entry in conn.entries:
    print(entry)
