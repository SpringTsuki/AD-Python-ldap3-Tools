from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    ldap = config.get("ldap")
    if not isinstance(ldap, dict) or not ldap.get("host") or not ldap.get("base_dn"):
        raise ValueError("config.yaml 必须包含 ldap.host 和 ldap.base_dn")
    return config


def load_credentials() -> tuple[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        return os.environ["LDAP_USER"], os.environ["LDAP_PASS"]
    except KeyError as exc:
        raise RuntimeError(f".env 缺少变量: {exc.args[0]}") from exc

