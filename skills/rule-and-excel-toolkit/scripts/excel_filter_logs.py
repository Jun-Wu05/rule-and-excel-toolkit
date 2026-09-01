#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 日志关键词筛选工具（执行型）
从 Excel 中筛选"指定列"包含"指定关键词"的行，输出到新 Excel。

命令行用法：
    python excel_filter_logs.py <输入文件> [输出文件] [--keyword 关键词] [--column 列名]

    --keyword：要筛选的关键词，默认 alarmExtendFieldsStrategyName
    --column：要筛选的列名，默认 原始日志
"""

import argparse
import os
import sys

import pandas as pd


def filter_alarm_logs(input_file: str, output_file: str, keyword: str, target_col: str):
    """
    从Excel中筛选指定列包含指定关键词的行。
    """
    print(f"📂 正在读取文件: {input_file}")
    df = pd.read_excel(input_file, dtype=str)

    if target_col not in df.columns:
        available_cols = list(df.columns)
        raise ValueError(
            f"❌ 未找到列 '{target_col}'！\n"
            f"   可用列名: {available_cols}\n"
            f"   请检查Excel表头是否完全匹配（注意空格/全角字符）"
        )

    mask = (
        df[target_col]
        .fillna("")
        .astype(str)
        .str.contains(keyword, na=False, regex=False)
    )

    filtered_df = df[mask]

    print(f"✅ 筛选完成: 共 {len(df)} 行，符合条件 {len(filtered_df)} 行")

    if len(filtered_df) == 0:
        print("⚠️  没有找到匹配数据，仍将生成空结果文件")

    filtered_df.to_excel(output_file, index=False)
    print(f"💾 结果已保存至: {output_file}")

    return filtered_df


def main():
    p = argparse.ArgumentParser(description="按关键词筛选 Excel 日志行")
    p.add_argument("input", help="输入 Excel 文件")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _筛选")
    p.add_argument("--keyword", default="alarmExtendFieldsStrategyName", help="筛选关键词")
    p.add_argument("--column", default="原始日志", help="被筛选的列名")
    args = p.parse_args(sys.argv[1:])

    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_筛选{ext or '.xlsx'}"

    try:
        result = filter_alarm_logs(args.input, output_path, args.keyword, args.column)

        if not result.empty and args.column in result.columns:
            print("\n--- 前3条匹配数据预览 ---")
            for i, val in enumerate(result[args.column].head(3)):
                preview = str(val)[:200].replace("\n", "\\n")
                print(f"[{i+1}] {preview}...")

    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
