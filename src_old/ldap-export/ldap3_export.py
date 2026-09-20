#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ldap3_export.py — 全量导出 OU=Organization 下的用户与计算机

用法:
    python ldap3_export.py                 # 默认导出 xlsx
    python ldap3_export.py --format all    # 导出 xlsx + csv + json
    python ldap3_export.py --format csv
    python ldap3_export.py --all-attrs     # 导出对象上的全部属性(列会非常多)

依赖:
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conn.ldap3_conn import get_connection, get_inspection_settings, get_ldap_settings

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    sys.exit("[!] 缺少依赖 openpyxl，请先执行: pip install -r requirements.txt")

# ---------------------------------------------------------------- 配置

SEARCH_SCOPE = "SUBTREE"

OUTPUT_STEM = "ldap_export_organization"

# 分页大小。AD 默认 MaxPageSize 通常为 1000，超过会被静默截断，
# 因此统一走 paged_search。
PAGE_SIZE = 500

# AD 中代表“永不过期”的极值时间戳(1601-01-01 / 9999-12-31)
# 注意: AD 返回的极大值带 999999 微秒, 不能用精确相等去比。
_AD_EPOCH_DATE = (1601, 1, 1)
_NEVER_EXPIRES_YEAR = 9999

# userAccountControl 位标志 (MS-ADTS)
UAC_FLAGS = [
    # 账户类型位（0x1 ~ 0x2000）
    (0x0001, "SCRIPT"), # [暂无作用] 登录脚本会执行。AD 的 LDAP 提供程序读写都不生效，属于历史遗留
    (0x0002, "ACCOUNTDISABLE"), # 账户是否处于禁用状态
    (0x0008, "HOMEDIR_REQUIRED"), # [暂无作用] 需要主目录（旧式 LAN Manager 遗留）
    (0x0010, "LOCKOUT"), # 账户是否被锁定
    (0x0020, "PASSWD_NOTREQD"), # 账户是否不需要密码
    (0x0040, "PASSWD_CANT_CHANGE"), # 用户不允许修改密码
    (0x0080, "ENCRYPTED_TEXT_PWD_ALLOWED"), # [暂无作用] 允许发送加密密码（历史遗留）
    (0x0100, "TEMP_DUPLICATE_ACCOUNT"), # [暂无作用] 主账户在别的域，这是本地账户。NT4 时代概念，现代 AD 基本不用
    (0x0200, "NORMAL_ACCOUNT"), # 普通用户账户（所有正常用户都有这一位）

    # 密码策略位（0x10000 起）
    (0x0800, "INTERDOMAIN_TRUST_ACCOUNT"), # 域间信任账户（信任另一个域的域控）
    (0x1000, "WORKSTATION_TRUST_ACCOUNT"), # 计算机账户（加入域的成员机/服务器）
    (0x2000, "SERVER_TRUST_ACCOUNT"), # 域控账户（BDC）
    (0x10000, "DONT_EXPIRE_PASSWORD"), # 账户密码是否永不过期
    (0x20000, "MNS_LOGON_ACCOUNT"), # 多数节点集（MNS）登录账户，用于无共享磁盘的集群
    (0x40000, "SMARTCARD_REQUIRED"), # 强制用智能卡登录
    (0x80000, "TRUSTED_FOR_DELEGATION"), # 允许 Kerberos 无约束委派
    (0x100000, "NOT_DELEGATED"), # 禁止委派
    (0x200000, "USE_DES_KEY_ONLY"), # 只允许 DES 加密，弱加密，应禁用
    (0x400000, "DONT_REQ_PREAUTH"), # 不需要 Kerberos 预认证——可被离线暴力破解（AS-REP Roasting 攻击）。高危
    (0x800000, "PASSWORD_EXPIRED"), # 密码是否过期
    (0x1000000, "TRUSTED_TO_AUTH_FOR_DELEGATION"), # 协议转换委派（Constrained Delegation）。微软明确标注"安全敏感，必须严格控制"
]

# sAMAccountType 取值。来源: [MS-SAMR] 2.2.1.9 ACCOUNT_TYPE Values
# https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/e742be45-665d-4576-b872-0bc99d1e1fbe
# 注意: 这是"账户类型"，与组作用域(groupType)是两回事，不要混淆。
SAM_TYPE = {
    0x00000000: "域对象",
    0x10000000: "安全组",
    0x10000001: "非安全组(分发组)",
    0x20000000: "别名对象(域本地组)",
    0x20000001: "非安全别名对象",
    0x30000000: "用户账户",
    0x30000001: "计算机账户",
    0x30000002: "信任账户",
    0x40000000: "应用基本组",
    0x40000001: "应用查询组",
}


# ---------------------------------------------------------------- 工具函数

