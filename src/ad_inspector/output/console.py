from __future__ import annotations

from ..findings import summarize
from ..models import Finding


def print_findings(findings: list[Finding]) -> None:
    counts = summarize(findings)
    print("巡检结果:", ", ".join(f"{key}={value}" for key, value in counts.items()) or "无风险")
    for item in findings:
        print(f"[{item.severity}] {item.check_id} {item.title} | {item.account_name} | {item.target_dn}")
        if item.recommendation:
            print(f"  建议: {item.recommendation}")

