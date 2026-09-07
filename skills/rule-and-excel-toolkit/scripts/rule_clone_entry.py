#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性变体脚本：只克隆入口规则（subResolver=0），子规则保持不变。
- 入口规则深拷贝 N 份，副本 name 加后缀（如 _new1/_new2）
- 副本顶层 id 换成新 UUID；内嵌 redirect case 的 analyzer rule.id 也重生成
- 副本继续通过 case.rule.ref 引用同一批子规则 UUID（子规则一字不改，UUID 不变）
- 输出 = 原子规则 + 原入口规则 + 各副本（共 14 条）

用法：
    python rule_clone_entry.py <输入.txt> [输出.txt] [--suffixes _new1,_new2]
"""
import base64
import json
import uuid
import os
import sys
import copy
import argparse


def gen() -> str:
    return str(uuid.uuid4())


def collect_refs(rule) -> set:
    """收集入口规则 redirect filter 里所有 case.rule.ref 引用的子规则 UUID"""
    refs = set()
    p = rule.get("parser") if isinstance(rule, dict) else None
    if isinstance(p, dict):
        for filt in p.get("filter") or []:
            if isinstance(filt, dict):
                for case in filt.get("cases") or []:
                    ru = case.get("rule")
                    if isinstance(ru, dict):
                        for r in ru.get("ref") or []:
                            if isinstance(r, str):
                                refs.add(r)
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output", nargs="?", default=None)
    ap.add_argument("--suffixes", default="_new1,_new2")
    args = ap.parse_args()

    input_path = args.input
    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_入口复制{ext}"

    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()
    clean = raw.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    rules = json.loads(base64.b64decode(clean))

    if not isinstance(rules, list):
        print("[ERROR] 解码后不是 JSON 数组")
        sys.exit(1)

    entry_rules = [r for r in rules if isinstance(r, dict) and r.get("subResolver") == 0]
    child_rules = [r for r in rules if isinstance(r, dict) and r.get("subResolver") != 0]
    print(f"[INFO] 共 {len(rules)} 条规则：入口 {len(entry_rules)} 条 / 子规则 {len(child_rules)} 条")
    if len(entry_rules) != 1:
        print(f"[WARN] 入口规则数量 = {len(entry_rules)}（预期 1）")

    child_ids = {c["id"] for c in child_rules if isinstance(c, dict) and c.get("id")}
    suffixes = [s for s in args.suffixes.split(",") if s]
    print(f"[INFO] 克隆副本后缀：{suffixes}")

    clones = []
    for e in entry_rules:
        for sfx in suffixes:
            c = copy.deepcopy(e)
            old_id = c.get("id")
            new_id = gen()
            c["id"] = new_id
            c["name"] = f"{c.get('name', '')}{sfx}"
            n_analyzer = 0
            p = c.get("parser")
            if isinstance(p, dict):
                for filt in p.get("filter") or []:
                    if isinstance(filt, dict):
                        for case in filt.get("cases") or []:
                            ru = case.get("rule")
                            if isinstance(ru, dict) and "id" in ru:
                                ru["id"] = gen()
                                n_analyzer += 1
            clones.append(c)
            print(f"[INFO] 副本 {sfx}：{e.get('name')} -> {c['name']}"
                  f"（id {old_id} -> {new_id}，重生成内嵌 analyzer id {n_analyzer} 个）")

    out_rules = list(child_rules) + list(entry_rules) + clones

    # ===== 验证 =====
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    print(f"输出规则总数：{len(out_rules)}（期望 {len(rules) + len(clones)}）")
    for idx, r in enumerate(out_rules):
        print(f"规则{idx + 1:02d}  subResolver={r.get('subResolver')}  name={r.get('name')}")
        print(f"          id={r.get('id')}")

    # 子规则 UUID 是否原样保留
    out_child_ids = {c["id"] for c in child_rules if isinstance(c, dict) and c.get("id")}
    print(f"\n子规则 UUID 保持一致：{out_child_ids == child_ids}（{len(out_child_ids)} 个）")

    # 每条入口规则（原 + 副本）引用完整性
    ok = True
    for idx, r in enumerate(out_rules):
        if r.get("subResolver") == 0:
            refs = collect_refs(r)
            missing = refs - child_ids
            extra = child_ids - refs
            status = "✅ 引用完整（覆盖全部 11 条子规则）" if (not missing and not extra) else \
                f"⚠️ 缺 {len(extra)} / 悬空 {len(missing)}"
            print(f"入口规则「{r.get('name')}」引用子规则 {len(refs)} 处 → {status}")
            if missing or extra:
                ok = False

    # 顶层 id 唯一性
    all_ids = [r.get("id") for r in out_rules]
    dup = len(all_ids) - len(set(all_ids))
    print(f"顶层规则 id 唯一性：重复 {dup} 个{'（全部唯一）' if dup == 0 else '（有重复！）'}")
    if dup:
        ok = False

    print("=" * 60)
    print("结论：" + ("✅ 全部通过" if ok else "⚠️ 有异常，请检查"))

    result_json = json.dumps(out_rules, ensure_ascii=False, separators=(",", ":"))
    result_b64 = base64.b64encode(result_json.encode("utf-8")).decode("ascii")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result_b64)

    print(f"\n[DONE] 输出已写入：{output_path}")


if __name__ == "__main__":
    main()
