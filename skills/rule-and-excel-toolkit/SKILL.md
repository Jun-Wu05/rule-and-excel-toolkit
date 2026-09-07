---
name: rule-and-excel-toolkit
description: 解析规则批处理与 Excel 日志数据加工的执行型工具集。适用于 Base64 解析规则 JSON 的层级编号、normalize 字段置空/删除、UUID 替换与引用同步、入口规则克隆、conditionMatch 规则链组装，以及设备/日志 Excel 的预检、字段提取、筛选、去重、拆 Sheet 和 IP 关联。脚本参数化、宿主无关，可由支持文件访问与 Python/命令执行能力的 Agent 调用。不用于普通文档、PPT、网页生成或与解析规则/日志 Excel 无关的通用编程。
---

# 解析规则与 Excel 日志加工工具集

## 1. Skill 定位

这是一个**执行型 Skill**。触发后应优先调用 `scripts/` 下已有能力完成任务，并返回最终结果文件，而不是只给用户脚本、伪代码或手工操作说明。

核心原则：

- **单 Skill、多能力域**：解析规则与 Excel 日志处理统一由本 Skill 管理。
- **宿主无关**：不绑定 DSH、Claude、Codex、GPT、OpenClaw、Hermes 或其他具体 Agent。
- **统一入口优先**：跨 Agent 调用优先使用 `scripts/toolkit.py`，独立脚本保留为兼容入口和业务实现层。
- **优先复用**：已有脚本能完成时，不重新实现同类逻辑。
- **参数适配优先**：字段名、前后缀、输出路径等差异优先通过 CLI 参数解决。
- **执行后验证**：任务完成前必须读取统一结果或脚本验证结果，确认输出可信。
- **保护原始数据**：除非用户明确要求，不覆盖原始输入文件。

跨 Agent 兼容说明见 `references/platform-compatibility.md`。

### 统一 CLI（优先）

跨 Agent 调用时，**优先使用 `scripts/toolkit.py` 作为稳定公共入口**；下方独立脚本继续保留为兼容入口和业务实现层。不要让宿主依赖各脚本不同的自然语言 stdout 判断结果。

```bash
python scripts/toolkit.py <rule|excel> <command> --input <path> [--output <path>] [业务参数...]
```

- Agent 推荐 `--format json`，读取带 `schema_version` 的结构化结果。
- 需要先确认调用计划时使用 `--dry-run`，不会执行脚本或写文件。
- 支持验证的命令使用 `--verify`。
- 新增正式能力必须注册到 `scripts/common/registry.py`，并遵循 `references/cli-contract.md`。
- 只有旧调用兼容、排障或直接开发业务脚本时，才直接调用具体 `scripts/*.py`。

当前统一命令：

| 能力 | 统一 CLI command |
|---|---|
| 规则层级编号 | `rule hierarchy` |
| 清空/删除 normalize field | `rule clear-field` |
| 替换 UUID | `rule reuuid` |
| 克隆入口规则 | `rule clone-entry` |
| 组装规则链 | `rule link` |
| Excel 预检 | `excel inspect` |
| Excel 字段提取 | `excel extract` |
| Excel 关键词筛选 | `excel filter` |
| Excel 按字段拆 Sheet | `excel split` |
| Excel 按列去重 | `excel dedup` |
| 设备日志 IP 关联 | `excel join` |

## 2. 标准执行流程

1. 识别输入类型：Base64 解析规则，或 Excel 文件。
2. 识别用户意图，并从下方选型表选择对应能力；优先映射到统一 CLI command。
3. Excel 的提取、去重、拆分类任务先执行 `excel inspect` 预检；旧入口等价于 `excel_inspect.py`。
4. 使用当前 Agent 可用的命令执行能力，优先通过 `scripts/toolkit.py` 运行对应命令；旧脚本 CLI 仅作为兼容入口。
5. 优先读取 `--format json` 的结构化结果；旧入口则读取脚本日志，检查行数、规则数、字段命中、UUID/引用、Sheet 数、诊断码等。
6. 能使用 `--verify`、`--verify-sample` 或等效诊断时应优先使用。
7. 验证通过后返回最终文件路径，并简要说明处理内容与验证结论。

