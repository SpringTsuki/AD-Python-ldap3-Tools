from __future__ import annotations

from typing import Any

from ..models import Finding
from ..search import paged_search

UAC_DONT_EXPIRE_PASSWORD = 0x10000
UAC_PASSWD_NOTREQD = 0x20
UAC_DONT_REQ_PREAUTH = 0x400000


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def check_account_flags(conn, base_dn: str, page_size: int = 500) -> list[Finding]:
    """Initial read-only account checks based on userAccountControl."""
    records = paged_search(
        conn,
        base_dn,
        "(&(objectCategory=person)(objectClass=user))",
        ["sAMAccountName", "displayName", "distinguishedName", "userAccountControl"],
        page_size,
    )
    findings: list[Finding] = []
    for record in records:
        attrs = record["attributes"]
        flags = _int(attrs.get("userAccountControl"))
        name = str(attrs.get("sAMAccountName", ""))
        dn = record["dn"]
        common = {"target_dn": dn, "account_name": name,
                  "evidence": {"userAccountControl": flags}}
        if flags & UAC_DONT_EXPIRE_PASSWORD:
            findings.append(Finding("ACC-001", "MEDIUM", "密码永不过期账户",
                                    recommendation="复核是否为必要的服务账户", **common))
        if flags & UAC_PASSWD_NOTREQD:
            findings.append(Finding("ACC-002", "HIGH", "账户不要求密码",
                                    recommendation="禁止空密码或不要求密码的账户", **common))
        if flags & UAC_DONT_REQ_PREAUTH:
            findings.append(Finding("ACC-003", "HIGH", "账户不要求 Kerberos 预认证",
                                    recommendation="启用 Kerberos 预认证并复核 AS-REP 风险", **common))
    return findings

