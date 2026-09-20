from __future__ import annotations

from collections import Counter

from .models import Finding


def summarize(findings: list[Finding]) -> dict[str, int]:
    return dict(Counter(item.severity for item in findings))

