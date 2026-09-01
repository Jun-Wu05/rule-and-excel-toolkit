"""
=============================================================================
脚本名称: 绿盟IDS规则链组装器 (conditionMatch 精准结构版)
功能描述:
    1. 读取Base64编码的TXT文件，解码获取多条独立规则
    2. 自动识别入口规则(subResolver=0)与子规则(subResolver=1)
    3. 在入口规则parser.filter中构建标准conditionMatch过滤器
       cases[].value = "{field} like 'xxx'"
       cases[].rule.ref = [子规则UUID]
    4. 严格保留原始UUID和name，仅修改拓扑连接关系
    5. 结果重新Base64编码后写入TXT文件
依赖: Python 3.6+ (仅使用标准库)
=============================================================================
"""

import json
import base64
import copy
import uuid
import os
import sys

# ======================== 配置区 ========================
INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"
CONDITION_MATCH_NAME = "conditionMatch"   # 固定名称，引擎识别关键字
DEFAULT_FIELD = "original_log"            # normalize无有效字段时的兜底值
# ========================================================


def extract_field_and_samples(entry_rule: dict) -> tuple:
    """
    从入口规则normalize中提取field和所有sample值
    返回: (field, [sample_values])
    """
    normalize_list = entry_rule.get('normalize')
    field = DEFAULT_FIELD
    samples = []

    if isinstance(normalize_list, list):
        for item in normalize_list:
            if not isinstance(item, dict):
                continue
            f = item.get('field')
            if f:
                field = f
            # 收集该normalize条目下的所有sample/result值作为case的匹配值
            result_vals = item.get('result')
            if isinstance(result_vals, list):
                samples.extend([str(v) for v in result_vals if v is not None])

    # 去重并保持顺序
    seen = set()
    unique_samples = []
    for s in samples:
        if s not in seen:
            seen.add(s)
            unique_samples.append(s)

    return field, unique_samples


def build_condition_match_filter(sub_rules: list, field: str) -> dict:
    """
    构建标准conditionMatch过滤器
    cases数量 = 子规则数量
    case.value = "{field} like '{sample}'" (sample循环使用)
    case.rule.ref = [对应子规则UUID]
    """
    cases = []
    # 如果没有sample值，用子规则序号作为默认匹配值
    sample_pool = None  # 延迟获取

    for i, sub_rule in enumerate(sub_rules):
        sub_id = sub_rule.get('id')
        if not sub_id:
            continue

        # 确定当前case的匹配值
        if sample_pool is None:
            # 注意：这里无法拿到entry_rule，所以sample由外部传入更合理
            # 但为保持接口简洁，当无sample时用序号兜底
            match_val = str(i + 1)
        else:
            match_val = sample_pool[i % len(sample_pool)] if sample_pool else str(i + 1)

        case_item = {
            "value": f"{field} like 'xxx'",
            "rule": {
                "name": "analyzer",
                "field": field,
                "normalize": True,
                "parser": {
                    "name": "nothing",
                    "resolverType": "event",
                    "unmappingKeep": False,
                    "deviceType": "1",
                    "filter": [
                        {
                            "fields": {
                                "product": "",
                                "event_name": "",
                                "event_level": "",
                                "log_vendor": ""
                            },
                            "name": "addFields",
                            "id": "additional_fields_filter"
                        }
                    ],
                    "subResolver": 1
                },
                "ref": [sub_id],
                "id": str(uuid.uuid4())
            },
            "name": "case",
            "id": ""
        }
        cases.append(case_item)

    return {
        "name": CONDITION_MATCH_NAME,
        "id": "",
        "default": {
            "name": "none"
        },
        "cases": cases
    }


def build_condition_match_filter_with_samples(sub_rules: list, field: str, samples: list) -> dict:
    """所有case的value固定为 original_log like 'xxx'"""
    cases = []
    for sub_rule in sub_rules:
        sub_id = sub_rule.get('id')
        if not sub_id:
            continue

        cases.append({
            "value": "original_log like 'xxx'",   # ← 完全固定，不再拼接
            "rule": {
                "name": "analyzer",
                "field": "original_log",          # ← 同步固定
                "normalize": True,
                "parser": {
                    "name": "nothing",
                    "resolverType": "event",
                    "unmappingKeep": False,
                    "deviceType": "1",
                    "filter": [{
                        "fields": {
                            "product": "", "event_name": "",
                            "event_level": "", "log_vendor": ""
                        },
                        "name": "addFields",
                        "id": "additional_fields_filter"
                    }],
                    "subResolver": 1
                },
                "ref": [sub_id],
                "id": str(uuid.uuid4())
            },
            "name": "case",
            "id": ""
        })

    return {
        "name": CONDITION_MATCH_NAME,
        "id": "",
        "default": {"name": "none"},
        "cases": cases
    }


