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
- `--verify`：仅对声明支持验证的命令开放。
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
3. 有输出文件时声明 `output_suffix`。
4. 需要专属参数时用 `OptionSpec` 声明，并映射到旧脚本参数。
5. 通过 CLI contract tests。
6. 同步 SKILL.md、README/相关文档和 CHANGELOG。

现有独立脚本是兼容层；新 Agent 集成不应依赖其自然语言 stdout 进行业务判断，应优先读取统一 CLI 的 JSON 结果。
