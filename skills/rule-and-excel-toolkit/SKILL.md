---
name: rule-and-excel-toolkit
description: 解析规则批处理与 Excel 日志数据加工的执行型工具集。当用户需要处理 Base64 编码的解析规则 JSON 时触发——按 ref 父子关系生成多级层级编号、清空 normalize 中指定 field、替换顶层规则 UUID 并同步所有引用、用 conditionMatch 把入口规则与子规则组装成规则链；或需要对设备/日志 Excel 做按 IP 关联汇总并拆分多 Sheet、从日志列用 JSON+正则双策略提取多个字段、按关键词筛选日志行时触发。脚本通用，输入输出路径、字段名、前缀/后缀均可通过命令行参数传入。不用于官网页面生成、普通文档处理或与解析规则/日志 Excel 无关的通用编程。
---

# 解析规则与 Excel 日志加工工具集（执行型）

本 Skill 是一套**执行型**工具集：被调用时，直接用 `scripts/` 下的脚本处理用户给定的输入文件，产出最终结果文件，并把结果路径交还给用户。**不要把脚本丢给用户让他们自己改配置、自己跑**——这是本 Skill 与普通脚本仓库的根本区别。

被调用后的标准动作：

1. 识别用户输入属于哪一类（解析规则 Base64，还是 Excel 文件），缺关键参数时只问一次。
2. 把用户的输入文件、输出文件、处理参数（前缀/后缀/字段名/关键词等）组装成命令行，直接用 shell（DSH 中是 pwsh）执行对应脚本。
3. 脚本输出仍是与用户输入同格式的文件（解析规则→Base64 txt，Excel→xlsx）。默认输出到输入文件同目录、文件名加处理后缀，也可由用户指定。
4. 读脚本打印的执行日志，确认规则数、改名/换 UUID 数量、引用一致性等；跑完用脚本自带的 `--verify` 或诊断信息判断是否成功。
5. 把**最终结果文件的绝对路径**告诉用户，并简要说明做了什么、验证结论是什么。

所有脚本在 `scripts/` 目录下，已统一支持命令行参数，无需改脚本源码。

## 运行环境（执行 Excel 类脚本前先确认）

解析规则类脚本只用 Python 标准库，任何 Python 3 都可直接跑。Excel 类脚本需要 `pandas` + `openpyxl`（依赖清单见 `requirements.txt`）。执行 Excel 类脚本前，按下方顺序准备好环境：

1. **先探测现有环境**：执行 `python -c "import pandas, openpyxl; print(sys.executable)"`——成功即用这个 `python` 继续。
2. **没成功就逐环境探测 conda**：执行 `conda env list` 列出所有环境，对每个环境跑 `<该环境的 python.exe> -c "import pandas, openpyxl"`，命中的记下，之后用 `conda run -n <env> python ...` 或该环境的完整 `python.exe` 路径执行。
3. **都探测不到 → 询问用户**：「未找到含 pandas/openpyxl 的 Python 环境，是否需要我新建一个虚拟环境并自动安装依赖？」用户同意后：优先 `conda create -n <名称> python=3.11 pandas openpyxl -y`；无 conda 时退回 `python -m venv <目录>` + `pip install pandas openpyxl`。用户拒绝则停止，不擅自安装任何东西。
4. **记住选中环境**：把最终选中的执行方式（如 `conda run -n <env>` 或某个 `python.exe` 的完整路径）写到当前工作目录的 `.dsh/python-env`（一行文本）。下次先读它：命中且 import 成功就直接复用；失效再重新探测。

## 什么时候触发

- 用户拿到一段 Base64 字符串或一个 Base64 txt 文件，说是"解析规则""规则导出""normalize 规则"，要改里面的内容。
- 用户要给解析规则加层级编号、加名称前缀/后缀、换 UUID、清空某个字段、把多条规则组装成规则链。
- 用户要把设备清单和多份原始日志 Excel 按 IP 关联、汇总、拆成多 Sheet。
- 用户要从日志 Excel 的某一列里提取多个 JSON 字段，或按关键词筛选日志行，或按某个字段值拆成多 Sheet。

