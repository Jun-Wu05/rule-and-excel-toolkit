# Changelog

本项目显著变更的记录，按 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 风格维护，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.2.0] - 2026-09-03

### Added
- `excel_extract_log_fields.py` 新增键值对日志格式支持（`key="value"|||` 管道分隔），与 JSON 体自动双格式适配；此前该格式会静默提取出全空列。
- `excel_extract_log_fields.py` 新增截断兜底：源文件被 Excel 32767 字符单元格上限截断、值有起始引号无闭合引号时，尽力提取到串尾并标记 `TRUNCATED_TAIL` 诊断。
- `excel_extract_log_fields.py` 新增 `--verify-sample N`：随机抽 N 行做「提取值 == 日志原文值」独立回对，捕获静默漏提。
- 新增 `excel_inspect.py`：只读预检工具——日志格式识别、目标字段出现率/非空率、截断风险行数、空日志行数。kv 识别覆盖 syslog 风格（带引号键 ≥1 个或不带引号键 ≥3 个）。
- 新增 `excel_dedup_sheets.py`：按指定列去重保留首条，每列一个 `<列名>去重` Sheet；提取逻辑复用主提取脚本。

### Changed
- `excel_extract_log_fields.py` 的 JSON 策略改为「仅在真正解析出 dict 时短路」，修复「日志含 `{` 但解析失败时带着空结果提前返回」的问题。
- 诊断码统一为 `OK` / `EMPTY_INPUT` / `TRUNCATED_TAIL` / `REGEX_MISS(matched=x/y)` / `RAW_EVENT_IS_NULL`，含义写入 SKILL.md。
- SKILL.md：「标准动作」新增 Excel 任务先预检一步；选型表登记两个新脚本；「重要边界」改为两级表述（列名不匹配用参数；格式不匹配允许工作区变体但须提醒登记回仓库）；新增 32767 截断失败模式说明。
- CONTEXT.md 补充 键值对日志 / 去重 Sheet / 预检 / 截断行 / 抽查回对 术语。

## [0.1.1] - 2026-09-01

### Fixed
- `excel_extract_log_fields.py`：提取字段时保留原始所有列（原实现只留日志列 + 提取列，漏掉原始数据列）。
- `excel_split_by_deviceaddress.py`：同样保留原始所有列。

### Added
- `rule_replace_uuid.py` 新增 `--prefix-only`：只给顶层 name 加前缀/后缀、跳过 UUID 替换（所有 ID 不动）。
- `excel_split_by_deviceaddress.py` 新增 `--split-field`：按任意字段去重并拆多 Sheet（默认 deviceAddress）。

### Changed
- SKILL.md 新增「前缀 / 编号 / 换 UUID（复制规则）」术语映射表，消除「加前缀 vs 加编号 vs 换 UUID」的歧义；把「复制/克隆规则」纳入换 UUID 触发词；拆分脚本改为「按某字段去重」。
- CONTEXT.md 补充 字面前缀 / 层级编号 / 复制规则 / 拆分字段 术语。

## [0.1.0] - 2026-09-01

### Added
- 将 `rule-and-excel-toolkit` skill 打包为 DSH 插件（provider bundle）：`SKILL.md` + 8 个脚本随包分发。
- 新增「运行环境」跑前序：先探测现有环境、缺失时征询用户新建虚拟环境并自动装依赖、把选中环境记 `.dsh/python-env` 复用。
- 补文档化第 8 个脚本 `excel_split_by_deviceaddress.py`。
- 新增 GitHub Actions CI 校验（`node verify.mjs`）。
- 新增 `README.md`、`LICENSE`（MIT）、`requirements.txt`、`CONTEXT.md` 与决策记录（`docs/adr/`）。
