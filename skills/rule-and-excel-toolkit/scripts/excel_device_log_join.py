#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 设备清单 × 多份日志按 IP 关联工具（执行型）
读取一份设备清单和多份原始日志 Excel，把日志里的 IP 列与设备清单按 IP 关联，
输出多 Sheet 结果（汇总 / 全量明细 / 每个 IP 一个 Sheet）。

命令行用法：
    python excel_device_log_join.py <设备清单> <输出文件> <日志1> [日志2 ...]
        [--device-ip-col 设备IP] [--device-name-col 设备名称] [--device-vendor-col 设备厂商]
        [--log-ip-col 设备描述] [--log-keep-col 原始保留] [--log-col 原始日志]

    日志表里的 IP 列名（--log-ip-col，默认"设备描述"）会作为关联键，
    关联时重命名为设备 IP 列名（--device-ip-col，默认"设备IP"）。
"""

import argparse
import os
import re
import sys

import pandas as pd


def join_device_logs(
    device_file: str,
    log_files: list,
    output_file: str,
    device_ip_col="设备IP",
    device_name_col="设备名称",
    device_vendor_col="设备厂商",
    log_ip_col="设备描述",
    log_keep_col="原始保留",
    log_col="原始日志",
):
    # 1. 读取设备清单
    print(f"📂 读取设备清单: {device_file}")
    df_device = pd.read_excel(device_file, sheet_name=0)

    need_device_cols = [device_ip_col, device_name_col, device_vendor_col]
    for col in need_device_cols:
        if col not in df_device.columns:
            raise ValueError(f"设备清单缺少列 '{col}'，可用列: {list(df_device.columns)}")

    df_device_map = df_device[need_device_cols].drop_duplicates(subset=[device_ip_col], keep="first")
    print(f"设备清单总记录数: {len(df_device)}，去重后IP数: {len(df_device_map)}")

    # 2. 合并所有原始日志
    df_log_full = pd.DataFrame()
    for file in log_files:
        if os.path.exists(file):
            df_temp = pd.read_excel(file, sheet_name=0)
            df_log_full = pd.concat([df_log_full, df_temp], ignore_index=True)
            print(f"已读取: {file}，共 {len(df_temp)} 条记录")
        else:
            print(f"⚠️  警告: 文件不存在 - {file}")

    print(f"\n原始日志总记录数: {len(df_log_full)}")
    print(f"原始日志表的列: {df_log_full.columns.tolist()}")

    # 检查必需列
    required_log_cols = [log_ip_col, log_keep_col, log_col]
    for col in required_log_cols:
        if col not in df_log_full.columns:
            raise ValueError(f"原始日志表中缺少列 '{col}'，可用列: {list(df_log_full.columns)}")

    # 将日志里的 IP 列重命名为设备 IP 列名，统一关联键
    df_log_full.rename(columns={log_ip_col: device_ip_col}, inplace=True)
    df_log_full = df_log_full[[device_ip_col, log_keep_col, log_col]].copy()

    # 3. 去重（用于汇总sheet）：按 IP 保留非空字段最多的那条
    def is_empty(val):
        return pd.isna(val) or str(val).strip() == ""

    df_log_clean = df_log_full.copy()
    df_log_clean["保留为空"] = df_log_clean[log_keep_col].apply(lambda x: 1 if is_empty(x) else 0)
    df_log_clean["日志为空"] = df_log_clean[log_col].apply(lambda x: 1 if is_empty(x) else 0)

    df_log_dedup = df_log_clean.sort_values(["保留为空", "日志为空"]).drop_duplicates(subset=[device_ip_col], keep="first")
    df_log_dedup = df_log_dedup.drop(columns=["保留为空", "日志为空"])

    print(f"去重前: {len(df_log_full)} 条，去重后: {len(df_log_dedup)} 条")

    final_cols = [device_ip_col, device_name_col, device_vendor_col, log_keep_col, log_col]

    # 4. 汇总表（去重）
    df_summary = pd.merge(df_log_dedup, df_device_map, on=device_ip_col, how="left")
    df_summary = df_summary.sort_values([device_vendor_col, device_name_col], na_position="last")
    df_summary = df_summary[final_cols]

    # 5. 全量明细表（不去重）
    df_full_detail = pd.merge(df_log_full, df_device_map, on=device_ip_col, how="left")
    df_full_detail = df_full_detail.sort_values([device_vendor_col, device_name_col], na_position="last")
    df_full_detail = df_full_detail[final_cols]

    print(f"全量明细: {len(df_full_detail)} 条记录")

    # 6. 写入多 Sheet
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="汇总", index=False)
        print(f"\n已写入汇总表，共 {len(df_summary)} 条记录")

        df_full_detail.to_excel(writer, sheet_name="全量明细", index=False)
        print(f"已写入全量明细表，共 {len(df_full_detail)} 条记录")

        # 所有唯一 IP，按 厂商→名称 排序
        df_temp = pd.merge(
            df_log_full[[device_ip_col]].drop_duplicates(),
            df_device_map,
            on=device_ip_col,
            how="left"
        )
        sorted_ips = df_temp.sort_values([device_vendor_col, device_name_col], na_position="last")[device_ip_col].tolist()
        sorted_ips = [ip for ip in sorted_ips if pd.notna(ip)]

        print(f"\n准备写入 {len(sorted_ips)} 个IP的明细Sheet...")

        for idx, ip in enumerate(sorted_ips, 1):
            df_ip_full = df_log_full[df_log_full[device_ip_col] == ip].copy()
            df_ip_full = pd.merge(df_ip_full, df_device_map, on=device_ip_col, how="left")
            df_ip_full = df_ip_full[final_cols]

            sheet_name = str(ip)
            sheet_name = re.sub(r'[\\/*?:\[\]]', '_', sheet_name)
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:31]

            try:
                df_ip_full.to_excel(writer, sheet_name=sheet_name, index=False)
            except Exception:
                sheet_name = f"IP_{idx}"
                df_ip_full.to_excel(writer, sheet_name=sheet_name, index=False)

            if idx % 20 == 0:
                print(f"已处理 {idx}/{len(sorted_ips)} 个IP...")

    print(f"\n处理完成！输出文件: {output_file}")
    print(f"  - Sheet '汇总': 去重后的汇总数据 ({len(df_summary)} 条)")
    print(f"  - Sheet '全量明细': 所有数据合并，不去重 ({len(df_full_detail)} 条)")
    print(f"  - 其余 Sheet: 每个IP的全量日志明细（共 {len(sorted_ips)} 个Sheet）")


def main():
    p = argparse.ArgumentParser(
        description="设备清单 × 多份日志按 IP 关联，输出多 Sheet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("device_file", help="设备清单 Excel 文件")
    p.add_argument("output", help="输出 Excel 文件")
    p.add_argument("log_files", nargs="+", help="一个或多个原始日志 Excel 文件")
    p.add_argument("--device-ip-col", default="设备IP", help="设备清单中 IP 列名")
    p.add_argument("--device-name-col", default="设备名称", help="设备清单中名称列名")
    p.add_argument("--device-vendor-col", default="设备厂商", help="设备清单中厂商列名")
    p.add_argument("--log-ip-col", default="设备描述", help="日志表中作为 IP 的列名（关联键）")
    p.add_argument("--log-keep-col", default="原始保留", help="日志表中保留列名")
    p.add_argument("--log-col", default="原始日志", help="日志表中日志列名")
    args = p.parse_args(sys.argv[1:])

    try:
        join_device_logs(
            device_file=args.device_file,
            log_files=args.log_files,
            output_file=args.output,
            device_ip_col=args.device_ip_col,
            device_name_col=args.device_name_col,
            device_vendor_col=args.device_vendor_col,
            log_ip_col=args.log_ip_col,
            log_keep_col=args.log_keep_col,
            log_col=args.log_col,
        )
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
