#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行型脚本：按 rule id 复制一条规则 N 份（独立副本）。

与 rule_clone_entry.py（克隆入口规则、子规则共享）、rule_replace_uuid.py（整批 1:1 换 UUID）的区别：
- 本脚本精确选中一条规则（通常是一条自包含的“子规则”）；深拷贝 N 份，追加到数组末尾。
- 每份副本：顶层 id 换成新 UUID，name 尾部加后缀（默认 _copy1/_copy2/...）。
- 不接线：入口规则与其他规则原样不动；副本不被任何规则引用，属于独立副本。

用法：
    python rule_clone_rule.py <输入.txt> [输出.txt] --rule-id <uuid> --count <N> [--suffix _copy]
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


def main():
    ap = argparse.ArgumentParser(description="按 id 复制一条规则 N 份（独立副本）")
    ap.add_argument("input")
    ap.add_argument("output", nargs="?", default=None)
    ap.add_argument("--rule-id", required=True, help="要复制的规则的顶层 id（uuid）")
    ap.add_argument("--count", type=int, required=True, help="复制份数（>=1）")
    ap.add_argument("--suffix", default="_copy", help="副本 name 后缀前缀，默认 _copy（生成 _copy1.._copyN）")
    args = ap.parse_args()

    if args.count < 1:
        print("[ERROR] --count 必须 >= 1")
        sys.exit(1)

    input_path = args.input
    output_path = args.output
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_规则复制{ext}"

    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()
    clean = raw.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    try:
        rules = json.loads(base64.b64decode(clean))
    except Exception as exc:
        print(f"[ERROR] Base64 解码失败：{exc}")
        sys.exit(1)

    if not isinstance(rules, list):
        print("[ERROR] 解码后不是 JSON 数组")
        sys.exit(1)

    print(f"[INFO] 共 {len(rules)} 条规则，目标 id={args.rule_id}，复制 {args.count} 份")

    matches = [r for r in rules if isinstance(r, dict) and r.get("id") == args.rule_id]
    if len(matches) != 1:
        if len(matches) == 0:
            print(f"[ERROR] 未找到 id={args.rule_id} 的规则")
        else:
            print(f"[ERROR] id={args.rule_id} 匹配到 {len(matches)} 条规则（应唯一）")
        sys.exit(1)

    source = matches[0]

    clones = []
    for i in range(1, args.count + 1):
        c = copy.deepcopy(source)
        old_id = c.get("id")
        new_id = gen()
        c["id"] = new_id
        c["name"] = f"{c.get('name', '')}{args.suffix}{i}"
        clones.append(c)
        print(f"[INFO] 副本{i:02d}：{source.get('name')} -> {c['name']}"
              f"（id {old_id} -> {new_id}）")

    out_rules = list(rules) + clones

    # ===== 验证 =====
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    print(f"输出规则总数：{len(out_rules)}（期望 {len(rules) + len(clones)}）")

    all_ids = [r.get("id") for r in out_rules if isinstance(r, dict)]
    dup = len(all_ids) - len(set(all_ids))
    print(f"顶层规则 id 唯一性：重复 {dup} 个{'（全部唯一）' if dup == 0 else '（有重复！）'}")
    print(f"注意：{len(clones)} 个副本为独立副本，未被任何规则引用（按需自行挂载）")
    ok = dup == 0
    print("=" * 60)
    print("结论：" + ("✅ 全部通过" if ok else "⚠️ 有异常，请检查"))

    print(f"[STATS] copied = {len(clones)}")
    print(f"[STATS] source_id = {source.get('id')}")

    result_json = json.dumps(out_rules, ensure_ascii=False, separators=(",", ":"))
    result_b64 = base64.b64encode(result_json.encode("utf-8")).decode("ascii")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result_b64)

    print(f"\n[DONE] 输出已写入：{output_path}")


if __name__ == "__main__":
    main()