def link_rules(data_array: list) -> list:
    """将独立规则通过conditionMatch组装为规则链"""
    result = copy.deepcopy(data_array)

    entry_rules = []
    sub_rules = []

    for idx, rule in enumerate(result):
        if not isinstance(rule, dict):
            continue
        if rule.get('subResolver', 1) == 0:
            entry_rules.append((idx, rule))
        else:
            sub_rules.append(rule)

    if not entry_rules:
        print("[WARN] 未找到入口规则(subResolver=0)，跳过组装")
        return result
    if not sub_rules:
        print("[WARN] 未找到子规则(subResolver=1)，跳过组装")
        return result

    print(f"[INFO] 发现 {len(entry_rules)} 个入口规则, {len(sub_rules)} 个子规则")
    for s in sub_rules:
        print(f"       子规则: {s.get('name')} ({s.get('id')})")

    for idx, entry in entry_rules:
        parser = entry.get('parser')
        if not isinstance(parser, dict):
            print(f"[WARN] 入口 [{entry.get('name')}] 缺少parser，跳过")
            continue

        field, samples = extract_field_and_samples(entry)
        print(f"[INFO] 入口 [{entry.get('name')}] field='{field}', samples={samples}")

        cm_filter = build_condition_match_filter_with_samples(sub_rules, field, samples)

        filters = parser.get('filter')
        if not isinstance(filters, list):
            parser['filter'] = []
            filters = parser['filter']

        # 幂等：查找已有conditionMatch并覆盖
        existing_idx = None
        for i, f in enumerate(filters):
            if isinstance(f, dict) and f.get('name') == CONDITION_MATCH_NAME:
                existing_idx = i
                break

        if existing_idx is not None:
            filters[existing_idx] = cm_filter
            print(f"[INFO] 更新入口 [{entry.get('name')}] 已有conditionMatch")
        else:
            filters.append(cm_filter)
            print(f"[INFO] 入口 [{entry.get('name')}] 新增conditionMatch，挂载 {len(sub_rules)} 个子规则")

    return result


def main():
    import argparse
    p = argparse.ArgumentParser(description="用 conditionMatch 把入口规则与子规则组装成规则链")
    p.add_argument("input", nargs="?", default=INPUT_FILE, help="输入文件（Base64），默认 input.txt")
    p.add_argument("output", nargs="?", default=None, help="输出文件，默认输入同名加 _规则链")
    args = p.parse_args(sys.argv[1:])

    input_path = args.input
    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_规则链{ext}"

    print(f"[INFO] 正在读取 {input_path} ...")
    with open(input_path, 'r', encoding='utf-8') as f:
        b64_content = f.read().strip()

    if not b64_content:
        raise ValueError(f"输入文件 {input_path} 为空")

    try:
        json_bytes = base64.b64decode(b64_content)
        data_array = json.loads(json_bytes.decode('utf-8'))
    except base64.binascii.Error as e:
        raise ValueError(f"Base64解码失败: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"解码后内容不是合法JSON: {e}")

    print(f"[INFO] 解码成功，共 {len(data_array)} 条规则")

    linked_data = link_rules(data_array)

    # 验证
    print("\n[INFO] ===== 组装结果验证 =====")
    for rule in linked_data:
        name = rule.get('name', '?')
        sub = rule.get('subResolver', '?')
        tag = "入口" if sub == 0 else "子规则"
        info = ""
        parser = rule.get('parser', {})
        for f in parser.get('filter', []):
            if isinstance(f, dict) and f.get('name') == CONDITION_MATCH_NAME:
                cases_summary = []
                for c in f.get('cases', []):
                    val = c.get('value', '?')
                    refs = c.get('rule', {}).get('ref', [])
                    cases_summary.append(f"{val}→{refs}")
                info = f" | conditionMatch: {cases_summary}"
        print(f"       [{tag}] {name}{info}")

    result_json = json.dumps(linked_data, ensure_ascii=False, indent=4)
    result_b64 = base64.b64encode(result_json.encode('utf-8')).decode('utf-8')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_b64)

    print(f"\n[INFO] 已写入 {output_path} (Base64编码)")


if __name__ == '__main__':
    main()