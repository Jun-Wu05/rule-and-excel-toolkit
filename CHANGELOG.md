# Changelog

本项目显著变更的记录，按 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 风格维护，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-09-01

### Added
- 将 `rule-and-excel-toolkit` skill 打包为 DSH 插件（provider bundle）：`SKILL.md` + 8 个脚本随包分发。
- 新增「运行环境」跑前序：先探测现有环境、缺失时征询用户新建虚拟环境并自动装依赖、把选中环境记 `.dsh/python-env` 复用。
- 补文档化第 8 个脚本 `excel_split_by_deviceaddress.py`。
- 新增 GitHub Actions CI 校验（`node verify.mjs`）。
- 新增 `README.md`、`LICENSE`（MIT）、`requirements.txt`、`CONTEXT.md` 与决策记录（`docs/adr/`）。
