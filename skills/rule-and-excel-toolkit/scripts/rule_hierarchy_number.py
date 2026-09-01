"""
=============================================================================
脚本名称: 绿盟IDS规则层级编号生成器 (Base64 TXT 输入输出最终版)
功能描述:
    1. 从TXT文件读取Base64编码的JSON数据并解码
    2. 通过深度递归提取JSON中任意嵌套位置的ref字段，100%准确构建规则层级树
    3. 基于构建的层级树自动生成多层级编号（支持无限深度）
    4. 自动清洗旧编号与前缀，防止重复叠加
    5. 将结果重新Base64编码后写入TXT文件
编号规则:
    第1层: 01_浦发银行_xxx
    第2层: 0101_浦发银行_xxx
    第3层: 010201_浦发银行_xxx
    第N层: 依次追加2位序号
依赖: Python 3.6+ (仅使用标准库)
=============================================================================
"""

import json
import re
import base64
import os
import sys
import argparse
from collections import defaultdict

# ======================== 配置区（命令行未传时兜底） ========================
NAME_PREFIX = "浦发银行_"
INPUT_FILE = "input.txt"          # Base64编码的TXT输入文件
OUTPUT_FILE = "output.txt"        # Base64编码的TXT输出文件
# ======================================================================


def build_hierarchy_by_ref(data_array: list) -> tuple:
    """
    纯ref驱动的层级构建（深度递归提取版）
    彻底解决嵌套在 cases/default/rule/parser 中的 ref 丢失问题

    Returns:
        children_map: {父索引: [子索引列表]}
        root_indices: 根节点索引列表
        id_to_idx: {规则ID: 索引} 映射
    """
    id_to_idx = {}
    parent_of = {}
    children_map = defaultdict(list)

    # 1. 建立 ID → 索引映射
    for idx, rule in enumerate(data_array):
        if isinstance(rule, dict) and rule.get('id'):
            id_to_idx[rule['id']] = idx

    # 2. 深度递归提取所有ref（无差别遍历dict/list）
    def extract_all_refs(obj, refs_set: set):
        if isinstance(obj, dict):
            if 'ref' in obj and isinstance(obj['ref'], list):
                for r in obj['ref']:
                    if isinstance(r, str) and r.strip():
                        refs_set.add(r.strip())
            for v in obj.values():
                extract_all_refs(v, refs_set)
        elif isinstance(obj, list):
            for item in obj:
                extract_all_refs(item, refs_set)

    # 3. 遍历每条规则，通过ref建立父子关系
    for idx, rule in enumerate(data_array):
        if not isinstance(rule, dict):
            continue
        refs_found = set()
        extract_all_refs(rule, refs_found)
        current_id = rule.get('id')
        for ref_id in refs_found:
            if ref_id != current_id and ref_id in id_to_idx:
                child_idx = id_to_idx[ref_id]
                if child_idx not in parent_of:
                    parent_of[child_idx] = idx
                    children_map[idx].append(child_idx)

    # 4. 识别根节点
    all_indices = set(range(len(data_array)))
    child_set = set(parent_of.keys())
    root_indices = sorted(all_indices - child_set)

    # 5. 调试输出
    print(f"[INFO] 通过ref构建了 {len(parent_of)} 条父子关系")
    for p_idx, kids in sorted(children_map.items()):
        p_name = data_array[p_idx].get('name', '?')
        for k in sorted(kids):
            k_name = data_array[k].get('name', '?')
            print(f"       {p_name} → {k_name}")
    print(f"[INFO] 识别到 {len(root_indices)} 个根节点")
    for r in root_indices:
        print(f"       根节点: {data_array[r].get('name', '?')}")

    return children_map, root_indices, id_to_idx


