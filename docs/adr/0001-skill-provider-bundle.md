# 1. 以 skill provider bundle 形态打包，而非每个脚本一个 model-facing tool

- 状态：已接受
- 日期：2026-09-01

## 背景

`rule-and-excel-toolkit` 是一套「指令 + 8 个 Python 脚本」的执行型工具集。把它接入 DSH 有两种形态：

- **(A) skill provider bundle**：把 `SKILL.md` + `scripts/` 打进一个 npm 包，注册一个 skill provider；模型按描述自动加载 skill，再通过 shell 执行脚本。
- **(B) tool 插件**：写 TypeScript Cordis 插件，把 7 个脚本分别注册成离散的 model-facing tool，带 JSON 参数 schema，模型直接 tool call。

## 决策

采用 **(A)** —— 保持 skill 形态，脚本仍是权威实现，模型按 SKILL.md 组装命令行并执行。

## 后果

- ✅ 改动最小，脚本一字不改，最快上 GitHub 迭代。
- ✅ 与 DSH 现有 skill 生态（`skill` tool、会话目录）直接兼容。
- ⚠️ 没有 per-tool 的 schema 校验，脚本参数正确性依赖模型遵循 SKILL.md。
- ⚠️ 若未来需要硬性的参数校验、缓存选中的环境等代码级能力，需重评估迁移到 tool 插件。
