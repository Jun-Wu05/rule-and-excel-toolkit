# rule-and-excel-toolkit

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml)

解析规则批处理 + Excel 日志加工的执行型 Agent Skill。核心业务逻辑保持宿主无关，可由具备文件访问与 Python/命令执行能力的 Agent 调用；DSH、Claude、Codex、GPT、OpenClaw、Hermes 等宿主只负责“如何加载与执行”，不改变 Skill 的业务规则。

## 使用

Agent 加载 `skills/rule-and-excel-toolkit/SKILL.md` 后，推荐优先通过统一入口 `scripts/toolkit.py` 执行任务。现有 11 个独立脚本继续保留，作为兼容入口和业务实现层。

统一命令形态：

```sh
python scripts/toolkit.py <rule|excel> <command> --input <path> [--output <path>] [业务参数...]
```

Agent 推荐使用机器输出：

```sh
python scripts/toolkit.py rule reuuid --input input.txt --format json --verify
python scripts/toolkit.py excel extract --input input.xlsx --fields deviceName,deviceAddress --format json --verify
```

统一 CLI 当前命令：

| 需求 | 命令 |
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

`--format json` 输出带稳定 `schema_version`；`--dry-run` 可检查最终调用计划但不运行脚本、不写输出。完整 CLI 契约见 `skills/rule-and-excel-toolkit/references/cli-contract.md`。

## DSH 使用示例

本仓库仍兼容 DSH：

```sh
dsh plugin --profile web add github:Jun-Wu05/rule-and-excel-toolkit
```

DSH 是兼容宿主之一，不是 Skill 的强制运行环境。

## 独立脚本兼容入口

| 脚本 | 作用 |
|---|---|
| `rule_hierarchy_number.py` | 按 ref 还原层级，给规则 name 加多级编号前缀 |
| `rule_clear_field.py` | 置空 / 删除 normalize 中的 field |
| `rule_replace_uuid.py` | 替换顶层规则 UUID + 同步引用，可改 name |
| `rule_clone_entry.py` | 只克隆入口规则 N 份，子规则共享不变 |
| `rule_link_conditionmatch.py` | 入口规则 + 子规则组装成 conditionMatch 规则链 |
| `excel_inspect.py` | 日志预检 |
| `excel_device_log_join.py` | 设备清单 × 多份日志按 IP 关联 |
| `excel_extract_log_fields.py` | 从日志列提取多个字段 |
| `excel_filter_logs.py` | 按关键词筛选日志行 |
| `excel_split_by_deviceaddress.py` | 按指定字段值去重并拆多 Sheet |
| `excel_dedup_sheets.py` | 按指定列去重保留首条 |

## 运行环境

- 解析规则类脚本只依赖 Python 标准库。
- Excel 类脚本需要 `pandas` + `openpyxl`，依赖见 [requirements.txt](requirements.txt)。
- 推荐先探测当前 Python：

```sh
python -c "import sys, pandas, openpyxl; print(sys.executable)"
```

未经用户明确同意，不自动创建虚拟环境或安装依赖。跨 Agent 兼容原则见 `skills/rule-and-excel-toolkit/references/platform-compatibility.md`。

## 验证与兼容性

- 统一 CLI 的 human/json 输出由公共结果层生成，Agent 不需要解析独立脚本的 emoji 或自然语言日志。
- 现有独立脚本旧调用方式继续可用；迁移阶段不做破坏性删除。
- CI 会检查命令注册、脚本存在性、默认输出规范、JSON schema、package/CHANGELOG 版本一致性。
- 新增正式脚本必须在 `common/registry.py` 注册，否则不应视为完成统一 CLI 接入。

## 迭代

- Skill 核心位于 `skills/rule-and-excel-toolkit/`。
- 新能力优先复用现有脚本；正式新增能力需同步 registry、SKILL.md、README/相关文档和 CHANGELOG。
- 不长期保留 `_new`、`_v2`、`_final`、客户名后缀等复制型变体脚本。
- push 后 CI 会执行 Node bundle 校验和 Python CLI contract tests。

## 许可证

[MIT](LICENSE)
