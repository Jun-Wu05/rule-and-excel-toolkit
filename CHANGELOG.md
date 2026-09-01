# Changelog

本项目显著变更的记录，按 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 风格维护，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

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