def ad_timestamp_to_str(value):
    """把 AD 的 FILETIME / datetime 转换成可读字符串。"""
    if value is None:
        return ""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # 9999-12-31 = 永不过期 (AD 返回带 999999 微秒, 用年份判断)
        if dt.year >= _NEVER_EXPIRES_YEAR:
            return "永不过期"
        # 1601-01-01 = 从未发生过 (lastLogon 等)
        if dt.year <= _AD_EPOCH_DATE[0]:
            return "从未"
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

    # 某些情况下 ldap3 会返回原始 FILETIME 整数
    if isinstance(value, int):
        if value == 0:
            return "从未"
        if value >= 0x7FFFFFFFFFFFFFFF:
            return "永不过期"
        try:
            dt = datetime(1601, 1, 1, tzinfo=timezone.utc) + \
                timedelta(microseconds=value / 10)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(value)
    return str(value)


def decode_uac(value):
    """把 userAccountControl 整数解码成易读标志串。"""
    if value is None or value == "":
        return ""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    names = [name for bit, name in UAC_FLAGS if n & bit]
    return f"{n} ({', '.join(names)})" if names else str(n)


def normalize_value(attr_name, value):
    """把任意 LDAP 值转成适合放进单元格的字符串。"""
    if value is None:
        return ""
    # 二进制属性(如 objectGUID / msExchMailboxSecurityDescriptor)
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex().upper()

    if isinstance(value, datetime):
        return ad_timestamp_to_str(value)

    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    if isinstance(value, (list, tuple, set)):
        return "; ".join(normalize_value(attr_name, v) for v in value)

    s = str(value)
    # 时间类属性统一格式化
    if attr_name in {
        "whenCreated", "whenChanged", "pwdLastSet", "lastLogon",
        "lastLogonTimestamp", "lastLogoff", "accountExpires",
        "badPasswordTime", "lockoutTime", "msExchWhenMailboxCreated",
    }:
        try:
            return ad_timestamp_to_str(value)
        except Exception:
            pass
    if attr_name == "userAccountControl":
        return decode_uac(value)
    if attr_name == "sAMAccountType":
        # 该属性只出现在账户对象上，取值见 SAM_TYPE
        try:
            n = int(value)
        except (TypeError, ValueError):
            return s
        return f"{s} ({SAM_TYPE.get(n, '未知类型')})"
    return s


# ---------------------------------------------------------------- 导出写入器

def write_xlsx(path, sheets):
    """写出 xlsx。sheets: list of (sheet_name, rows)，rows[0] 为表头。"""
    wb = Workbook()
    wb.remove(wb.active)
    header_font = Font(bold=True, color="FFFFFFFF")
    header_fill = PatternFill("solid", fgColor="FF4472C4")

    for name, rows in sheets:
        ws = wb.create_sheet(title=name[:31])
        for row in rows:
            ws.append(row)
        if not rows:
            continue
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
        ws.freeze_panes = "A2"
        for idx, col in enumerate(ws.columns, start=1):
            width = max(
                (len(str(c.value)) for c in col if c.value is not None),
                default=8,
            )
            ws.column_dimensions[get_column_letter(idx)].width = min(max(width + 2, 10), 50)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=False)

    wb.save(path)


def write_csv(path, header, rows):
    # utf-8-sig 让 Excel 双击打开时正确识别中文
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h, "") for h in header])


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- 主流程

# 关注度高、优先展示的列(放在最前面)
PREFERRED_FIRST = [
    "distinguishedName", "name", "cn",
    "sAMAccountName", "userPrincipalName", "displayName",
    "objectClass", "objectCategory",
]

# 对导出来说没意义的属性(不展示)
SKIP_ATTRS = {
    "dSCorePropagationData", "instanceType", "codePage", "countryCode",
    "uSNCreated", "uSNChanged", "showInAddressList", "mDBUseDefaults",
    "msExchMailboxSecurityDescriptor", "msExchMailboxGuid",
    "msExchTextMessagingState", "msExchPoliciesIncluded",
    "msExchVersion", "msExchRecipientDisplayType",
    "msExchELCMailboxFlags", "objectGUID", "objectSid",
    "servicePrincipalName", "proxyAddresses", "msExchUMDtmfMap",
}


def search_paged(conn, base, filt, page_size=PAGE_SIZE):
    """分页搜索，避免超过服务端 MaxPageSize 被静默截断。

    返回 list[dict]: {'dn': str, 'attributes': {name: value}}
    """
    results = conn.extend.standard.paged_search(
        search_base=base,
        search_filter=filt,
        search_scope=SEARCH_SCOPE,
        attributes=["*"],
        paged_size=page_size,
        generator=False,
    )
    out = []
    for r in results:
        # paged_search 在 generator=False 时仍可能带回 searchResRef 条目
        if r.get("type") != "searchResEntry":
            continue
        out.append({"dn": r.get("dn", ""),
                    "attributes": r.get("attributes", {})})
    return out


def collect_attrs(records, all_attrs=False):
    """收集所有出现过的属性名，排出列顺序。records 为 search_paged 的返回。"""
    seen = []
    seen_set = set()
    for rec in records:
        for a in rec["attributes"]:
            if a in seen_set:
                continue
            if not all_attrs and a in SKIP_ATTRS:
                continue
            seen_set.add(a)
            seen.append(a)

    ordered = [a for a in PREFERRED_FIRST if a in seen_set]
    rest = sorted(a for a in seen if a not in ordered)
    return ordered + rest