## 不使用场景

- 与解析规则、日志 Excel 无关的通用编程、调试。
- 官网/页面生成、文档排版、PPT 制作。

## 识别输入 + 选脚本

先判断输入形态，再决定用哪条命令：

| 输入形态 | 用户要做的事 | 用哪个脚本 |
|---|---|---|
| Base64 txt（解码后是规则 JSON 数组） | 加层级编号前缀 | `rule_hierarchy_number.py` |
| Base64 txt | 清空 normalize 中某个 field | `rule_clear_field.py` |
| Base64 txt | 换 UUID（+加 name 前缀/后缀） | `rule_replace_uuid.py` |
| Base64 txt | 入口规则+子规则组装成规则链 | `rule_link_conditionmatch.py` |
| .xlsx 设备清单 + 多份日志 xlsx | 按 IP 关联、汇总、拆多 Sheet | `excel_device_log_join.py` |
| .xlsx 含日志列 | 从日志列提取多个 JSON 字段 | `excel_extract_log_fields.py` |
| .xlsx 含日志列 | 按关键词筛选行 | `excel_filter_logs.py` |
| .xlsx 含日志列 | 按 deviceAddress 去重并拆多 Sheet | `excel_split_by_deviceaddress.py` |

不确定输入是哪种时，先解码看一眼：Base64 解码后是 `[ {...}, {...} ]` 且元素含 `id`/`name`/`normalize`/`parser` → 解析规则；否则多半是 Excel。

解析规则类脚本只依赖 Python 标准库。Excel 类脚本依赖 `pandas` + `openpyxl`，执行前按上文「运行环境」准备。

## 一、解析规则批处理（Base64 JSON）

共同数据约定：
- 输入是一整段 Base64，解码后是 JSON 数组 `[规则1, 规则2, ...]`。
- 每条规则是 dict，关键字段：`id`(规则UUID)、`name`、`normalize`(归一化数组)、`parser`(含 `filter`、`subResolver`)、`ref`(引用其他规则 UUID)。
- 输出同样是 Base64（重新编码）。

### 1. rule_hierarchy_number.py — 层级编号生成器

通过递归提取每条规则里的 `ref` 还原父子层级树，给每条规则的 `name` 加多层级编号前缀：第1层 `01_前缀_原名`，第2层 `0101_前缀_原名`，深度不限。自动清洗旧编号和旧前缀，防重复叠加。

```bash
python scripts/rule_hierarchy_number.py <输入.txt> [输出.txt] [--prefix 前缀]
```
- `--prefix`：名称前缀，如 `浦发银行_`；不传则用脚本内置默认；传空字符串 `--prefix ""` 则只加编号不加前缀。
- 输出默认输入同名加 `_层级编号`。跑完打印每条规则改名前后对照。

### 2. rule_clear_field.py — 置空 / 删除 normalize 中的 field

处理 `normalize` 数组中 `field` 完全等于指定值的条目，有两种模式（用 `--mode` 指定）：

- **`--mode clear`（默认）**：把匹配条目的 `field` 值置为空字符串 `""`，**条目保留**，其余字段不动。让某归一化字段失效但不动条目结构。
- **`--mode remove`**：**删除整个条目**（条目从数组里消失）。彻底移除某个归一化字段。

```bash
python scripts/rule_clear_field.py <输入.txt> <输出.txt> location_country                    # 默认置空
python scripts/rule_clear_field.py <输入.txt> <输出.txt> location_country --mode remove       # 删除整个条目
python scripts/rule_clear_field.py <输入.txt> <输出.txt> --fields=location_country,location_province
```
不传字段名时会交互式提示输入。跑完打印每个字段处理了几处。

