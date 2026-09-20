from __future__ import annotations

from typing import Any

from ldap3 import SUBTREE


def paged_search(conn, base: str, ldap_filter: str, attributes: list[str] | str = "*",
                 page_size: int = 500) -> list[dict[str, Any]]:
    results = conn.extend.standard.paged_search(
        search_base=base,
        search_filter=ldap_filter,
        search_scope=SUBTREE,
        attributes=attributes,
        paged_size=page_size,
        generator=False,
    )
    return [
        {"dn": item.get("dn", ""), "attributes": item.get("attributes", {})}
        for item in results
        if item.get("type") == "searchResEntry"
    ]

