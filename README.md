# rule-and-excel-toolkit

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jun-Wu05/rule-and-excel-toolkit/actions/workflows/ci.yml)

解析规则批处理 + Excel 日志加工的执行型工具集，打包成 **DeepSeek Harness (DSH)** 的 skill 插件（provider bundle）。

## 安装

```sh
dsh plugin --profile web add github:Jun-Wu05/rule-and-excel-toolkit
```

装完重启 profile（`dsh web`），`rule-and-excel-toolkit` 会出现在会话的 skill 目录中，可被模型按描述自动触发或由你点名调用。

## 使用

直接说你要做什么即可，模型加载 skill 后用 `scripts/` 下的脚本处理你的输入文件，并把**结果文件的绝对路径**交还给你：

- 「帮我把这个 Base64 规则文件加层级编号，前缀用浦发银行_」
- 「把这份设备清单和这几份日志按 IP 汇总、拆 Sheet」
- 「从这份日志 Excel 的原始日志列提取 deviceName/deviceAddress」

具体触发词、选脚本规则、每个脚本的命令行参数，见 `skills/rule-and-excel-toolkit/SKILL.md`。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `rule_hierarchy_number.py` | 按 ref 还原层级，给规则 name 加多级编号前缀 |
| `rule_clear_field.py` | 置空 / 删除 normalize 中的 field |
| `rule_replace_uuid.py` | 替换顶层规则 UUID + 加 name 前缀/后缀（可 `--verify`） |
| `rule_link_conditionmatch.py` | 入口规则 + 子规则组装成规则链 |
| `excel_inspect.py` | 日志预检（只读）：格式识别、字段出现率、截断风险 |
| `excel_device_log_join.py` | 设备清单 × 多份日志按 IP 关联、汇总、拆 Sheet |
| `excel_extract_log_fields.py` | 从日志列提取多个字段（JSON/键值对双格式 + 截断兜底 + `--verify-sample`） |
| `excel_filter_logs.py` | 按关键词筛选日志行 |
| `excel_split_by_deviceaddress.py` | 按 deviceAddress 去重并拆多 Sheet |
| `excel_dedup_sheets.py` | 按指定列去重保留首条，每列一个 Sheet |

## 运行环境

- 解析规则类脚本只用 Python 标准库，任何 Python 3 均可。
- Excel 类脚本需要 `pandas` + `openpyxl`（见 [requirements.txt](requirements.txt)）。
- skill 的执行前序会：先探测现有环境 → 缺失时询问你是否新建虚拟环境并自动装依赖 → 把选中环境记到工作目录 `.dsh/python-env` 复用。详见 SKILL.md 的「运行环境」一节。

## 迭代

- 日常改 `skills/rule-and-excel-toolkit/`（SKILL.md 或脚本）→ `git commit` + `push`。
- push 后 CI 会跑 `node verify.mjs` 校验包结构；有变更顺手 bump `package.json` 的 `version` 并更新 [CHANGELOG.md](CHANGELOG.md)。
- 让装好的 profile 用上新版本：重新 `dsh plugin --profile web add github:Jun-Wu05/rule-and-excel-toolkit`（或 pin 到新 commit / tag）。
- 设计决策与术语分别记录在 [CONTEXT.md](CONTEXT.md) 和 [docs/adr/](docs/adr/)。

## 许可证

[MIT](LICENSE)