def record_to_row(rec, attr_order):
    """把一条分页搜索结果转成 dict，按 attr_order 取值。"""
    attrs = rec["attributes"]
    return {a: normalize_value(a, attrs.get(a)) for a in attr_order}


def main():
    ap = argparse.ArgumentParser(description="导出 OU=Organization 下的用户与计算机")
    ap.add_argument("--format", default="xlsx",
                    choices=["xlsx", "csv", "json", "all"],
                    help="导出格式(默认 xlsx)")
    ap.add_argument("--all-attrs", action="store_true",
                    help="导出对象上的全部属性(默认会过滤掉一批技术性属性)")
    ap.add_argument("--outdir", default=".", help="输出目录")
    ap.add_argument("--ou", default=None, help="目标 OU 名(默认读取 config.yaml)")
    args = ap.parse_args()

    load_dotenv()
    ldap_settings = get_ldap_settings()
    inspection_settings = get_inspection_settings()
    try:
        user = os.environ["LDAP_USER"]
        password = os.environ["LDAP_PASS"]
    except KeyError as e:
        sys.exit(f"[!] .env 缺少变量: {e}")

    base_dn = ldap_settings["base_dn"]
    target_ou = args.ou or inspection_settings.get("target_ou", "Organization")
    ou_dn = f"OU={target_ou},{base_dn}"

    print(f"[*] 连接 DC {ldap_settings['host']} ...")
    conn = get_connection()
    print(f"[+] 绑定成功 (bound={conn.bound})")

    # 用户: objectCategory=person 可以排除计算机(计算机也是 user 的子类)
    USER_FILTER = "(&(objectClass=user)(objectCategory=person))"
    COMPUTER_FILTER = "(objectClass=computer)"

    sets = []
    for label, filt in (("用户", USER_FILTER), ("计算机", COMPUTER_FILTER)):
        records = search_paged(conn, ou_dn, filt, int(inspection_settings.get("page_size", PAGE_SIZE)))
        print(f"[+] {label}: {len(records)} 条")
        sets.append((label, filt, records))

    all_records = [r for _, _, rs in sets for r in rs]
    if not all_records:
        print("[!] 没有查到任何对象，请检查 OU 名称与权限")
        conn.unbind()
        return

    rows_by_label = {}
    for label, _, records in sets:
        attrs = collect_attrs(records, args.all_attrs)
        rows_by_label[label] = (attrs, [record_to_row(r, attrs) for r in records])

    os.makedirs(args.outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []

    def build_sheets():
        sheets = []
        # 汇总页
        summary = [["对象类型", "数量", "搜索基准", "过滤器"]]
        for label, filt, records in sets:
            summary.append([label, len(records), ou_dn, filt])
        summary.append(["合计", len(all_records), "", ""])
        sheets.append(("汇总", summary))
        for label, _, _ in sets:
            attrs, rows = rows_by_label[label]
            sheets.append((label, [attrs] + [[r.get(a, "") for a in attrs] for r in rows]))
        return sheets

    if args.format in ("xlsx", "all"):
        path = os.path.join(args.outdir, f"{inspection_settings.get('output_stem', OUTPUT_STEM)}_{stamp}.xlsx")
        write_xlsx(path, build_sheets())
        written.append((path, "xlsx"))

    if args.format in ("csv", "all"):
        for label, _, _ in sets:
            attrs, rows = rows_by_label[label]
            path = os.path.join(args.outdir, f"{inspection_settings.get('output_stem', OUTPUT_STEM)}_{label}_{stamp}.csv")
            write_csv(path, attrs, rows)
            written.append((path, "csv"))

    if args.format in ("json", "all"):
        payload = {
            "exported_at": datetime.now().isoformat(),
            "dc": ldap_settings["host"],
            "search_base": ou_dn,
            "counts": {label: len(records) for label, _, records in sets},
            "objects": {
                label: rows_by_label[label][1]
                for label, _, _ in sets
            },
        }
        path = os.path.join(args.outdir, f"{inspection_settings.get('output_stem', OUTPUT_STEM)}_{stamp}.json")
        write_json(path, payload)
        written.append((path, "json"))

    print("\n[+] 导出完成:")
    for p, kind in written:
        size = os.path.getsize(p)
        print(f"    {p}  ({kind}, {size:,} bytes)")

    # 控制台预览
    for label, _, _ in sets:
        attrs, rows = rows_by_label[label]
        print(f"\n--- {label} ({len(rows)}) 可用属性 {len(attrs)} 个 ---")
        for r in rows:
            print(f"    {r.get('sAMAccountName', '?')}  |  {r.get('distinguishedName', '')}")

    conn.unbind()
    print("\n[+] 连接已关闭")


if __name__ == "__main__":
    main()