**术语映射（重要，避免歧义）**：用户常说"删掉/清空/去掉某字段"，这词有歧义。按下面规则定 mode，**不要自己另写处理逻辑绕过 skill**：

| 用户原话 | 含义 | 用哪个 mode |
|---|---|---|
| "清空/置空/把 field 改空/让字段失效" | field 值变空，条目保留 | `--mode clear`（默认） |
| "删掉/去掉/删除字段"（笼统说法） | **默认按置空理解**，用 `clear` | `--mode clear` |
| "删除整个条目/把这个归一化项移除/把这条删了" | 条目消失 | `--mode remove` |

笼统的"删除字段"默认走 `clear`（置空），因为这是最常见的诉求，也是 skill 的标准操作。处理完明确告诉用户"已置空 N 处 field（条目保留）"，如果用户其实想删条目，改 `--mode remove` 重跑即可——不要凭猜测自己写删除逻辑。

**字段名可能出现在两处**：同一个名字（如 `event_name`）可能既是 `normalize[].field` 的值，又是 `parser.filter[].fields` 里的 key（addFields 过滤器给日志打字段值，常有 `'网络连接'` 这类实际值）。本脚本只处理 `normalize` 里的。处理前先解码确认该名字出现在哪些位置；如果用户想动的其实不在 normalize，或两处都要动，要跟用户确认范围再处理。

### 3. rule_replace_uuid.py — 替换顶层规则 UUID + 加 name 前缀/后缀

只替换每条顶层规则的 `id`（生成新 UUID），递归把所有引用到旧 UUID 的地方同步换成新 UUID，保证层级引用不断裂；可选给顶层 `name` 加前缀和/或后缀（幂等，防重复叠加）。只改顶层规则 UUID 和顶层 name，不碰 `deviceType.id`、`filter.id`、`deviceType.name`、`parser.name` 等。

```bash
python scripts/rule_replace_uuid.py <输入.txt> [输出.txt] [--prefix 前缀] [--suffix 后缀] [--verify]
```
- `--prefix`/`--suffix`：给顶层 name 加前缀/后缀，如 `--suffix _0731`。可同时用，也可都不用（仅换 UUID）。
- `--verify`：跑完后打印每条规则 id/name 和引用一致性校验。
- 输出默认输入同名加 `_reuuid`。

### 4. rule_link_conditionmatch.py — 组装入口规则 + 子规则成规则链

自动识别入口规则（`subResolver=0`）和子规则（`subResolver=1`），在入口规则 `parser.filter` 里构建标准 `conditionMatch` 过滤器，把每个子规则 UUID 挂到 `cases[].rule.ref`，连成规则链。严格保留原始 UUID 和 name，只改拓扑连接；幂等，已有 `conditionMatch` 会覆盖更新。

```bash
python scripts/rule_link_conditionmatch.py <输入.txt> [输出.txt]
```
- 每个 case 的匹配条件默认固定为 `original_log like 'xxx'`，需要具体匹配值时在生成后手工替换 `'xxx'`。
- 输出默认输入同名加 `_规则链`。跑完打印每条规则的入口/子规则标记和 conditionMatch 组装情况。

## 二、Excel 日志数据加工（pandas）

依赖 `pandas` 和 `openpyxl`，执行前按上文「运行环境」确认环境（缺包可 `pip install -r requirements.txt`）。

### 5. excel_device_log_join.py — 设备清单 × 多份日志按 IP 关联

读取一份设备清单（默认列 `设备IP`/`设备名称`/`设备厂商`）和多份原始日志（默认列 `设备描述`/`原始保留`/`原始日志`，其中 `设备描述` 作为 IP 关联键），输出多 Sheet：`汇总`(按 IP 去重)、`全量明细`(不去重)、每个 IP 一个独立 Sheet。