不要因为宿主不同改变业务处理逻辑；宿主只决定“如何执行命令”，不决定“执行哪个业务逻辑”。

## 3. 运行环境

解析规则类脚本仅依赖 Python 标准库；Excel 类脚本需要 `pandas` + `openpyxl`。

Excel 任务先探测当前 Python：

```bash
python -c "import sys, pandas, openpyxl; print(sys.executable)"
```

处理规则：

1. 当前 Python 可用时直接复用。
2. 不可用时，可探测现有 conda/venv 环境。
3. 宿主支持环境缓存时，可复用已验证的 Python；不支持时重新探测即可。
4. 未经用户明确同意，不新建虚拟环境、不安装依赖。
5. 不把 `.dsh/`、PowerShell、Bash 或任一 Agent 专属机制作为本 Skill 的强制依赖。

## 4. 触发范围

### 解析规则

当用户提供 Base64 字符串或 Base64 txt，并要求：

- 按 `ref` 父子关系加层级编号；
- 给规则 name 加前缀/后缀；
- 清空或删除 `normalize[].field`；
- 替换顶层 UUID 并同步引用；
- 复制/克隆整批规则；
- 只克隆入口规则、子规则共享；
- 组装入口规则与子规则为 `conditionMatch` 规则链。

### Excel 日志

当用户要求：

- 预检 Excel 的 Sheet、列名、日志格式、字段分布；
- 从 JSON / 键值对日志提取多个字段；
- 按关键词筛选日志；
- 按字段值拆分多个 Sheet；
- 按指定列去重生成汇总 Sheet；
- 设备清单与多份日志按 IP 关联汇总。

### 不使用场景

- 与解析规则、日志 Excel 无关的普通编程；
- 普通文档、PPT、网页、图片生成；
- 已有专用 Skill 明显更匹配的任务。

## 5. 输入识别与脚本选型

| 输入 | 用户需求 | 统一命令 | 独立脚本兼容入口 |
|---|---|---|---|
| Base64 txt | 加层级编号 | `rule hierarchy` | `rule_hierarchy_number.py` |
| Base64 txt | 清空/删除 normalize field | `rule clear-field` | `rule_clear_field.py` |
| Base64 txt | 换 UUID / 复制整批规则 / 改 name | `rule reuuid` | `rule_replace_uuid.py` |
| Base64 txt | 只克隆入口规则 N 份，子规则共享 | `rule clone-entry` | `rule_clone_entry.py` |
| Base64 txt | 入口规则 + 子规则组装规则链 | `rule link` | `rule_link_conditionmatch.py` |
| .xlsx | 提取/去重/拆分前预检 | `excel inspect` | `excel_inspect.py` |
| 设备清单 + 日志 xlsx | 按 IP 关联汇总 | `excel join` | `excel_device_log_join.py` |
| .xlsx 含日志列 | 提取多个字段 | `excel extract` | `excel_extract_log_fields.py` |
| .xlsx 含日志列 | 关键词筛选 | `excel filter` | `excel_filter_logs.py` |
| .xlsx 含日志列 | 按字段值拆多个 Sheet | `excel split` | `excel_split_by_deviceaddress.py` |
| .xlsx 含日志列 | 按指定列分别去重 | `excel dedup` | `excel_dedup_sheets.py` |

不确定输入类型时，先检查文件或解码内容。Base64 解码后若为 JSON 数组，且元素包含 `id`、`name`、`normalize`、`parser` 等解析规则结构，则按解析规则处理。

## 6. 解析规则类脚本

以下独立脚本说明保留用于兼容、排障和业务实现理解；跨 Agent 正常执行优先使用统一 CLI。

### 6.1 `rule_hierarchy_number.py`

按递归 `ref` 关系还原层级，为 name 加多级编号，例如 `01_`、`0101_`，深度不限；自动清洗旧编号与旧前缀，避免重复叠加。

```bash
python scripts/rule_hierarchy_number.py <输入.txt> [输出.txt] [--prefix 前缀]
```

- `--prefix ""`：只加数字编号，不加业务前缀。
- 输出默认加 `_层级编号` 后缀。

### 6.2 `rule_clear_field.py`

处理 `normalize` 数组中 `field` 完全匹配的条目。

