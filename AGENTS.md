# PA Agent 智能体入口

## 项目目的

PA Agent 是 Windows 优先的价格行为分析桌面工具。它读取 MT5、TradingView 和 A 股等数据源的结构化 K 线，通过两阶段流程生成市场诊断与交易决策；它不连接券商执行下单。

## 入口地图

- `README.md`：产品范围、安装与启动。
- `pa_agent/main.py`：PyQt6 应用入口。
- `pa_agent/app_context.py`：数据源、AI 客户端、Prompt、校验器和记录组件装配。
- `pa_agent/orchestrator/two_stage.py`：阶段一诊断 → 策略路由 → 阶段二决策主链路。
- `pa_agent/data/`：行情源、K 线快照和数据规范化。
- `pa_agent/ai/`：模型客户端、Prompt、JSON 校验、归一化和决策规则。
- `pa_agent/gui/`：桌面界面与后台线程。
- `prompt_engineering/`：运行时 Prompt 与策略文本，属于行为事实源。
- `tests/`：单元、集成、端到端和 live 测试。
- `docs/WORKFLOW.md`：智能体实施、证据、授权和交接流程。
- `docs/TESTING.md`：分层验证命令与环境要求。
- `docs/HARNESS.md`：Harness 组件、风险与回收规则。

## 工作规则

- 开始前读取目标代码、直接相关测试和对应文档；不要扫描无关目录。
- 修复或新增行为必须先写能证明缺失行为的失败测试，再做最小实现。
- 保留现有 API、QClaw、WorkBuddy、Cursor 和数据源边界，除非任务明确要求改变。
- Prompt、JSON schema、策略路由或归一化变更必须补充相应 fixture/validator 测试。
- GUI 改动优先使用 `QT_QPA_PLATFORM=offscreen` 自动验证；可见窗口只用于明确授权的人工验收。
- 不运行 `live` 测试、不访问真实 API、不启动 MT5/浏览器、不发送通知，除非用户明确授权。
- 不提交 `config/settings.json`、`.env`、日志、分析记录、经验数据、交易导出或任何密钥。
- 删除、覆盖用户数据、发布、部署、推送、创建 PR、账号或付费操作必须有明确授权。
- 只修改任务允许的文件；测试通过不代表授权范围正确，交付前必须检查 diff。

## 常用命令

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q
.\.venv\Scripts\python.exe -m ruff check pa_agent tests
powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_project_harness.ps1
```

按风险选择更小的定向测试；完整命令与 live/e2e 边界见 `docs/TESTING.md`。

## 必须暂停交给人

- 需求会改变“只做辅助分析、不执行下单”的产品边界。
- 需要真实 API Key、真实账户、真实行情服务登录或产生费用。
- 需要删除/覆盖运行记录、配置、经验库或用户数据。
- 需要向 GitHub、飞书、PushPlus 或其他外部系统写入，但本轮没有明确授权。
- 现有代码、文档和用户最新口径存在会显著改变结果的冲突。
