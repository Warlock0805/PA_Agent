---
name: pa-agent
description: 启动 PA Agent 桌面窗口，并在当前 Codex 对话中完成其待处理的两阶段行情分析请求；适用于无需 API Key 的本地分析流程。
---

# PA Agent

用于把 PA Agent 的桌面端分析请求交给当前 Codex 对话处理。它只读取本地 K 线和提示词，返回分析 JSON；不会登录行情服务、调用真实 API 或执行下单。

## 启动桌面端

1. 将项目根目录设为当前工作目录，或设置 `PA_AGENT_HOME` 为项目根目录。
2. 运行本技能目录中的 `scripts/open_pa_agent.ps1`，并传入项目根目录。
3. 向用户说明窗口已经打开。不要尝试把 PyQt 窗口嵌入聊天界面。

若启动脚本报告项目目录或虚拟环境不存在，停止并如实说明，不要自动安装依赖或创建配置。

## 处理待分析请求

仅在用户要求处理当前分析、继续分析，或桌面端已发出请求时执行：

1. 在项目根目录运行 `& "$env:PA_AGENT_HOME\\.venv\\Scripts\\python.exe" -m pa_agent.codex_bridge_cli list`；无待处理请求时，提示用户在 PA Agent 窗口选择“当前 Codex 对话”模式并点击分析。
2. 若有多个请求，选择最新的未响应请求，并告知用户所选请求 ID 与阶段；不要猜测或伪造请求。
3. 使用 `& "$env:PA_AGENT_HOME\\.venv\\Scripts\\python.exe" -m pa_agent.codex_bridge_cli show <REQUEST_ID>` 读取完整 `messages`。严格遵循其中的 system、user 消息和 JSON 格式要求。
4. 在当前对话中完成分析。输出必须是一个可解析的 JSON 对象，不使用 Markdown 围栏，不附加说明文字。
5. 将 JSON 正文写入临时 UTF-8 文件，执行 `& "$env:PA_AGENT_HOME\\.venv\\Scripts\\python.exe" -m pa_agent.codex_bridge_cli respond <REQUEST_ID> --content-file <FILE>` 回填。若需要保留简短推理，使用单独的 `--reasoning-file`；不要把密钥、账户信息或无关对话写入其中。
6. 再运行一次同一模块的 `list` 命令。若阶段一已完成且出现阶段二请求，继续处理阶段二；阶段二完成后告知用户桌面端会显示结果。

## 约束

- 只处理 `stage1`、`stage2` 的本地 bridge 请求，且请求 ID 必须来自 `list`。
- 不读取、不展示、不修改 `config/settings.json`、`.env` 或任何密钥。
- 不运行 live 测试，不访问 MT5、浏览器、券商、真实 API 或外部行情服务。
- 不能因等待请求而臆造结果；请求过期、取消或响应写入失败时，报告错误并让用户重新提交。
