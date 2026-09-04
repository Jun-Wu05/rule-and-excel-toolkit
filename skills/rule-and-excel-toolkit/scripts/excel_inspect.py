#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 日志预检工具（执行型，只读不写）

跑提取/去重/拆分类脚本之前先「看一眼数据」：行列数、列名、日志格式识别、
目标字段出现率、Excel 32767 字符截断风险、空日志行数。把手工临时检查标准化。

命令行用法：
    python excel_inspect.py <输入文件> [--log-column 原始日志] [--fields f1,f2,...] [--sample N]

    --log-column：日志所在列名，默认 原始日志
    --fields    ：关心的字段，逗号分隔（用于统计出现率/非空率），默认 node_ip,node_name,log_msg
    --sample    ：格式识别抽样行数，默认 200（全量逐行识别大文件时较慢）
"""

import argparse
import json
import re
import sys

import pandas as pd

LOG_COLUMN = "原始日志"
DEFAULT_FIELDS = ["node_ip", "node_name", "log_msg"]
DEFAULT_SAMPLE = 200
# Excel 单元格字符上限；接近即视为截断风险
EXCEL_CELL_LIMIT = 32767
TRUNCATION_RISK_THRESHOLD = 32000


def detect_log_format(log_str):
    """识别单条日志的格式: json / kv / mixed / empty / unknown"""
    if not isinstance(log_str, str) or not log_str.strip():
        return "empty"
    start = log_str.find('{')
    end = log_str.rfind('}') + 1
    if start != -1 and end > start:
        try:
            data = json.loads(log_str[start:end])
            if isinstance(data, dict):
                return "json"
        except json.JSONDecodeError:
            pass
    # kv 风格: 带引号 key="value" 至少 1 个，或不带引号 key=value 出现 3 次以上
    # （syslog 风格日志常只有个别键带引号，如 GenTime="..." SrcIP= DstIP=）
    kv_quoted = len(re.findall(r'[A-Za-z_][A-Za-z0-9_]*="', log_str))
    kv_plain = len(re.findall(r'[A-Za-z_][A-Za-z0-9_]*=(?!=)', log_str))
    if kv_quoted >= 1 or kv_plain >= 3:
        return "kv"
    return "unknown"


def inspect(input_path, log_column, fields, sample_n):
    print(f"📂 读取文件: {input_path}")
    xl = pd.ExcelFile(input_path)
    print(f"📋 Sheet 列表: {xl.sheet_names}")
    df = pd.read_excel(input_path, dtype=str)
    print(f"📐 行 × 列: {len(df)} × {len(df.columns)}")
    print(f"🏷️ 列名: {list(df.columns)}")

    if log_column not in df.columns:
        print(f"❌ 未找到日志列 '{log_column}'（可用列见上），用 --log-column 指定实际列名")
        return

    logs = df[log_column]
    empty_rows = int((logs.isna() | (logs.fillna("").str.strip() == "")).sum())
    print(f"\n📜 日志列 '{log_column}': 空值/空白 {empty_rows}/{len(df)} 行")

    # 截断风险
    lengths = logs.fillna("").str.len()
    n_risk = int((lengths >= TRUNCATION_RISK_THRESHOLD).sum())
    n_limit = int((lengths >= EXCEL_CELL_LIMIT).sum())
    print(f"📏 日志长度: 最长 {int(lengths.max())} 字符 | "
          f"≥{TRUNCATION_RISK_THRESHOLD} 字符(截断风险) {n_risk} 行 | "
          f"≥{EXCEL_CELL_LIMIT}(已达上限) {n_limit} 行")

    # 格式识别（抽样）
    sample = logs.dropna().sample(n=min(sample_n, int(logs.notna().sum())), random_state=42)
    fmt_counts = sample.map(detect_log_format).value_counts()
    print(f"\n🔤 日志格式识别（抽样 {len(sample)} 行）:")
    for k, v in fmt_counts.items():
        print(f"   {k}: {v} ({v / len(sample):.0%})")

    # 字段出现率/非空率（全量，kv 正则 + JSON 风格双探测）
    print(f"\n🎯 字段探测（全量 {len(logs)} 行）:")
    for field in fields:
        kv_pat = re.compile(rf'(?<![A-Za-z0-9_]){re.escape(field)}="((?:[^"\\]|\\.)*)"')
        json_pat = re.compile(rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"')
        has_key = 0
        non_empty = 0
        for txt in logs:
            if not isinstance(txt, str):
                continue
            m = json_pat.search(txt) or kv_pat.search(txt)
            if m:
                has_key += 1
                if m.group(1):
                    non_empty += 1
            elif f'{field}="' in txt or f'"{field}"' in txt:
                has_key += 1  # 有键但值被截断/异常
        print(f"   - {field}: 出现 {has_key}/{len(logs)} 行, 其中非空值 {non_empty} 行")

    # 选脚本提示
    print("\n💡 提示: 格式为 kv/json 均可直接用 excel_extract_log_fields.py 提取；"
          "存在截断风险行时提取结果会带 TRUNCATED_TAIL 诊断（值不完整，源头截断）。")


def main():
    p = argparse.ArgumentParser(description="Excel 日志预检：格式识别 + 字段探测 + 截断风险")
    p.add_argument("input", help="输入 Excel 文件")
    p.add_argument("--log-column", default=LOG_COLUMN, help=f"日志列名，默认 {LOG_COLUMN}")
    p.add_argument("--fields", default=",".join(DEFAULT_FIELDS),
                   help=f"关心的字段，逗号分隔，默认 {','.join(DEFAULT_FIELDS)}")
    p.add_argument("--sample", type=int, default=DEFAULT_SAMPLE,
                   help=f"格式识别抽样行数，默认 {DEFAULT_SAMPLE}")
    args = p.parse_args(sys.argv[1:])

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    inspect(args.input, args.log_column, fields, args.sample)


if __name__ == "__main__":
    main()
