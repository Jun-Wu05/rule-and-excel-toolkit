# Unified CLI Contract

本文件定义 `rule-and-excel-toolkit` 的稳定命令行契约。所有新能力应优先注册到 `scripts/toolkit.py`，旧业务脚本可保留兼容入口，但 Agent 应优先使用统一 CLI。

## 命令结构

```bash
python scripts/toolkit.py <domain> <command> --input <path> [--output <path>] [业务参数...]
```

当前 domain：`rule`、`excel`。

公共参数：

- `--input`：主输入文件，必填。
- `--output`：产生文件的命令统一支持；省略时由命令规范生成默认名称。
- `--format human|json`：默认 `human`；Agent 推荐 `json`。
- `--verify`：所有产生输出文件的统一命令都支持；验证应检查真实输出文件，而不是仅依据退出码或 stdout 文案。
- `--dry-run`：只展示执行计划，不运行旧脚本、不写文件。

## 机器输出

JSON 输出必须包含：

- `schema_version`
- `status`
- `command`
- `input`
- `output`
- `stats`
- `verification`
- `warnings`
- `error`

当前 schema：`1.0`。增加兼容字段可提升 minor；破坏字段语义或删除字段必须提升 major。

`stats` 应优先来自真实输出文件检查或标准 `[STATS] key=value` 输出，不应要求 Agent 解析自然语言 `legacy_stdout` 才能得到关键业务统计。

## 验证规则

统一层验证和旧脚本内建验证是并列检查，**任一失败则总体验证失败**，不得由后执行的检查覆盖前一个失败结果。

解析规则至少检查：

- 输出 Base64 可解码为 JSON 数组；
- 顶层 ID 唯一；
- 处理前后未知引用集合；
- `new_unknown_refs = unknown_after - unknown_before` 必须为空。

Excel 至少检查：

- 输出 xlsx 可读取；
- 至少存在一个 Sheet；
- 结构化返回 Sheet 名、Sheet 行数、列名等统计。

命令如另有专属验证（例如字段抽样回对），必须与统一输出检查合并，不能互相覆盖。

## 日志字段解析

公共字段解析器不得硬编码某个业务字段为特殊语义。对于 plain KV 中需要“从 `field=` 一直取到日志末尾”的嵌套载荷字段，应通过 `tail_fields` / `--tail-fields` 显式声明。

例如：

```bash
python scripts/toolkit.py excel split \
  --input input.xlsx \
  --fields raw_data,dev_ip \
  --split-field dev_ip \
  --tail-fields raw_data
```

## 退出码

- `0`：成功
- `2`：CLI/参数错误
- `3`：输入错误
- `4`：执行错误
- `5`：验证失败
- `6`：输出错误

## 新增能力规则

新增正式脚本时必须：

1. 在 `common/registry.py` 注册 `CommandSpec`。
2. 使用现有公共参数名称，不创建 `--out`、`--outfile`、`--destination` 等同义参数。
3. 有输出文件时声明 `output_suffix` 并支持结构化 `--verify`。
4. 需要专属参数时用 `OptionSpec` 声明，并映射到旧脚本参数。
5. 至少有一个真实 E2E 测试，通过统一 CLI 执行命令并检查输出文件/JSON 结果；不能只测 `--help` 或 `--dry-run`。
6. Excel 能力的 CI 必须安装 `requirements.txt` 后实际执行。
7. 同步 SKILL.md、README/相关文档和 CHANGELOG。

现有独立脚本是兼容层；新 Agent 集成不应依赖其自然语言 stdout 进行业务判断，应优先读取统一 CLI 的 JSON 结果。
