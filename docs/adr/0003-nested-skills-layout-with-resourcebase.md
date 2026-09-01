# 3. 嵌套 skills/<name>/ 布局，resourceBase 指向 skill 目录

- 状态：已接受
- 日期：2026-09-01

## 背景

SKILL.md 正文以相对路径引用 `scripts/*.py`；DSH 加载 skill 时通过 `resourceBase` 解析这些相对引用，脚本必须和 SKILL.md 在同一可解析目录下。仓库布局有两种：

- **(A) 嵌套式**：`skills/rule-and-excel-toolkit/{SKILL.md, scripts/}`，provider 扫描 `skills/`。
- **(B) 平铺式**：`SKILL.md` + `scripts/` 直接位于仓库根，provider 指向根目录。

## 决策

采用 **(A)** 嵌套式布局；provider 把 `resourceBase` 设为 `skills/rule-and-excel-toolkit/`（directory 类型）。

## 后果

- ✅ 与 DSH 打包 skill 的标准形态一致；未来加第二个 skill 只是往 `skills/` 丢目录，provider 不用改。
- ✅ `resourceBase` 让 `scripts/xxx.py` 相对引用按 skill 定义解析。
- ⚠️ 原始 `SKILL.md` 与 `scripts/` 从仓库根下移了一层。
