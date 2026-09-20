"""Shared Active Directory configuration and connection helpers."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv
from ldap3 import ALL, NTLM, Connection, Server

# src_old/conn/ldap3_conn.py -> project root is two levels above src_old.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    settings = config.get("ldap")
    if not isinstance(settings, dict) or not settings.get("host") or not settings.get("base_dn"):
        raise ValueError("config.yaml 必须包含 ldap.host 和 ldap.base_dn")
    return config

def get_connection(config: dict[str, Any] | None = None) -> Connection:
    load_dotenv(PROJECT_ROOT / ".env")
    config = config or load_config()
    settings = config["ldap"]
    try:
        user = os.environ["LDAP_USER"]
        password = os.environ["LDAP_PASS"]
    except KeyError as exc:
        raise RuntimeError(f".env 缺少变量: {exc.args[0]}") from exc
    use_ssl = bool(settings.get("use_ssl", False))
    port = int(settings.get("port") or (636 if use_ssl else 389))
    scheme = "ldaps" if use_ssl else "ldap"
    server = Server(f"{scheme}://{settings['host']}:{port}", get_info=ALL,
                    connect_timeout=int(settings.get("connect_timeout", 10)))
    authentication = str(settings.get("authentication", "ntlm")).lower()
    if authentication != "ntlm":
        raise ValueError(f"暂不支持的认证方式: {authentication}")
    return Connection(server, user=user, password=password, authentication=NTLM,
                      auto_bind=True, receive_timeout=int(settings.get("receive_timeout", 30)))

def get_ldap_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    return (config or load_config())["ldap"]

def get_inspection_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    return (config or load_config()).get("inspection", {})
