#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 日志字段提取工具（执行型）
读取 Excel 中的日志列，对每行用「JSON 解析优先 + 双风格正则兜底」策略提取指定字段，保留原始所有列并追加提取列。

支持三种日志形态（自动适配，无需指定）：
    1. JSON 体（含 parsedInfos 或平铺 dict）—— 优先解析
    2. JSON 风格正则兜底:   "field":"value"
    3. 键值对风格兜底:      field="value"   （管道分隔日志常见格式，如 node_ip="1.2.3.4"|||）
    另有截断兜底: 源文件被 Excel 32767 字符单元格上限截断、值有起始引号无闭合引号时，
    尽力提取到字符串尾部，_diag 标记 TRUNCATED_TAIL（值可能不完整）。

命令行用法：
    python excel_extract_log_fields.py <输入文件> [输出文件] [--log-column 列名] \
        [--fields f1,f2,...] [--no-diag] [--verify-sample N]

    --log-column   ：日志所在列名，默认 原始日志
    --fields       ：要提取的字段，逗号分隔，默认 deviceName,deviceAddress,deviceProductType,productVendorName,deviceSendProductName,rawEvent
    --no-diag      ：不输出 _diag 诊断列（默认输出）
    --verify-sample：写完输出后随机抽 N 行做「提取值 == 日志原文值」回对，打印通过率
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
    """每个字段返回两个安全正则（转义安全: (?:[^"\\\\]|\\\\.)* 替代 (.*?)）:
    - JSON 风格:  "field":"value"
    - kv 风格:    field="value"   （key 不带引号，管道分隔日志常见格式）
    """
    patterns = {}
    for field in target_fields:
        patterns[field] = (
            # JSON 风格
            re.compile(rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"'),
            # key="value" 风格
            re.compile(rf'{re.escape(field)}="((?:[^"\\]|\\.)*)"'),
        )
    return patterns


def _clean_for_excel(value):
    """移除字符串中Excel不支持的非法控制字符"""
    if isinstance(value, str):
        return _ILLEGAL_CHARS_RE.sub('', value)
    return value


def _unescape(raw_val):
    """把正则捕获的原始值按 JSON 字符串转义规则还原"""
    try:
        return json.loads(f'"{raw_val}"')
    except Exception:
        return raw_val


def extract_fields_from_log(log_str, target_fields, field_patterns):
    """
    多策略字段提取: JSON解析(仅在真正解析成功时短路) → JSON风格正则 → kv风格正则 → 截断兜底
    返回字典包含所有 target_fields + _diag
    诊断码: OK / EMPTY_INPUT / TRUNCATED_TAIL / REGEX_MISS(matched=x/y) / RAW_EVENT_IS_NULL
    """
    result = {field: "" for field in target_fields}
    diag = "OK"

    if not isinstance(log_str, str) or not log_str.strip():
        result["_diag"] = "EMPTY_INPUT"
        return result

    # 策略1: JSON解析——只在真正解析出 dict 时才短路返回，避免「含 { 但解析失败」的行带着空结果提前返回
    start = log_str.find('{')
    end = log_str.rfind('}') + 1
    if start != -1 and end > start:
        try:
            data = json.loads(log_str[start:end])
            infos = data.get("parsedInfos", data) if isinstance(data, dict) else None
            if isinstance(infos, dict):
                for field in target_fields:
                    val = infos.get(field, "")
                    result[field] = str(val) if val is not None else ""
                if infos.get("rawEvent") is None and "rawEvent" in target_fields:
                    diag = "RAW_EVENT_IS_NULL"
                result["_diag"] = diag
                return result
        except json.JSONDecodeError:
            pass  # 无有效 JSON 体，落入正则兜底

    # 策略2+3: 双风格正则兜底（JSON 风格优先，key="value" 风格次之）
    matched = 0
    truncated = False
    for field in target_fields:
        pat_json, pat_kv = field_patterns[field]
        m = pat_json.search(log_str) or pat_kv.search(log_str)
        if m:
            matched += 1
            result[field] = _unescape(m.group(1))
        else:
            # 策略4: 截断兜底——值有起始引号、无闭合引号（源文件被 32767 字符上限切断）
            anchor = re.search(rf'(?<![A-Za-z0-9_]){re.escape(field)}="', log_str)
            if anchor:
                matched += 1
                truncated = True
                result[field] = _unescape(log_str[anchor.end():])

    if truncated:
        diag = "TRUNCATED_TAIL"
    elif matched < len(target_fields):
        diag = f"REGEX_MISS(matched={matched}/{len(target_fields)})"

    result["_diag"] = diag
    return result


def _escape_like_source(value):
    """把已还原的值重新转义，用于在原文中做包含性检查"""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def verify_sample(result_df, log_column, target_fields, n, seed=42):
    """
    随机抽 N 行做独立回对：用与提取不同的简单正则重新从原文找值，比对输出单元格。
    - 输出有值 + 简单正则也匹配到值 → 强校验（值相等）
    - 输出有值 + 简单正则匹配不到（值被深度转义/截断）→ 弱校验（转义后前缀包含于原文）
    - 输出为空 + 原文里也找不到非空值 → 通过；输出为空但原文有值 → 失败（典型静默漏提）
    返回 True 表示全部通过。
    """
    if n <= 0 or len(result_df) == 0:
        return True
    sample_idx = result_df.sample(n=min(n, len(result_df)), random_state=seed).index.tolist()
    passed = failed = 0
    failures = []
    for i in sample_idx:
        log_str = result_df.at[i, log_column]
        if not isinstance(log_str, str):
            continue
        for field in target_fields:
            if field not in result_df.columns:
                continue
            raw = result_df.at[i, field]
            val = "" if raw is None or (isinstance(raw, float) and pd.isna(raw)) else str(raw)
            simple = re.search(rf'(?<![A-Za-z0-9_]){re.escape(field)}="([^"]*)"', log_str) \
                or re.search(rf'"{re.escape(field)}"\s*:\s*"([^"]*)"', log_str)
            if val:
                if simple and simple.group(1):
                    if _unescape(simple.group(1)) == val \
                            or _escape_like_source(val)[:60] in log_str or val[:30] in log_str:
                        passed += 1
                    else:
                        failed += 1
                        failures.append((i, field))
                else:
                    # 简单正则不覆盖（转义引号/截断/JSON体内值）→ 弱校验: 前缀包含
                    if _escape_like_source(val)[:60] in log_str or val[:30] in log_str:
                        passed += 1
                    else:
                        failed += 1
                        failures.append((i, field))
            else:
                if simple and simple.group(1):
                    failed += 1  # 原文有值却提取为空 → 典型静默漏提
                    failures.append((i, field))
                else:
                    passed += 1

    total = passed + failed
    print(f"\n🧪 抽查回对 (随机 {len(sample_idx)} 行 × {len(target_fields)} 字段): "
          f"通过 {passed}/{total}")
    if failures:
        print(f"   ❌ 不一致的 (行号, 字段): {failures[:20]}")
    return failed == 0


def process_excel(input_path, output_path, log_column="原始日志",
                  target_fields=None, enable_diag=True, verify_n=0):
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
    extracted_df = pd.DataFrame(extracted.tolist())

    # 只清洗新提取的列；原始列原样保留
    for col in extracted_df.columns:
        extracted_df[col] = extracted_df[col].apply(_clean_for_excel)

    if not enable_diag and "_diag" in extracted_df.columns:
        extracted_df.drop(columns=["_diag"], inplace=True)

    # 保留所有原始列 + 追加提取列
    result_df = pd.concat([df, extracted_df], axis=1)
    result_df.to_excel(output_path, index=False)
    print(f"✅ 完成! 输出: {output_path}")
    print(f"   列: {list(result_df.columns)}")

    for field in target_fields:
        if field in result_df.columns:
            non_empty = (result_df[field].fillna("") != "").sum()
            print(f"   - {field}: {non_empty}/{len(df)} 条有值")

    if enable_diag and "_diag" in result_df.columns:
        print("\n📊 诊断统计:")
        for k, v in result_df["_diag"].value_counts().items():
            print(f"   {k}: {v}")
        if (result_df["_diag"] == "TRUNCATED_TAIL").any():
            print("   ⚠️ TRUNCATED_TAIL = 源文件被 Excel 32767 字符上限截断，该行提取值不完整（源头问题，非提取错误）")

    if verify_n > 0:
        ok = verify_sample(result_df, log_column, target_fields, verify_n)
        if not ok:
            print("   ⚠️ 抽查存在不一致，请检查上方失败明细")


def main():
    p = argparse.ArgumentParser(description="从 Excel 日志列提取字段（JSON/键值对双格式 + 截断兜底）")
    p.add_argument("input", help="输入 Excel 文件")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _提取")
    p.add_argument("--log-column", default=LOG_COLUMN, help=f"日志列名，默认 {LOG_COLUMN}")
    p.add_argument("--fields", default=None, help="逗号分隔的字段列表，默认内置 6 个字段")
    p.add_argument("--no-diag", action="store_true", help="不输出 _diag 诊断列")
    p.add_argument("--verify-sample", type=int, default=0, metavar="N",
                   help="随机抽 N 行做提取值与原文的回对校验，默认 0（不抽查）")
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
        verify_n=args.verify_sample,
    )


if __name__ == "__main__":
    main()