```bash
python scripts/excel_device_log_join.py <设备清单.xlsx> <输出.xlsx> <日志1.xlsx> [日志2.xlsx ...] \
  [--device-ip-col 设备IP] [--device-name-col 设备名称] [--device-vendor-col 设备厂商] \
  [--log-ip-col 设备描述] [--log-keep-col 原始保留] [--log-col 原始日志]
```
所有列名参数都可按实际表头改。列名对不上会报错并列出可用列名，据此调整 `--*-col` 即可。

### 6. excel_extract_log_fields.py — 从日志列提取多个 JSON 字段

读取 Excel 中的日志列，对每行用「JSON 解析优先 + 安全正则兜底」双策略提取指定字段，展开成多列输出。默认提取 `deviceName`/`deviceAddress`/`deviceProductType`/`productVendorName`/`deviceSendProductName`/`rawEvent`。自动清除 Excel 不支持的控制字符；默认输出 `_diag` 诊断列。

```bash
python scripts/excel_extract_log_fields.py <输入.xlsx> [输出.xlsx] \
  [--log-column 原始日志] [--fields f1,f2,...] [--no-diag]
```
- `--fields`：逗号分隔的字段列表，覆盖默认 6 个字段。
- `--no-diag`：不输出诊断列。
- 输出默认输入同名加 `_提取`。

### 7. excel_filter_logs.py — 按关键词筛选日志行

读取 Excel（全部按字符串读，保留换行），筛选指定列包含指定关键词的行，输出到新 Excel。

```bash
python scripts/excel_filter_logs.py <输入.xlsx> [输出.xlsx] [--keyword 关键词] [--column 列名]
```
- `--keyword`：默认 `alarmExtendFieldsStrategyName`。
- `--column`：默认 `原始日志`。
- 输出默认输入同名加 `_筛选`。跑完打印命中行数并预览前 3 条。

### 8. excel_split_by_deviceaddress.py — 按 deviceAddress 拆 Sheet

读取 Excel，对日志列用「JSON 优先 + 正则兜底」提取指定字段，输出三类 Sheet：`原始全量数据`（全量）、`deviceAddress去重`（按 deviceAddress 保留首条）、每个不同 deviceAddress 一个独立 Sheet（Sheet 名为该 deviceAddress）。自动清除 Excel 不支持的控制字符。

```bash
python scripts/excel_split_by_deviceaddress.py <输入.xlsx> <输出.xlsx> \
  [--log-column 原始日志] [--fields f1,f2,...]
```
- `<输出.xlsx>` 是**必填**位置参数（与其它 Excel 脚本不同，此脚本输出不默认带后缀）。
- `--fields`：默认 `deviceName,productVendorName,deviceSendProductName,dvcAddress,rawEvent,deviceAddress,dataType`。
- `--log-column`：默认 `原始日志`。
- 跑完打印 Sheet 列表和每个字段的非空统计。

## 执行后怎么做

- 解析规则类：跑完读日志里的规则数、UUID 替换数、name 改写数；用了 `--verify` 的看引用一致性是否通过。引用一致性报"指向未知 ID"是正常的——原始规则里本来就存在引用项目外规则的情况，只要顶层 UUID 全换、引用同步没断即可。
- Excel 类：读日志里的行数、命中数、各字段非空统计、诊断分布，判断结果是否符合预期。
- 把最终结果文件的绝对路径给用户，说明做了什么、验证结论、还剩什么需要手工处理（如 conditionMatch 里的 `'xxx'` 占位值）。

## 重要边界

- 解析规则改错字段可能让规则在引擎里失效；改之前建议先备份原始 Base64，跑完用 `--verify` 或诊断信息确认。
- Excel 脚本严格依赖表头列名，列名对不上会直接报错并列出可用列名，按提示用 `--*-col` 调整，不要改脚本源码。
- 输出文件默认写在输入文件同目录，命名加后缀避免覆盖原始文件；用户明确指定输出路径时用用户指定的。
- 需要新增一个类似场景时，优先复用最接近的脚本加命令行参数，而不是从零重写。
- 未经用户明确同意，不新建虚拟环境、不安装任何依赖。
