# 2. provider 采用零构建 ESM JavaScript，而非 TypeScript + prepare

- 状态：已接受
- 日期：2026-09-01

## 背景

provider（`lib/index.js`）可以用零构建的纯 ESM JS，也可以用 TypeScript 编译到 `lib/`。用户选择主要通过 `dsh plugin add github:...` 从 Git 安装——该方式拉取源码但不跑 `build`，TypeScript 包会因缺少构建产物而加载失败，需要作者写 `prepare` 脚本 + 用户 allowBuild。

## 决策

采用**零构建纯 ESM JS**：`lib/index.js` 直接可加载，无构建步骤、无 dev 依赖。

## 后果

- ✅ `dsh plugin add github:Jun-Wu05/rule-and-excel-toolkit` 无需任何构建权限，即装即用。
- ✅ 用 `node verify.mjs`（CI 与本地）做冒烟校验，弥补缺类型检查的损失。
- ⚠️ 无静态类型；provider 长约 150 行，风险可控。若未来 provider 逻辑膨胀，再评估引入 TypeScript。
