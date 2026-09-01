#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base64 解析规则数据 - 清空 normalize.field 工具

功能说明:
1. 输入 Base64 加密数据
2. Base64 解码为 JSON 数组
3. 根据用户输入的 field 名称，遍历每个规则对象中的 normalize 数组
4. 将所有 field 完全等于用户输入值的条目，其 field 置为空字符串 ""

处理规则:
- 用户输入 location_country，则将所有 normalize 中 field == "location_country" 的
  条目的 field 改为 ""，其余字段（mappings、sim、result、entity、index 等）保持不变
- 支持一次处理多个 field，例如:
    location_country,location_province
- 如果同一个规则的 normalize 中存在多个匹配项，全部置空
- 如果多个规则中都存在匹配项，也全部置空
- 只处理顶层规则对象下的 normalize 数组
- 不修改 id、name、deviceType、parser、properties、sample 等其他字段
- 不删除 normalize 条目本身，仅清空 field 值

处理前示例:
    {
        "mappings": [],
        "field": "location_country",
        "sim": false,
        "result": ["中国"],
        "info": null,
        "entity": "位置",
        "required": false,
        "core": false,
        "value": "",
        "index": "syslog.r_country"
    }

处理后示例:
    {
        "mappings": [],
        "field": "",
        "sim": false,
        "result": ["中国"],
        "info": null,
        "entity": "位置",
        "required": false,
        "core": false,
        "value": "",
        "index": "syslog.r_country"
    }

用法:
    python clear_normalize_field.py input.txt output.txt location_country

    python clear_normalize_field.py input.txt output.txt location_country location_province

    python clear_normalize_field.py input.txt output.txt --fields=location_country,location_province

    python clear_normalize_field.py input.txt output.txt
    # 不传 field 时会交互式提示输入
"""

import base64
import json
import os
import re
import sys


# ======================== 默认配置 ========================
DEFAULT_INPUT_FILE = "input.txt"
DEFAULT_OUTPUT_FILE = "output.txt"
# =========================================================


def print_help():
    """打印使用说明"""
    help_text = """
用法:
    python clear_normalize_field.py [输入文件] [输出文件] [field1] [field2] ...

示例:
    python clear_normalize_field.py input.txt output.txt location_country

    python clear_normalize_field.py input.txt output.txt location_country location_province

    python clear_normalize_field.py input.txt output.txt --fields=location_country,location_province

参数说明:
    输入文件      Base64 加密数据文件，默认 input.txt
    输出文件      处理后输出的 Base64 文件，默认 output.txt
    field        要置空的 normalize.field 名称，支持多个
    --fields     使用逗号或空格分隔多个 field
    -h, --help   显示帮助信息
