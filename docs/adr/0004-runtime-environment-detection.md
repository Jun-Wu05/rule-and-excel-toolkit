# 4. Excel 依赖不打包进插件，运行时探测 + 征询新建虚拟环境

- 状态：已接受
- 日期：2026-09-01

## 背景

Excel 类脚本依赖第三方库 `pandas` + `openpyxl`，它们不在 Python 标准库里。DSH 插件是 npm 包，若把 Python 解释器/第三方 wheel 打进包里，又大又平台绑定，是反模式。需要决定依赖如何随插件交付。

## 决策

**不打包环境**。插件只随包分发 `SKILL.md` + `scripts/` + `requirements.txt`；SKILL.md 的执行前序负责运行时准备环境：

1. 先探测现有环境（`python -c "import pandas, openpyxl"`，失败则逐 conda env 探测）；
2. 都探测不到 → 询问用户是否新建虚拟环境并自动装依赖（conda 为主，无 conda 退 venv）；
3. 把选中环境记到工作目录 `.dsh/python-env`，下次优先复用。

## 后果

- ✅ 插件轻量、可移植；`requirements.txt` + 文档是唯一依赖交付面。
- ✅ 用户机器上有多 conda 环境时，skill 能定位到装了依赖的那一个。
- ⚠️ 目标机器必须有 Python（这里是 Anaconda base，已具备）；首次跑 Excel 类脚本可能需要新建环境或装依赖，且新建环境需要用户明确同意。
