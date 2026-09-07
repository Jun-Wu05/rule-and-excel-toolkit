# CONTEXT.md — 领域词汇表

本文件是 `rule-and-excel-toolkit` 的领域术语表（glossary）。只记录术语的精确定义，不含实现细节；实现与用法见 `skills/rule-and-excel-toolkit/SKILL.md`。

## 解析规则侧

- **解析规则（rule）**：一段 Base64 编码的 JSON 数组；解码后每条规则是一个 dict，关键字段为 `id`、`name`、`normalize`、`parser`、`ref`。是解析规则的导出/交换形态。
- **顶层规则（top-level rule）**：Base64 解码后的 JSON 数组中的直接元素。脚本中的“替换顶层 UUID”仅针对这些规则对象的顶层 `id`，不代表它一定是规则链根节点，也不等同于“入口规则”。
- **子规则（sub-rule）**：`subResolver=1` 的规则；通常通过 `ref` 或 conditionMatch 挂接到其它规则之下。
- **入口规则（entry rule）**：`subResolver=0` 的规则；通常作为规则链起点，与“顶层规则”概念不同。
- **ref（引用）**：规则中引用其它规则 UUID 的字段；替换 UUID 时必须同步所有指向被替换 UUID 的内部引用。
- **外部引用（external ref）**：当前导出文件中找不到目标规则对象的 UUID 引用。原文件已有外部引用可以保留，但处理后不得新增未知引用。
- **normalize（归一化数组）**：规则内一串归一化条目，每条含 `field` 等字段；“清空/删除字段”默认针对其中的 `field`。
- **conditionMatch**：入口规则 `parser.filter` 中的条件匹配过滤器；可把子规则 UUID 挂到 `cases[].rule.ref`，形成规则链。
- **规则链（rule chain）**：入口规则与子规则通过 conditionMatch 等引用关系连接形成的规则拓扑。
- **字面前缀（literal prefix）／后缀（suffix）**：直接加在规则 `name` 前/后的固定文本，如 `启明星辰_数据库审计_`；不含数字层级含义，区别于“层级编号”。
- **层级编号（hierarchy number）**：按 `ref` 父子层级给规则 `name` 生成的数字前缀，如 `01_`、`0101_`；反映层级，而非纯字面前缀。
- **复制整批规则／克隆整批规则（clone rule set）**：需要为当前规则集合生成一套新的顶层 UUID，并同步内部引用；可同时修改顶层 `name`。默认由 `rule_replace_uuid.py` 处理。
- **只克隆入口规则（clone entry rule only）**：只复制 `subResolver=0` 的入口规则 N 份，子规则原样保留、UUID 不变；每份副本换新顶层 UUID、加 `name` 后缀，并继续引用同一批子规则。默认由 `rule_clone_entry.py` 处理。

## Excel 侧

- **设备清单（device inventory）**：一份 xlsx，默认列 `设备IP` / `设备名称` / `设备厂商`。
- **原始日志（raw log）**：日志 xlsx 中存放日志正文的列，默认列名 `原始日志`。
- **键值对日志（kv log）**：管道分隔的 `key="value"` 日志形态（如 `node_ip="10.0.0.1"|||`），与 JSON 体相对；提取脚本可双格式适配。
- **设备描述（device description）**：日志侧的 IP 关联键列（默认列名 `设备描述`），与设备清单的 `设备IP` 对齐。
- **关联（join）**：按 IP（设备描述 ↔ 设备IP）把设备清单与多份日志合并。
- **deviceAddress（设备地址）**：日志中标识设备的字段；是拆分字段的默认值之一。
- **拆分字段（split field）**：按某个字段值去重并拆成多个 Sheet 的分组键；默认 `deviceAddress`，可通过 `--split-field` 换成其它已有列或提取列。
- **去重 Sheet（dedup sheet）**：按某列去重只保留每个值首条所生成的 Sheet（`<列名>去重`）；与“按字段值拆多个 Sheet”不同。
- **预检（inspect）**：跑提取、去重、拆分前的只读检查，包括日志格式识别、字段出现率/非空率、列名、Sheet、空日志和截断风险；不产生输出文件。
- **截断风险（truncation risk）**：当前单元格达到 Excel 长度上限或日志结构表现出疑似截断。诊断可标记 `TRUNCATED_TAIL`；这表示存在风险，不能仅凭当前 xlsx 断言原始日志一定被截断，也不能从当前文件恢复不存在的数据。
- **抽查回对（verify sample）**：提取后随机抽 N 行，用独立方式从原文重新找值并与输出比对；“原文有值、提取为空”应判失败，用于捕获静默漏提。
- **诊断列（diag）**：提取脚本默认附带的 `_diag` 列，用于标记每行提取结果并辅助验证。

## 运行侧

- **执行环境（runtime environment）**：运行脚本所使用的 Python 环境；解析规则类脚本只依赖标准库，Excel 类脚本要求包含 `pandas` + `openpyxl`。
- **宿主（host / Agent host）**：负责加载 Skill、提供文件访问与命令执行能力的平台或 Agent，例如 DSH、Claude、Codex、GPT、OpenClaw、Hermars 等。宿主只决定“如何执行”，不应改变 Skill 的业务逻辑。
- **环境缓存（runtime cache）**：宿主若支持，可复用已经验证可用的 Python 解释器或环境；不支持时重新探测即可。`.dsh/python-env` 只是 DSH 兼容实现之一，不是本 Skill 的通用要求。
