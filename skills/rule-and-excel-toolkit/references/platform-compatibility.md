# 跨 Agent 兼容说明

本 Skill 的业务逻辑、脚本选择、验证标准应保持宿主无关。

- 不在 SKILL.md 中强绑定某个 Agent 的 shell、插件或工作目录实现。
- 使用“当前 Agent 可用的命令执行能力”描述脚本执行方式。
- 允许宿主自行决定 Bash、PowerShell、exec、sandbox 等实现。
- 若宿主支持 Python 环境缓存，可复用已验证的解释器；不支持时重新探测。
- 平台专属接入说明应放在仓库级文档或宿主配置中，不写入核心业务逻辑。
- Skill 内只依赖 Python、输入文件和脚本参数，不依赖特定 Agent 名称。

## Python 环境探测

优先使用：

```bash
python -c "import sys, pandas, openpyxl; print(sys.executable)"
```

若当前 Python 不满足依赖，再探测可用环境。未经用户明确同意，不自动创建虚拟环境或安装依赖。
