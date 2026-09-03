#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 多 Sheet 去重工具（执行型）

读取 Excel，从日志列提取指定字段（复用 excel_extract_log_fields 的
「JSON 优先 + 双风格正则兜底 + 截断兜底」策略，保留原始所有列并追加提取列），
然后按指定列分别去重（保留首条），每列生成一个独立 Sheet。

输出 Sheet 结构：
    - 全量数据     ：原始所有列 + 提取列（不去重）
    - <列名>去重   ：按该列去重保留首条（每个 --dedup-cols 列一个 Sheet）

与 excel_split_by_deviceaddress.py 的区别：那个按字段值分组、每个值一个 Sheet；
本脚本按列去重只留每个值的首条，适合「看有哪些不同的事件/类型」。

命令行用法：
    python excel_dedup_sheets.py <输入文件> <输出文件> \
        [--log-column 原始日志] [--fields f1,f2,...] [--dedup-cols col1,col2]

    --log-column ：日志所在列名，默认 原始日志
    --fields     ：要从日志列提取的字段，逗号分隔，默认 log_msg
    --dedup-cols ：要按其去重的列（可多个），逗号分隔，每个列生成一个去重 Sheet
"""

import argparse
import sys

import pandas as pd

# 复用同目录主提取脚本的逻辑（JSON 优先 + JSON/kv 双风格正则 + 截断兜底）
from excel_extract_log_fields import (
    build_field_patterns,
    _clean_for_excel,
    extract_fields_from_log,
)

DEFAULT_FIELDS = ["log_msg"]


def process(input_path, output_path, log_column, target_fields, dedup_cols):
    print(f"📂 读取文件: {input_path}")
    df = pd.read_excel(input_path)

    if log_column not in df.columns:
        raise ValueError(f"❌ 未找到列 '{log_column}'，可用列: {list(df.columns)}")

    # 1. 从日志列提取字段（已存在的同名列会被跳过，避免重复提取）
    todo_fields = [f for f in target_fields if f not in df.columns]
    skipped = [f for f in target_fields if f in df.columns]
    if skipped:
        print(f"⏭️ 字段已存在，跳过提取: {skipped}")

    if todo_fields:
        print(f"🔍 共 {len(df)} 条记录，从 '{log_column}' 提取字段 {todo_fields}...")
        field_patterns = build_field_patterns(todo_fields)
        extracted = df[log_column].apply(
            lambda s: extract_fields_from_log(s, todo_fields, field_patterns)
        )
        extracted_df = pd.DataFrame(extracted.tolist())
        for col in extracted_df.columns:
            extracted_df[col] = extracted_df[col].apply(_clean_for_excel)
        if "_diag" in extracted_df.columns:
            print("📊 提取诊断统计:")
            for k, v in extracted_df["_diag"].value_counts().items():
                print(f"   {k}: {v}")
            if (extracted_df["_diag"] == "TRUNCATED_TAIL").any():
                print("   ⚠️ TRUNCATED_TAIL = 源文件被 Excel 32767 字符上限截断，该行提取值不完整")
        extracted_df.drop(columns=["_diag"], inplace=True, errors="ignore")
        df = pd.concat([df, extracted_df], axis=1)
        for field in todo_fields:
            non_empty = (df[field].fillna("") != "").sum()
            print(f"   - {field}: {non_empty}/{len(df)} 条有值")
    else:
        print("🔍 无需提取字段（全部已存在）")

    # 2. 校验去重列
    for col in dedup_cols:
        if col not in df.columns:
            raise ValueError(f"❌ 未找到去重列 '{col}'，可用列: {list(df.columns)}")

    # 3. 写多 Sheet
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="全量数据", index=False)
        print(f"📝 Sheet '全量数据': {len(df)} 行, {len(df.columns)} 列")

        for col in dedup_cols:
            dedup_df = df.drop_duplicates(subset=[col], keep="first")
            dedup_df.to_excel(writer, sheet_name=f"{col}去重", index=False)
            n_unique = dedup_df[col].nunique(dropna=True)
            n_null = int(dedup_df[col].isna().sum())
            print(f"📝 Sheet '{col}去重': {len(dedup_df)} 行 "
                  f"(唯一值 {n_unique} 个, 空值行保留 {n_null} 条)")

    print(f"✅ 完成! 输出: {output_path}")


def main():
    p = argparse.ArgumentParser(description="提取日志字段 + 按指定列去重拆多 Sheet")
    p.add_argument("input", help="输入 Excel 文件")
    p.add_argument("output", help="输出 Excel 文件")
    p.add_argument("--log-column", default="原始日志", help="日志列名，默认 原始日志")
    p.add_argument("--fields", default=",".join(DEFAULT_FIELDS),
                   help=f"要提取的日志字段，逗号分隔，默认 {','.join(DEFAULT_FIELDS)}")
    p.add_argument("--dedup-cols", required=True,
                   help="要按其去重的列，逗号分隔，每个列一个去重 Sheet")
    args = p.parse_args(sys.argv[1:])

    target_fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    dedup_cols = [c.strip() for c in args.dedup_cols.split(",") if c.strip()]
    if not dedup_cols:
        raise SystemExit("❌ --dedup-cols 不能为空")

    process(args.input, args.output, args.log_column, target_fields, dedup_cols)


if __name__ == "__main__":
    main()