```bash
python scripts/rule_clear_field.py <输入.txt> <输出.txt> location_country
python scripts/rule_clear_field.py <输入.txt> <输出.txt> location_country --mode remove
python scripts/rule_clear_field.py <输入.txt> <输出.txt> --fields=location_country,location_province
```

术语映射：

| 用户原话 | 默认解释 | mode |
|---|---|---|
| 清空 / 置空 / 让字段失效 | field 值改为空字符串，条目保留 | `clear` |
| 删掉 / 去掉 / 删除字段（未强调条目） | 默认仍按置空理解 | `clear` |
| 删除整个条目 / 移除归一化项 | 条目从 normalize 消失 | `remove` |

注意：同名字段还可能出现在 `parser.filter[].fields` 中。本脚本只处理 `normalize`。若用户明确要求同时处理其他位置，应先确认范围。

### 6.3 `rule_replace_uuid.py`

替换每条顶层规则 `id`，并递归同步所有指向旧 UUID 的引用；可同时修改顶层 name。不会修改 `deviceType.id`、`filter.id`、`deviceType.name`、`parser.name` 等非顶层对象。

```bash
python scripts/rule_replace_uuid.py <输入.txt> [输出.txt] [--prefix 前缀] [--suffix 后缀] [--verify] [--prefix-only]
```

- 只加 name 前后缀且 UUID 不动：使用 `--prefix-only`。
- “复制/克隆整批规则”默认走 UUID 替换模式。
- 重要任务建议带 `--verify`。

### 6.4 `rule_clone_entry.py`

仅克隆入口规则（`subResolver=0`）N 份；子规则原样保留、UUID 不变。副本顶层 `id` 与 redirect 内嵌 analyzer `rule.id` 会重新生成，`case.rule.ref` 继续引用原子规则。

```bash
python scripts/rule_clone_entry.py <输入.txt> [输出.txt] [--suffixes _new1,_new2]
```

它与 `rule_replace_uuid.py` 的区别：后者处理整批规则 UUID；本脚本只克隆入口规则。

### 6.5 `rule_link_conditionmatch.py`

识别入口规则（`subResolver=0`）和子规则（`subResolver=1`），在入口规则 `parser.filter` 中构建 `conditionMatch`，把子规则 UUID 写入 `cases[].rule.ref`。

```bash
python scripts/rule_link_conditionmatch.py <输入.txt> [输出.txt]
```

当前脚本默认生成 `original_log like 'xxx'` 占位条件。若用户已提供具体匹配值，不应把 `'xxx'` 当作最终交付；应明确剩余手工项，或在脚本能力支持后传入真实条件。

## 7. Excel 类脚本

以下独立脚本说明同样作为兼容入口；统一 CLI 会负责公共参数、JSON 输出和退出码。

### 7.1 `excel_inspect.py`

提取、去重、拆分类任务必须优先预检：Sheet、列名、行列数、日志格式、目标字段出现率/非空率、空日志行和 32767 字符截断风险。

```bash
python scripts/excel_inspect.py <输入.xlsx> [--log-column 原始日志] [--fields f1,f2,...] [--sample 200]
```

预检只读，不修改文件。

### 7.2 `excel_device_log_join.py`

按设备 IP 将一份设备清单与多份日志关联，输出汇总、全量明细和按 IP 拆分 Sheet。

```bash
python scripts/excel_device_log_join.py <设备清单.xlsx> <输出.xlsx> <日志1.xlsx> [日志2.xlsx ...]
```

列名差异优先使用现有 `--*-col` 参数适配，不修改源码。

### 7.3 `excel_extract_log_fields.py`

支持 JSON 与键值对两类日志，保留原始列并追加提取列；包含 JSON 解析、正则兜底与诊断信息。

```bash
python scripts/excel_extract_log_fields.py <输入.xlsx> [输出.xlsx] \
  [--log-column 原始日志] [--fields f1,f2,...] [--no-diag] [--verify-sample 20]
```

重要任务建议使用 `--verify-sample N` 做独立回对。

诊断码：

- `OK`：正常。
- `EMPTY_INPUT`：日志为空。
- `REGEX_MISS(...)`：部分目标字段未匹配。
- `TRUNCATED_TAIL`：当前单元格达到 Excel 长度上限或表现出疑似截断，应视为**截断风险**，不能仅凭当前文件恢复缺失内容。

