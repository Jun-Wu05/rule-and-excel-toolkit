#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按指定字段拆 Sheet 的日志加工脚本（执行型）
- 从 原始日志 列解析 JSON，提取指定字段；
- 保留原始所有列，并追加提取字段列；
- 首页：原始全量数据；
- 第二页：按 --split-field 去重（保留首条，默认 deviceAddress）；
- 之后每个不同字段值一个独立 Sheet，Sheet 名为该值。
"""

import argparse
import json
import os
import re
import sys

import pandas as pd
from openpyxl import Workbook

_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def clean_for_excel(value):
    if isinstance(value, str):
        return _ILLEGAL_CHARS_RE.sub('', value)
    return value


def safe_sheet_name(name, used):
    """生成合法且不重复的 sheet 名（Excel 限制 31 字符，禁用 : \\ / ? * [ ]）"""
    base = str(name) if name is not None and str(name) != "" else "空"
    base = re.sub(r'[\:\\/?*\[\]]', '_', base)
    base = base.strip()
    if len(base) > 31:
        base = base[:31]
    candidate = base
    i = 2
    while candidate in used:
        suffix = f"_{i}"
        candidate = base[:31 - len(suffix)] + suffix
        i += 1
    used.add(candidate)
    return candidate


def extract_one(log_str, target_fields):
    """JSON 优先 + 正则兜底，返回 (字段字典, 是否成功)"""
    result = {f: "" for f in target_fields}
    if not isinstance(log_str, str) or not log_str.strip():
        return result, False
    # 策略1：JSON
    try:
        start = log_str.find('{')
        end = log_str.rfind('}') + 1
        if start != -1 and end > start:
            data = json.loads(log_str[start:end])
            infos = data.get("parsedInfos", data)
            for f in target_fields:
                v = infos.get(f, "")
                result[f] = str(v) if v is not None else ""
            return result, True
    except json.JSONDecodeError:
        pass
    # 策略2：正则兜底
    for f in target_fields:
        m = re.search(rf'"{f}"\s*:\s*"((?:[^"\\]|\\.)*)"', log_str)
        if m:
            raw = m.group(1)
            try:
                result[f] = json.loads(f'"{raw}"')
            except Exception:
                result[f] = raw
    return result, True


def process(input_path, output_path, log_column, target_fields, split_field="deviceAddress"):
    print(f"📂 读取: {input_path}")
    df = pd.read_excel(input_path, dtype=object)
    if log_column not in df.columns:
        raise ValueError(f"❌ 未找到列 '{log_column}'，可用列: {list(df.columns)}")
    print(f"🔍 共 {len(df)} 行，提取字段 {target_fields}")

    extracted = df[log_column].apply(lambda s: extract_one(s, target_fields))
    field_df = pd.DataFrame([r for r, _ in extracted], index=df.index)

    # 保留所有原始列 + 追加提取列
    out = pd.concat([df, field_df[target_fields]], axis=1)
    out = out.applymap(clean_for_excel)

    if split_field not in out.columns:
        raise ValueError(f"❌ 未找到拆分字段 '{split_field}'，可用列: {list(out.columns)}")

    # 去重页（按 split_field 保留首条）
    dedup = out.drop_duplicates(subset=[split_field], keep="first").reset_index(drop=True)

    distinct = list(dict.fromkeys(out[split_field].astype(str).tolist()))
    print(f"   全量 {len(out)} 行；去重后 {len(dedup)} 行；不同 {split_field} 共 {len(distinct)} 个")

    wb = Workbook()
    wb.remove(wb.active)
    used = set()

    def write_sheet(name, frame):
        sn = safe_sheet_name(name, used)
        ws = wb.create_sheet(title=sn)
        ws.append(list(frame.columns))
        for row in frame.itertuples(index=False, name=None):
            ws.append([("" if (v is None or (isinstance(v, float) and pd.isna(v))) else v) for v in row])
        # 简单列宽
        for i, col in enumerate(frame.columns, 1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = max(12, min(60, max(len(str(col)), 14)))
        return sn

    # 首页：原始全量
    write_sheet("原始全量数据", out)
    # 第二页：按 split_field 去重
    write_sheet(f"{split_field}去重", dedup)
    # 之后：每个字段值一个 sheet
    for addr in distinct:
        sub = out[out[split_field].astype(str) == addr].reset_index(drop=True)
        write_sheet(addr, sub)

    wb.save(output_path)
    print(f"✅ 完成! 输出: {output_path}")
    print(f"   Sheet 列表({len(wb.sheetnames)}): {wb.sheetnames}")
    # 字段非空统计
    for f in target_fields:
        non_empty = (out[f].astype(str) != "").sum()
        print(f"   - {f}: {non_empty}/{len(out)} 条有值")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--log-column", default="原始日志")
    p.add_argument("--fields", default="deviceName,productVendorName,deviceSendProductName,dvcAddress,rawEvent,deviceAddress,dataType")
    p.add_argument("--split-field", default="deviceAddress", help="按该列去重并拆 Sheet（默认 deviceAddress）")
    a = p.parse_args(sys.argv[1:])
    fields = [f.strip() for f in a.fields.split(",") if f.strip()]
    process(a.input, a.output, a.log_column, fields, a.split_field)


if __name__ == "__main__":
    main()
