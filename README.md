# rule-and-excel-toolkit

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml)

解析规则批处理 + Excel 日志加工的执行型 Agent Skill。核心业务逻辑保持宿主无关，可由具备文件访问与 Python/命令执行能力的 Agent 调用；DSH、Claude、Codex、GPT、OpenClaw、Hermes 等宿主只负责“如何加载与执行”，不改变 Skill 的业务规则。

## 使用

直接说明要处理的任务即可。Agent 加载 `skills/rule-and-excel-toolkit/SKILL.md` 后，应优先使用 `scripts/` 下已有脚本处理输入文件、验证结果，并返回最终输出文件。

示例：

- 「帮我把这个 Base64 规则文件加层级编号，前缀用浦发银行_」
- 「把这份设备清单和这几份日志按 IP 汇总、拆 Sheet」
- 「从这份日志 Excel 的原始日志列提取 deviceName/deviceAddress」
- 「只复制入口规则两份，子规则保持共享」

具体触发规则、脚本选择、执行边界和验证标准见 `skills/rule-and-excel-toolkit/SKILL.md`。

## DSH 使用示例

本仓库仍兼容 DSH。需要通过 DSH 安装时，可使用：

```sh
dsh plugin --profile web add github:Jun-Wu05/rule-and-excel-toolkit
```

安装后重启对应 profile。DSH 只是当前兼容宿主之一，不是本 Skill 的强制运行环境。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `rule_hierarchy_number.py` | 按 ref 还原层级，给规则 name 加多级编号前缀 |
| `rule_clear_field.py` | 置空 / 删除 normalize 中的 field |
| `rule_replace_uuid.py` | 替换顶层规则 UUID + 同步引用，可改 name（支持 `--verify` / `--prefix-only`） |
| `rule_clone_entry.py` | 只克隆入口规则 N 份，子规则共享不变 |
| `rule_link_conditionmatch.py` | 入口规则 + 子规则组装成 conditionMatch 规则链 |
| `excel_inspect.py` | 日志预检（只读）：格式识别、字段出现率、截断风险 |
| `excel_device_log_join.py` | 设备清单 × 多份日志按 IP 关联、汇总、拆 Sheet |
| `excel_extract_log_fields.py` | 从日志列提取多个字段（JSON/键值对双格式 + 诊断 + `--verify-sample`） |
| `excel_filter_logs.py` | 按关键词筛选日志行 |
| `excel_split_by_deviceaddress.py` | 按指定字段值去重并拆多 Sheet，默认 `deviceAddress` |
| `excel_dedup_sheets.py` | 按指定列去重保留首条，每列一个 Sheet |

## 运行环境

- 解析规则类脚本只依赖 Python 标准库。
- Excel 类脚本需要 `pandas` + `openpyxl`，依赖见 [requirements.txt](requirements.txt)。
- 推荐先探测当前 Python 是否可用：

```sh
python -c "import sys, pandas, openpyxl; print(sys.executable)"
```

- 当前环境不可用时，可探测已有 conda/venv 环境。
- 宿主若支持环境缓存，可复用已验证的 Python；不支持时重新探测即可。
- 未经用户明确同意，不自动创建虚拟环境或安装依赖。

跨 Agent 兼容原则见 `skills/rule-and-excel-toolkit/references/platform-compatibility.md`。

## 验证原则

Skill 不是“脚本能跑完就算成功”。

- 解析规则任务应检查规则数量、UUID 替换、name 改写、引用关系，以及处理前后未知引用集合；不得产生新的未知 UUID 引用。
- Excel 任务应根据场景检查行数、字段非空率、Sheet/唯一值数量、诊断码、抽查回对结果和截断风险。
- `TRUNCATED_TAIL` 表示存在疑似截断风险，不能仅凭当前 xlsx 断言缺失内容一定可恢复或一定不可恢复。

## 迭代

- Skill 核心位于 `skills/rule-and-excel-toolkit/`。
- 业务逻辑优先通过现有脚本和 CLI 参数扩展，不长期保留 `_new`、`_v2`、`_final`、客户名后缀等复制型变体脚本。
- 新增正式能力时同步更新 `SKILL.md`、README/相关文档和 [CHANGELOG.md](CHANGELOG.md)。
- push 后 CI 会执行 `node verify.mjs` 校验包结构。
- 设计决策与领域术语分别记录在 [docs/adr/](docs/adr/) 与 [CONTEXT.md](CONTEXT.md)。

## 许可证

[MIT](LICENSE)