### 7.4 `excel_filter_logs.py`

按指定列中的关键词筛选日志行。

```bash
python scripts/excel_filter_logs.py <输入.xlsx> [输出.xlsx] [--keyword 关键词] [--column 列名]
```

### 7.5 `excel_split_by_deviceaddress.py`

按指定字段值分组拆 Sheet，同时输出原始全量数据和该字段去重 Sheet。

```bash
python scripts/excel_split_by_deviceaddress.py <输入.xlsx> <输出.xlsx> \
  [--log-column 原始日志] [--fields f1,f2,...] [--split-field 字段]
```

默认 `--split-field deviceAddress`，也可指定其他已存在或已提取字段。

### 7.6 `excel_dedup_sheets.py`

按一个或多个指定列分别去重，每列生成一个 `<列名>去重` Sheet，同时保留全量数据。

```bash
python scripts/excel_dedup_sheets.py <输入.xlsx> <输出.xlsx> \
  [--log-column 原始日志] [--fields log_msg] --dedup-cols 列1,列2
```

与 split 脚本区别：split 是“每个字段值一个 Sheet”；dedup 是“每个指定列一个去重 Sheet”。

## 8. 歧义处理

### name 前缀、层级编号、UUID 复制不要混用

| 用户表达 | 实际含义 | 处理方式 |
|---|---|---|
| 加前缀 / 加后缀 | 只改顶层 name | `rule reuuid --prefix-only` |
| 加层级编号 / 01_ / 0101_ | 按 ref 生成编号 | `rule hierarchy` |
| 换 UUID / 重新出规则 ID / 复制整批规则 | 顶层 UUID 全换并同步引用 | `rule reuuid` |
| 只复制入口规则 | 子规则共享不变 | `rule clone-entry` |

缺少真正阻塞执行的关键参数时只问一次；能通过预检、脚本默认值或现有文件结构推断的，不重复询问。

## 9. 验证标准

### 解析规则

至少检查：

- 输入/输出规则数量是否符合任务预期；
- 顶层 UUID 替换数量是否正确；
- name 改写数量是否正确；
- 子规则引用是否仍指向正确 UUID；
- 处理前后的未知引用集合。

对于外部 UUID：原始文件已有的未知引用可以保留，但**处理后不得新增未知引用**。可按集合判断：

```text
new_unknown_refs = unknown_refs_after - unknown_refs_before
```

`new_unknown_refs` 必须为空；否则视为新断链，不应直接交付。

### Excel

至少根据任务检查：

- 输入行数与输出行数；
- 目标字段非空数量/比例；
- Sheet 数量与唯一值数量；
- 筛选命中数或去重结果数；
- `_diag` / 诊断码分布；
- `--verify-sample` 抽查通过率；
- 截断风险行数量。

不能只因为脚本退出码为 0 就认定业务结果正确。

## 10. 代码与扩展边界

- 已有脚本能完成的任务，禁止临时重写一份同功能实现。
- 列名不匹配时优先通过 CLI 参数调整，不修改源码。
- 新需求优先扩展现有脚本参数或公共解析策略。
- 新增正式能力时必须同步注册到 `scripts/common/registry.py`，让统一 CLI、JSON 输出和 CI contract 自动覆盖该能力。
- 禁止通过复制脚本形成 `_new`、`_v2`、`_final`、客户名后缀等长期变体。
- 只有现有脚本架构明显无法容纳的新能力，才新增独立脚本，并同步更新 registry、SKILL.md、README/文档和 CHANGELOG。
- 若必须临时应急实现，应明确告知用户它不是标准能力，后续应收敛回正式脚本。

## 11. 输出要求

统一 CLI 模式下优先读取结构化结果：

- `status`
- `command`
- `input`
- `output`
- `stats`
- `verification`
- `warnings`
- `error`
- `schema_version`

任务完成后至少告诉用户：

1. 做了什么处理；
2. 输入/输出的关键统计；
3. 验证是否通过；
4. 是否存在截断、未匹配、外部引用或其他风险；
5. 最终结果文件路径；
6. 是否仍有手工项，例如 `conditionMatch` 中尚未替换的 `'xxx'`。

不要覆盖原始输入；除非用户明确要求，否则输出文件使用新文件名。