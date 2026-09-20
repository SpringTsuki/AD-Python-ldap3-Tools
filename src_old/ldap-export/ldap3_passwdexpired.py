import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conn.ldap3_conn import get_connection, get_ldap_settings

BASE = get_ldap_settings()['base_dn']
conn = get_connection()

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
