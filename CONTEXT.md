# CONTEXT.md — 领域词汇表

本文件是 `rule-and-excel-toolkit` 的领域术语表（glossary）。只记录术语的精确定义，不含实现细节；实现与用法见 `skills/rule-and-excel-toolkit/SKILL.md`。

## 解析规则侧

- **解析规则（rule）**：一段 Base64 编码的 JSON 数组；解码后每条规则是一个 dict，关键字段为 `id`、`name`、`normalize`、`parser`、`ref`。是解析规则的导出/交换形态。
- **顶层规则（top-level rule）**：层级树的根节点——被其它规则通过 `ref` 引用、其 UUID 会被换成新值的规则。与「子规则」相对。
- **子规则（sub-rule）**：`subResolver=1` 的规则；通过 `ref` 挂到父规则之下。
- **入口规则（entry rule）**：`subResolver=0` 的规则；规则链的起点。
- **ref（引用）**：规则里引用其它规则 UUID 的字段，构成父子层级；替换 UUID 时必须同步所有 `ref` 指向。
- **normalize（归一化数组）**：规则内一串归一化条目，每条含 `field` 等字段；「清空/删除字段」即针对其中的 `field`。
- **conditionMatch**：入口规则 `parser.filter` 里的标准过滤器；把子规则 UUID 挂到 `cases[].rule.ref` 以连成规则链。
- **规则链（rule chain）**：入口规则 + 子规则通过 `conditionMatch` 连接而成的链。
- **字面前缀（literal prefix）／后缀（suffix）**：直接加在规则 `name` 前/后的固定文本，如 `启明星辰_数据库审计_`；不含数字、不含层级含义，区别于「层级编号」。
- **层级编号（hierarchy number）**：按 `ref` 父子层级给规则 `name` 生成的数字前缀，如 `01_`、`0101_`；反映层级，而非纯字面前缀。
- **复制规则／克隆规则（clone rule）**：复制一条规则的需求；副本需生成新 UUID（避免与原件冲突），并可改 `name`。

## Excel 侧

- **设备清单（device inventory）**：一份 xlsx，默认列 `设备IP` / `设备名称` / `设备厂商`。
- **原始日志（raw log）**：日志 xlsx 里存放日志正文的列，默认列名 `原始日志`。
- **设备描述（device description）**：日志侧的 IP 关联键列（默认列名 `设备描述`），与设备清单的 `设备IP` 对齐。
- **关联（join）**：按 IP（设备描述 ↔ 设备IP）把设备清单与多份日志合并。
- **deviceAddress（设备地址）**：日志中标识设备的字段；是「拆分字段」的默认值。
- **拆分字段（split field）**：按某个字段值去重并拆成多个 Sheet 的分组键，默认 `deviceAddress`，可用命令行换成其它列。
- **诊断列（diag）**：提取脚本默认附带的 `_diag` 列，标记每行提取结果以便验证。

## 运行侧

- **执行环境（runtime environment）**：跑脚本所用的 Python 环境；Excel 类脚本要求其含 `pandas` + `openpyxl`。选中后记入工作目录 `.dsh/python-env` 复用。
