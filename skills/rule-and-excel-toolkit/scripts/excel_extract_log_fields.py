#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 日志字段提取工具（执行型）
读取 Excel 中的日志列，对每行用「JSON 解析优先 + 安全正则兜底」双策略提取指定字段，展开成多列输出。

命令行用法：
    python excel_extract_log_fields.py <输入文件> [输出文件] [--log-column 列名] [--fields f1,f2,...] [--no-diag]

    --log-column：日志所在列名，默认 原始日志
    --fields：要提取的字段，逗号分隔，默认 deviceName,deviceAddress,deviceProductType,productVendorName,deviceSendProductName,rawEvent
    --no-diag：不输出 _diag 诊断列（默认输出）
"""

import argparse
import json
import os
import re
import sys

import pandas as pd

# ==================== 默认配置（命令行未传时兜底） ====================
INPUT_FILE = "input.xlsx"
OUTPUT_FILE = "output.xlsx"
LOG_COLUMN = "原始日志"
DEFAULT_TARGET_FIELDS = [
    "deviceName", "deviceAddress", "deviceProductType",
    "productVendorName", "deviceSendProductName", "rawEvent",
]
ENABLE_DIAG = True
# ====================================================================

# Excel禁止的控制字符: \x00-\x08, \x0b, \x0c, \x0e-\x1f
_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def build_field_patterns(target_fields):
    """安全正则模板: 用 (?:[^"\\]|\\.)* 替代 (.*?)，正确处理转义引号"""
    return {
        field: re.compile(rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"')
        for field in target_fields
    }


def _clean_for_excel(value):
    """移除字符串中Excel不支持的非法控制字符"""
    if isinstance(value, str):
        return _ILLEGAL_CHARS_RE.sub('', value)
    return value


def extract_fields_from_log(log_str, target_fields, field_patterns):
    """
    双策略字段提取: JSON优先 → 安全正则兜底
    返回字典包含所有 target_fields + 可选 _diag
    """
    result = {field: "" for field in target_fields}
    diag = "OK"

    if not isinstance(log_str, str) or not log_str.strip():
        diag = "EMPTY_INPUT"
        result["_diag"] = diag
        return result

    # 策略1: JSON解析
    try:
        start = log_str.find('{')
        end = log_str.rfind('}') + 1
        if start == -1 or end <= start:
            diag = "NO_JSON_BODY"
        else:
            data = json.loads(log_str[start:end])
            infos = data.get("parsedInfos", data)
            for field in target_fields:
                val = infos.get(field, "")
                result[field] = str(val) if val is not None else ""
            if infos.get("rawEvent") is None and "rawEvent" in target_fields:
                diag = "RAW_EVENT_IS_NULL"
            result["_diag"] = diag
            return result
    except json.JSONDecodeError as e:
        diag = f"JSON_ERROR:{str(e)[:80]}"

    # 策略2: 安全正则兜底
    matched = 0
    for field in target_fields:
        m = field_patterns[field].search(log_str)
        if m:
            matched += 1
            raw_val = m.group(1)
            try:
                result[field] = json.loads(f'"{raw_val}"')
            except Exception:
                result[field] = raw_val

    if not result.get("rawEvent"):
        diag = f"REGEX_MISS(rawEvent,matched={matched}/{len(target_fields)})"

    result["_diag"] = diag
    return result


def process_excel(input_path, output_path, log_column="原始日志",
                  target_fields=None, enable_diag=True):
    if target_fields is None:
        target_fields = list(DEFAULT_TARGET_FIELDS)
    field_patterns = build_field_patterns(target_fields)

    print(f"📂 读取文件: {input_path}")
    df = pd.read_excel(input_path)

    if log_column not in df.columns:
        raise ValueError(f"❌ 未找到列 '{log_column}'，可用列: {list(df.columns)}")

    print(f"🔍 共 {len(df)} 条记录，提取字段 {target_fields}...")
    extracted = df[log_column].apply(
        lambda s: extract_fields_from_log(s, target_fields, field_patterns)
    )
    result_df = pd.DataFrame(extracted.tolist())

    result_df.insert(0, log_column, df[log_column].values)

    for col in result_df.columns:
        result_df[col] = result_df[col].apply(_clean_for_excel)

    if not enable_diag and "_diag" in result_df.columns:
        result_df.drop(columns=["_diag"], inplace=True)

    result_df.to_excel(output_path, index=False)
    print(f"✅ 完成! 输出: {output_path}")
    print(f"   列: {list(result_df.columns)}")

    for field in target_fields:
        if field in result_df.columns:
            non_empty = (result_df[field] != "").sum()
            print(f"   - {field}: {non_empty}/{len(df)} 条有值")

    if enable_diag and "_diag" in result_df.columns:
        print("\n📊 诊断统计:")
        for k, v in result_df["_diag"].value_counts().items():
            print(f"   {k}: {v}")


def main():
    p = argparse.ArgumentParser(description="从 Excel 日志列提取多个 JSON 字段")
    p.add_argument("input", help="输入 Excel 文件")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _提取")
    p.add_argument("--log-column", default=LOG_COLUMN, help=f"日志列名，默认 {LOG_COLUMN}")
    p.add_argument("--fields", default=None, help="逗号分隔的字段列表，默认内置 6 个字段")
    p.add_argument("--no-diag", action="store_true", help="不输出 _diag 诊断列")
    args = p.parse_args(sys.argv[1:])

    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_提取{ext or '.xlsx'}"

    target_fields = None
    if args.fields:
        target_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    process_excel(
        args.input, output_path,
        log_column=args.log_column,
        target_fields=target_fields,
        enable_diag=not args.no_diag,
    )


if __name__ == "__main__":
    main()
