import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conn.ldap3_conn import get_connection, get_ldap_settings

settings = get_ldap_settings()
conn = get_connection()

conn.search(
    search_base=settings['base_dn'],
    search_filter='(objectClass=user)',
    attributes=['sAMAccountName', 'displayName', 'distinguishedName', 'mail']
)

for entry in conn.entries:
    # print(entry.distinguishedName)
    # print('  登录名:', entry.sAMAccountName)
    # print('  显示名:', entry.displayName)
    print(entry)