def generate_numbered_names(data_array: list, children_map: dict, root_indices: list, name_prefix: str = None) -> dict:
    """
    基于ref构建的准确层级树生成编号（支持任意深度）
    所有层级均加编号，不再跳过任何深度
    name_prefix: 名称前缀，默认用模块级 NAME_PREFIX
    """
    if name_prefix is None:
        name_prefix = NAME_PREFIX
    name_map = {}

    def clean_old_prefix(name: str) -> str:
        """去除旧的编号和名称前缀，防止重复叠加"""
        clean = name
        if name_prefix and clean.startswith(name_prefix):
            clean = clean[len(name_prefix):]
        clean = re.sub(r'^\d{2,8}_', '', clean)
        return clean

    def traverse(idx: int, code: str, depth: int):
        rule = data_array[idx]
        old_name = str(rule.get('name', ''))
        clean_name = clean_old_prefix(old_name)
        new_name = f"{code}_{name_prefix}{clean_name}" if name_prefix else f"{code}_{clean_name}"
        name_map[idx] = new_name

        child_indices = sorted(children_map.get(idx, []))
        for seq, child_idx in enumerate(child_indices, start=1):
            child_code = f"{code}{seq:02d}"
            traverse(child_idx, child_code, depth + 1)

    # 从每个根节点开始遍历
    for root_seq, root_idx in enumerate(sorted(root_indices), start=1):
        root_code = f"{root_seq:02d}"
        traverse(root_idx, root_code, 1)

    # 兜底：未被遍历到的孤立节点
    assigned = set(name_map.keys())
    orphan_seq = 99
    for idx in range(len(data_array)):
        if idx not in assigned:
            old_name = str(data_array[idx].get('name', ''))
            clean_name = clean_old_prefix(old_name)
            name_map[idx] = f"{orphan_seq}_{name_prefix}{clean_name}" if name_prefix else f"{orphan_seq}_{clean_name}"
            orphan_seq += 1

    return name_map


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="按 ref 层级关系给解析规则 name 生成多级编号前缀",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", nargs="?", default=INPUT_FILE, help="输入文件（Base64），默认 input.txt")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _层级编号")
    p.add_argument("--prefix", default=None, help="名称前缀，如 浦发银行_；不传则用脚本内置默认，传空字符串则不加前缀")
    return p.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    input_path = args.input
    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_层级编号{ext}"

    # 命令行传了 --prefix（含空串）就覆盖，否则用模块默认
    name_prefix = NAME_PREFIX if args.prefix is None else args.prefix

    print(f"[INFO] 正在读取 {input_path} ...")
    with open(input_path, 'r', encoding='utf-8') as f:
        b64_content = f.read().strip()

    if not b64_content:
        raise ValueError(f"输入文件 {input_path} 为空，请检查文件内容")

    try:
        json_bytes = base64.b64decode(b64_content)
        data_array = json.loads(json_bytes.decode('utf-8'))
    except base64.binascii.Error as e:
        raise ValueError(f"Base64解码失败，请确认文件内容为合法的Base64字符串: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Base64解码后的内容不是合法JSON: {e}")

    print(f"[INFO] Base64解码成功，共 {len(data_array)} 条规则")

    # 构建层级
    print("[INFO] 正在分析规则层级关系...")
    children_map, root_indices, _ = build_hierarchy_by_ref(data_array)

    # 生成编号
    print(f"[INFO] 正在生成层级编号 (前缀='{name_prefix}')...")
    name_map = generate_numbered_names(data_array, children_map, root_indices, name_prefix=name_prefix)

    # 应用编号并打印结果
    for idx in sorted(name_map.keys()):
        old_name = data_array[idx].get('name', '')
        new_name = name_map[idx]
        data_array[idx]['name'] = new_name
        print(f"       [{idx}] {old_name} → {new_name}")

    # 重新Base64编码并写入
    result_json = json.dumps(data_array, ensure_ascii=False, indent=4)
    result_b64 = base64.b64encode(result_json.encode('utf-8')).decode('utf-8')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_b64)

    print(f"[INFO] 已写入 {output_path} (Base64编码)")


if __name__ == '__main__':
    main()