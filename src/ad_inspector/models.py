from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


@dataclass(slots=True)
class Finding:
    check_id: str
    severity: Severity
    title: str
    target_dn: str = ""
    account_name: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

