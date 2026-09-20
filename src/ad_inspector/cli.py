from __future__ import annotations

import argparse

from .checks.accounts import check_account_flags
from .config import load_config
from .connection import create_connection
from .output.console import print_findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Active Directory 只读巡检工具")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="执行巡检")
    check.add_argument("target", choices=["accounts"], help="巡检领域")
    args = parser.parse_args()

    config = load_config()
    ldap = config["ldap"]
    inspection = config.get("inspection", {})
    conn = create_connection(config)
    try:
        if args.target == "accounts":
            findings = check_account_flags(
                conn,
                ldap["base_dn"],
                int(inspection.get("page_size", 500)),
            )
            print_findings(findings)
    finally:
        if conn.bound:
            conn.unbind()


if __name__ == "__main__":
    main()

