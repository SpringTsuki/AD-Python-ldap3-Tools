from __future__ import annotations

from typing import Any

from ldap3 import ALL, NTLM, Connection, Server

from .config import load_config, load_credentials


def create_connection(config: dict[str, Any] | None = None) -> Connection:
    config = config or load_config()
    settings = config["ldap"]
    user, password = load_credentials()
    use_ssl = bool(settings.get("use_ssl", False))
    port = int(settings.get("port") or (636 if use_ssl else 389))
    scheme = "ldaps" if use_ssl else "ldap"
    server = Server(
        f"{scheme}://{settings['host']}:{port}",
        get_info=ALL,
        connect_timeout=int(settings.get("connect_timeout", 10)),
    )
    if str(settings.get("authentication", "ntlm")).lower() != "ntlm":
        raise ValueError("当前只支持 NTLM 认证")
    return Connection(
        server,
        user=user,
        password=password,
        authentication=NTLM,
        auto_bind=True,
        receive_timeout=int(settings.get("receive_timeout", 30)),
    )

