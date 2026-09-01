#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base64 解析规则修改工具（执行型）
- 仅替换顶层规则的 UUID，其他所有 ID（deviceType.id、filter.id 等）保持不变
- 自动同步所有引用处，保证规则间层级关系不断裂
- 可选给顶层 name 加前缀或后缀（幂等，防重复叠加）

命令行用法：
    python rule_replace_uuid.py <输入文件> [输出文件] [--prefix 前缀] [--suffix 后缀] [--verify]

    输入文件：Base64 编码的解析规则 JSON 文本文件
    输出文件：默认在输入文件同目录，文件名加 _reuuid 后缀
    --prefix：给顶层 name 加前缀，如 --prefix 南方电网_
    --suffix：给顶层 name 加后缀，如 --suffix _0731
    --prefix 与 --suffix 可同时使用，也可都不用（只换 UUID 不改 name）
    --verify：跑完后打印 UUID 替换与引用一致性校验
"""

import json
import base64
import uuid
import os
import sys
import copy
import argparse


def generate_rule_uuid() -> str:
    """生成标准 UUID（规则级别）"""
    return str(uuid.uuid4())


def collect_rule_uuid_mapping(data_array: list) -> dict:
    """
    仅收集顶层规则对象的 id，建立 old_uuid -> new_uuid 映射。
    不收集 deviceType.id、filter.id 等非规则 UUID。
    """
    mapping = {}
    for item in data_array:
        if isinstance(item, dict):
            old_id = item.get('id')
            if old_id and old_id not in mapping:
                mapping[old_id] = generate_rule_uuid()
    return mapping


def replace_rule_uuids_recursive(obj, mapping: dict):
    """
    递归替换所有"值完全等于旧规则UUID"的字符串。
    只替换精确匹配，不做子串替换，不影响其他字段。
    """
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            if isinstance(val, str) and val in mapping:
                obj[key] = mapping[val]
            else:
                replace_rule_uuids_recursive(val, mapping)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in mapping:
                obj[i] = mapping[item]
            else:
                replace_rule_uuids_recursive(item, mapping)


def modify_top_level_names(data_array: list, prefix: str = "", suffix: str = ""):
    """
    仅修改顶层规则对象的 name 字段：加前缀和/或后缀。
    不递归、不触碰 deviceType.name / properties[].name / parser.name / filter[].name。
    幂等：已有该前缀/后缀则跳过，防止重复叠加。
    """
    changed = 0
    for item in data_array:
        if isinstance(item, dict) and 'name' in item:
            old_name = item['name']
            if not old_name:
                continue
            new_name = str(old_name)
            if prefix and not new_name.startswith(prefix):
                new_name = f"{prefix}{new_name}"
            if suffix and not new_name.endswith(suffix):
                new_name = f"{new_name}{suffix}"
            if new_name != str(old_name):
                item['name'] = new_name
                changed += 1
    return changed


def process(b64_input: str, prefix: str = "", suffix: str = "") -> str:
    """主处理流程：解码 → 换 UUID → 改 name → 重新编码"""
    # 1. Base64 解码 → JSON
    clean = b64_input.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    decoded = base64.b64decode(clean).decode('utf-8')
    data_array = json.loads(decoded)

    if not isinstance(data_array, list):
        raise ValueError("解码后数据不是 JSON 数组")

    print(f"[INFO] 共 {len(data_array)} 条规则")

    # 2. 收集顶层规则 UUID 映射（仅此一步决定哪些 ID 会变）
    uuid_mapping = collect_rule_uuid_mapping(data_array)
    print(f"[INFO] 共 {len(uuid_mapping)} 个规则 UUID 需要替换")
    for old, new in uuid_mapping.items():
        print(f"       {old}  →  {new}")

    # 3. 深拷贝后递归替换所有引用（保证层级一致）
    data_array = copy.deepcopy(data_array)
    replace_rule_uuids_recursive(data_array, uuid_mapping)

    # 4. 改顶层 name（前缀/后缀，可选）
    if prefix or suffix:
        changed = modify_top_level_names(data_array, prefix, suffix)
        desc = []
        if prefix:
            desc.append(f"前缀 '{prefix}'")
        if suffix:
            desc.append(f"后缀 '{suffix}'")
        print(f"[INFO] 已为 {changed} 条规则的 name 加 {' + '.join(desc)}")
    else:
        print("[INFO] 未指定 prefix/suffix，仅替换 UUID，name 不变")

    # 5. 序列化 + 重新 Base64 编码
    result_json = json.dumps(data_array, ensure_ascii=False, separators=(',', ':'))
    result_b64 = base64.b64encode(result_json.encode('utf-8')).decode('ascii')

    return result_b64


def verify_result(result_b64: str):
    """打印验证信息：每条规则的 id/name，以及引用一致性校验"""
    decoded = base64.b64decode(result_b64).decode('utf-8')
    check = json.loads(decoded)

    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    rule_ids = {}
    for i, rule in enumerate(check):
        rid = rule.get('id')
        rule_ids[rid] = i
        print(f"规则{i+1} 顶层 name : {rule.get('name')}")
        print(f"       顶层 id   : {rid}")
        dt = rule.get('deviceType', {})
        print(f"       deviceType: id={dt.get('id')}  name={dt.get('name')}  parentId={dt.get('parentId')}")
        parser = rule.get('parser', {})
        print(f"       parser    : name={parser.get('name')}")
        filters = parser.get('filter') or []
        for fi, f in enumerate(filters):
            print(f"       filter[{fi}]: id={f.get('id')}  name={f.get('name')}  ref={f.get('ref')}")
        print()

    # 验证引用一致性
    bad = 0
    for i, rule in enumerate(check):
        normalize = rule.get('normalize') or []
        for ni, norm in enumerate(normalize):
            info_list = norm.get('info') or []
            for info in info_list:
                if isinstance(info, dict) and info.get('id'):
                    ref_id = info['id']
                    if ref_id not in rule_ids:
                        print(f"⚠️  规则{i+1} normalize[{ni}].info 引用了未知ID: {ref_id}")
                        bad += 1

        props = rule.get('properties') or []
        for pi, prop in enumerate(props):
            info_list = prop.get('info') or []
            for info in info_list:
                if isinstance(info, dict) and info.get('id'):
                    ref_id = info['id']
                    if ref_id not in rule_ids:
                        print(f"⚠️  规则{i+1} properties[{pi}].info 引用了未知ID: {ref_id}")
                        bad += 1

        filters = (rule.get('parser') or {}).get('filter') or []
        for fi, f in enumerate(filters):
            refs = f.get('ref') or []
            for r in refs:
                if r not in rule_ids:
                    print(f"⚠️  规则{i+1} filter[{fi}].ref 引用了未知ID: {r}")
                    bad += 1
                else:
                    print(f"✅ 规则{i+1} filter[{fi}].ref → 规则{rule_ids[r]+1} (一致)")

    if bad == 0:
        print("✅ 引用一致性校验通过：所有 ref/info 引用都指向已知规则")
    else:
        print(f"⚠️  发现 {bad} 处引用指向未知 ID，请检查")
    print("=" * 60)


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="替换顶层规则 UUID（同步引用）+ 可选给 name 加前缀/后缀",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="输入文件（Base64 编码的解析规则）")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _reuuid")
    p.add_argument("--prefix", default="", help="给顶层 name 加前缀，如 南方电网_")
    p.add_argument("--suffix", default="", help="给顶层 name 加后缀，如 _0731")
    p.add_argument("--verify", action="store_true", help="跑完后打印引用一致性校验")
    return p.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])

    input_path = args.input
    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_reuuid{ext}"

    print("=" * 60)
    print("  Base64 解析规则修改工具（执行型）")
    print(f"  输入: {input_path}")
    print(f"  输出: {output_path}")
    print(f"  name 改写: {('前缀=' + args.prefix) if args.prefix else ''}"
          f"{(' 后缀=' + args.suffix) if args.suffix else ''}"
          f"{' (仅换UUID,不改name)' if not (args.prefix or args.suffix) else ''}")
    print("=" * 60)

    if not os.path.exists(input_path):
        print(f"[ERROR] 文件不存在: {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        b64_data = f.read()

    result = process(b64_data, prefix=args.prefix, suffix=args.suffix)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"\n[DONE] 输出已写入: {output_path}")

    if args.verify:
        verify_result(result)


if __name__ == "__main__":
    main()