"""
    print(help_text.strip())


def split_fields(raw: str):
    """
    拆分用户输入的多个 field

    支持:
        location_country
        location_country,location_province
        location_country location_province
        location_country, location_province src_port
    """
    if not raw:
        return []

    return [item.strip() for item in re.split(r"[,\s]+", raw.strip()) if item.strip()]


def parse_args(argv):
    """
    解析命令行参数

    返回:
        input_path, output_path, fields, mode
    """
    input_path = DEFAULT_INPUT_FILE
    output_path = DEFAULT_OUTPUT_FILE
    fields = []
    mode = "clear"  # 默认置空，--mode remove 则删除整个条目

    args = argv[1:]
    remaining = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-h", "--help"):
            print_help()
            sys.exit(0)

        if arg.startswith("--fields="):
            fields.extend(split_fields(arg.split("=", 1)[1]))
        elif arg == "--fields":
            if i + 1 < len(args):
                fields.extend(split_fields(args[i + 1]))
                i += 1
        elif arg.startswith("--mode="):
            mode = arg.split("=", 1)[1].strip()
        elif arg == "--mode":
            if i + 1 < len(args):
                mode = args[i + 1].strip()
                i += 1
        else:
            remaining.append(arg)
        i += 1

    if len(remaining) >= 1:
        input_path = remaining[0]

    if len(remaining) >= 2:
        output_path = remaining[1]

    if len(remaining) >= 3:
        for item in remaining[2:]:
            fields.extend(split_fields(item))

    # 去重，保持输入顺序
    seen = set()
    unique_fields = []
    for field in fields:
        if field not in seen:
            seen.add(field)
            unique_fields.append(field)

    fields = unique_fields

    # 如果命令行没有传 field，则交互式提示输入
    if not fields:
        try:
            raw = input("请输入要处理的 normalize.field，多个可用逗号或空格分隔: ")
        except EOFError:
            raw = ""

        fields = split_fields(raw)

    if mode not in ("clear", "remove"):
        raise ValueError(f"--mode 只能是 clear 或 remove，收到: {mode}")

    return input_path, output_path, fields, mode


def read_input(input_path: str) -> str:
    """读取输入数据"""
    if input_path == "-":
        return sys.stdin.read()

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        return f.read()


def write_output(output_path: str, data: str):
    """输出结果"""
    if output_path == "-":
        sys.stdout.write(data)
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(data)


def base64_to_json(b64_data: str):
    """
    Base64 解码为 JSON 对象

    支持:
        - 自动去除换行、空格、回车
        - 自动去除 data URI 前缀
        - 自动补齐 Base64 padding
        - 标准 Base64 解码失败时尝试 URL Safe Base64
    """
    clean = b64_data.strip()

    # 兼容 data:application/json;base64,xxxx 格式
    if clean.startswith("data:"):
        clean = clean.split(",", 1)[-1]

    # 去除所有空白字符
    clean = re.sub(r"\s+", "", clean)

    if not clean:
        raise ValueError("Base64 输入为空")

    # 补齐 padding
    missing_padding = len(clean) % 4
    if missing_padding:
        clean += "=" * (4 - missing_padding)

    try:
        decoded_bytes = base64.b64decode(clean)
    except Exception:
        decoded_bytes = base64.urlsafe_b64decode(clean)

    decoded_text = decoded_bytes.decode("utf-8")

    try:
        return json.loads(decoded_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Base64 解码后不是合法 JSON: {e}")


def json_to_base64(data) -> str:
    """JSON 对象重新编码为 Base64 字符串"""
    json_text = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return base64.b64encode(
        json_text.encode("utf-8")
    ).decode("ascii")


def clear_normalize_fields(data_array, fields_to_clear, mode="clear"):
    """
    处理 normalize 数组中 field 匹配的条目

    参数:
        data_array: Base64 解码后的 JSON 数组
        fields_to_clear: 要处理的 field 列表
        mode: "clear"=把 field 值置为空字符串(条目保留); "remove"=删除整个条目

    返回:
        cleared_counter: 每个 field 被处理的次数
    """
    if not isinstance(data_array, list):
        raise ValueError("解码后的数据不是 JSON 数组")

    if mode not in ("clear", "remove"):
        raise ValueError(f"mode 只能是 clear 或 remove，收到: {mode}")

    targets = set(fields_to_clear)

    cleared_counter = {
        field: 0
        for field in fields_to_clear
    }

    for rule in data_array:
        if not isinstance(rule, dict):
            continue

        normalize = rule.get("normalize")

        if not isinstance(normalize, list):
            continue

        if mode == "clear":
            # 置空模式：条目保留，field 值改为 ""
            for entry in normalize:
                if not isinstance(entry, dict):
                    continue
                field_name = entry.get("field")
                if field_name in targets:
                    entry["field"] = ""
                    cleared_counter[field_name] = cleared_counter.get(field_name, 0) + 1
        else:
            # 删除模式：移除整个条目（原地改 list）
            kept = []
            for entry in normalize:
                if isinstance(entry, dict) and entry.get("field") in targets:
                    cleared_counter[entry["field"]] = cleared_counter.get(entry["field"], 0) + 1
                else:
                    kept.append(entry)
            rule["normalize"] = kept

    return cleared_counter


def process(b64_input: str, fields_to_clear, mode="clear"):
    """
    主处理函数

    输入:
        b64_input: Base64 字符串
        fields_to_clear: 要处理的 normalize.field 列表
        mode: "clear"=置空 field 值(条目保留); "remove"=删除整个条目

    返回:
        result_b64: 处理后的 Base64 字符串
        cleared_counter: 处理统计
    """
    data = base64_to_json(b64_input)

    cleared_counter = clear_normalize_fields(
        data_array=data,
        fields_to_clear=fields_to_clear,
        mode=mode
    )

    result_b64 = json_to_base64(data)

    return result_b64, cleared_counter


def main():
    """程序入口"""
    try:
        input_path, output_path, fields, mode = parse_args(sys.argv)

        action = "置空" if mode == "clear" else "删除"

        print("=" * 60)
        print(f"Base64 解析规则数据 - {action} normalize.field 工具")
        print("=" * 60)
        print(f"输入文件: {input_path}")
        print(f"输出文件: {output_path}")
        print(f"模式: {mode} ({action} field)")
        print(f"待{action} field: {fields if fields else '未指定'}")
        print("-" * 60)

        if not fields:
            print(f"[WARN] 未指定要{action}的 field，输出数据不会发生变化。")

        b64_data = read_input(input_path)

        result_b64, cleared_counter = process(
            b64_input=b64_data,
            fields_to_clear=fields,
            mode=mode
        )

        write_output(output_path, result_b64)

        total_cleared = sum(cleared_counter.values())

        for field_name, count in cleared_counter.items():
            print(f"{action} field=\"{field_name}\" 共 {count} 处")

        print("-" * 60)
        print(f"总计{action} normalize.field: {total_cleared} 处")
        print(f"输出已写入: {output_path}")

    except Exception as e:
        print(f"[ERROR] 处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()