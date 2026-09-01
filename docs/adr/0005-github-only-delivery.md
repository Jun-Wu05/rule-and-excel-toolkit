# 5. 纯 GitHub 交付，暂不发布 npm

- 状态：已接受
- 日期：2026-09-01

## 背景

插件的分发有两种：从 Git 安装（`dsh plugin add github:...`）或从 npm 安装（`dsh plugin add rule-and-excel-toolkit-dsh`）。用户当前需求是「放在 GitHub 上迭代」，而非对外发布稳定版本。

## 决策

**只走 GitHub**：仓库即 bundle，更新靠重新 `dsh plugin add`（或 pin 到新 commit/tag）。npm 包名 `rule-and-excel-toolkit-dsh` 已预留在 `package.json` 的 `name` 与 `exports`，结构随时可发布。

## 后果

- ✅ 零发布流水线，改动 push 后即可重新安装生效。
- ✅ 保留未来平滑迁移到 npm（`prepublishOnly` 已挂 `verify`）。
- ⚠️ 己方安装无版本化升级：更新需手动重新 add；若未来要给多台机器版控升级，再发 npm。
