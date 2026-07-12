# PA Agent Codex 主控模式开发计划

> **给 Terra 模型：** 必须按任务顺序执行。每个任务均采用 RED → GREEN → 回归验证；不得跳过失败测试，不得扩大范围。只允许在 `codex/codex-controller-mode` 分支提交，只允许推送 `origin`，禁止推送 `upstream`。

**目标：** 让用户无需在 PA Agent 中配置模型 API Key，即可从当前 Codex 对话处理 PA Agent 的两阶段分析请求，并在 Codex 发起后打开独立的 PyQt6 桌面界面查看完整结果。

**架构：** 保留现有 `TwoStageOrchestrator`、Prompt 组装、策略路由、JSON 校验、记录落盘和 GUI 回填链路。新增一个实现现有 AI 客户端接口的 `CodexBridgeClient`：编排器调用它时，它将完整消息写入本地交换目录并阻塞等待 Codex 回写；Codex skill 使用稳定 CLI 读取请求、在当前对话完成推理、再写回结果。原 API 模式继续使用现有客户端，不改变行为。

**技术栈：** Python 3.11+、PyQt6、Pydantic 2、pytest、JSON 文件协议、PowerShell、Codex skill。

## 全局约束

- 不调用、不读取、不导出 PA Agent 的模型 API Key；Codex 模式允许 `provider.api_key == ""`。
- PyQt6 界面以独立 Windows 窗口打开，不宣称嵌入 Codex 对话区域。
- PA Agent 不能主动调用或占用当前 Codex 对话；必须由用户在 Codex 中发起或继续任务。
- 第一版只保证单次分析闭环，不实现持续盯盘、无人值守后台服务和多任务并发抢占。
- 保留原 `api` 模式，现有 OpenAI 兼容、QClaw、WorkBuddy 和 Cursor 路由不得回归。
- 现有交易边界不变：不连接券商执行下单，不把输出描述成投资建议。
- 交换文件必须位于 Git 忽略目录，不得提交 Prompt 实例、行情实例、分析结果、密钥或登录信息。
- 所有运行时写入必须使用 UTF-8；JSON 写入必须采用同目录临时文件后原子替换。
- GUI 同时只允许一个活动分析请求；取消后的迟到结果不得回填。
- 不修改无关代码、文案和格式，不进行架构重写。
- Git 远程约束：`origin=https://github.com/Warlock0805/PA_Agent.git`；`upstream` 只读且 push URL 保持 `DISABLED`。

---

## 一、目标使用流程

### 流程 A：打开界面

用户在 Codex 中输入：

```text
打开 PA Agent
```

Codex skill：

1. 定位 `D:\about-ai\PA_Agent` 或由环境变量 `PA_AGENT_HOME` 指定的项目目录。
2. 检查 PA Agent 窗口是否已经运行。
3. 未运行时使用项目虚拟环境以独立进程启动 `python -m pa_agent.main`。
4. 已运行时不创建第二个窗口，并提示用户复用当前窗口。

### 流程 B：单次两阶段分析

1. 用户在 PA Agent 中选择数据源、品种和周期，点击“提交分析”。
2. Codex 模式下，阶段一完整 messages 写入交换目录，GUI 显示“等待当前 Codex 对话处理阶段一”。
3. 用户在 Codex 中输入“处理 PA Agent 待分析请求”。
4. Codex skill 读取最新有效请求，并在当前对话中生成严格 JSON。
5. skill 写回阶段一结果；现有编排器执行校验、归一化、策略路由和经验加载。
6. 编排器生成阶段二请求；同一 Codex 任务继续读取并回答阶段二。
7. 现有编排器校验并保存完整记录，GUI 更新诊断、决策树、支撑阻力和未来走势。

### 第一版明确不承诺

- 用户只在 GUI 点击按钮后，Codex 能在没有活动任务的情况下自动醒来。
- PA Agent 窗口直接向任意 Codex 会话发送消息。
- Codex 退出后桌面程序仍能自行完成 AI 分析。
- 同时处理多个 PA Agent 窗口或多个活动请求。

---

## 二、文件变更地图

### 新建文件

- `pa_agent/ai/codex_bridge.py`：协议常量、原子 JSON 存储、等待/取消逻辑和 `CodexBridgeClient`。
- `pa_agent/codex_bridge_cli.py`：供 Codex skill 调用的 `list/show/respond/cancel/doctor` 命令。
- `tests/unit/test_codex_bridge.py`：文件协议、匹配、超时、取消、迟到结果测试。
- `tests/unit/test_codex_bridge_cli.py`：CLI 输入输出、UTF-8 和错误码测试。
- `tests/unit/test_codex_mode_ui.py`：设置界面、API Key 门禁和 Codex 状态文案测试。
- `tests/integration/test_codex_two_stage_bridge.py`：两阶段编排器通过桥接完成的集成测试。
- `codex/skills/pa-agent/SKILL.md`：可安装的 PA Agent Codex 工作流。
- `codex/skills/pa-agent/scripts/open_pa_agent.ps1`：独立启动 GUI，并避免明显重复启动。
- `codex/skills/pa-agent/scripts/install.ps1`：将 skill 安装到用户 Codex skills 目录。

### 修改文件

- `pa_agent/config/settings.py`：增加 `runtime_mode` 和统一的分析就绪判断。
- `pa_agent/config/paths.py`：增加桥接运行时目录常量。
- `pa_agent/ai/client_factory.py`：Codex 模式路由到 `CodexBridgeClient`。
- `pa_agent/app_context.py`：Codex 模式跳过外部智能体提供商自动同步。
- `pa_agent/orchestrator/two_stage.py`：在每次模型调用前向支持该接口的客户端设置阶段上下文。
- `pa_agent/gui/ai_model_settings_dialog.py`：增加运行模式选择，Codex 模式禁用 API 字段。
- `pa_agent/gui/settings_dialog.py`：保持旧设置入口与新运行模式一致。
- `pa_agent/gui/main_window.py`：Codex 模式不弹 API Key 提示，显示等待 Codex 的状态。
- `tests/unit/test_client_factory.py`：增加 Codex 客户端路由测试。
- `tests/unit/test_api_key_configured.py`：增加 Codex 模式无需 Key 的就绪测试。
- `tests/unit/test_settings_round_trip.py`：增加运行模式持久化测试。
- `.gitignore`：忽略 `runtime/codex_bridge/`。
- `pyproject.toml`：增加 `pa-agent-codex = "pa_agent.codex_bridge_cli:main"` 命令入口。

---

## 三、交换协议

协议版本固定为整数 `1`。

### 请求文件

路径：

```text
runtime/codex_bridge/requests/<request_id>.json
```

结构：

```json
{
  "protocol_version": 1,
  "request_id": "32位十六进制UUID",
  "status": "pending",
  "stage": "stage1",
  "created_at": "2026-07-12T08:00:00.000+00:00",
  "expires_at": "2026-07-12T08:10:00.000+00:00",
  "messages": [
    {"role": "system", "content": "完整系统提示"},
    {"role": "user", "content": "完整用户提示"}
  ]
}
```

字段要求：

- `request_id` 由 `uuid.uuid4().hex` 生成。
- `stage` 只能为 `stage1` 或 `stage2`。
- `messages` 原样保存现有编排器交给 AI 客户端的消息，不新增隐藏指令。
- 文件不得包含 `api_key`、`api_key_encrypted`、数据源密码或通知凭据。

### 响应文件

路径：

```text
runtime/codex_bridge/responses/<request_id>.json
```

结构：

```json
{
  "protocol_version": 1,
  "request_id": "与请求完全相同",
  "created_at": "2026-07-12T08:01:00.000+00:00",
  "content": "模型输出的完整JSON字符串",
  "reasoning_content": "可为空；不得要求Codex暴露隐藏推理"
}
```

### 状态规则

- 请求存在且响应不存在：`pending`。
- CLI 成功写入响应：`responded`，通过响应文件存在性判断，不就地重写请求。
- 用户取消：在 `runtime/codex_bridge/cancelled/<request_id>.json` 写取消标记。
- 客户端等待时每次轮询先检查取消标记和 `CancelToken`。
- 超时只抛出 `TimeoutError` 并由现有编排器记录失败；不得自动删除证据文件。
- 只有 `protocol_version`、`request_id` 和阶段上下文匹配时才返回响应。

---

## Task 1：配置模型和 API Key 门禁

**文件：**

- 修改：`pa_agent/config/settings.py`
- 修改：`tests/unit/test_api_key_configured.py`
- 修改：`tests/unit/test_settings_round_trip.py`

**接口：**

```python
RuntimeMode = Literal["api", "codex"]

class AIProviderSettings(BaseModel):
    runtime_mode: RuntimeMode = "api"

def provider_analysis_ready(settings: Settings | None) -> bool:
    ...
```

- `provider_api_key_configured()` 保持原语义，只回答 Key 是否存在。
- `provider_analysis_ready()` 在 `codex` 模式返回 `True`，在 `api` 模式复用原 Key 判断。

- [ ] 写失败测试：默认模式是 `api`，保存并加载后保持 `codex`。
- [ ] 写失败测试：Codex 模式空 Key 时 `provider_analysis_ready()` 为真。
- [ ] 写失败测试：API 模式空 Key 时仍为假。
- [ ] 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_key_configured.py tests\unit\test_settings_round_trip.py -q
```

预期 RED：缺少 `runtime_mode` 或 `provider_analysis_ready`。

- [ ] 最小实现上述字段和函数。
- [ ] 重跑相同命令，预期全部 PASS。
- [ ] 提交：

```powershell
git add pa_agent/config/settings.py tests/unit/test_api_key_configured.py tests/unit/test_settings_round_trip.py
git commit -m "feat: add Codex analysis runtime mode"
```

---

## Task 2：桥接存储与原子协议

**文件：**

- 新建：`pa_agent/ai/codex_bridge.py`
- 修改：`pa_agent/config/paths.py`
- 修改：`.gitignore`
- 新建：`tests/unit/test_codex_bridge.py`

**接口：**

```python
PROTOCOL_VERSION = 1

@dataclass(frozen=True, slots=True)
class BridgeRequest:
    request_id: str
    path: Path

class CodexBridgeStore:
    def __init__(self, root: Path, *, poll_interval_s: float = 0.2) -> None: ...
    def create_request(self, *, messages: list[dict[str, Any]], stage: str,
                       timeout_s: float) -> BridgeRequest: ...
    def list_pending_requests(self) -> list[dict[str, Any]]: ...
    def read_request(self, request_id: str) -> dict[str, Any]: ...
    def write_response(self, request_id: str, *, content: str,
                       reasoning_content: str = "") -> Path: ...
    def cancel_request(self, request_id: str) -> Path: ...
    def wait_for_response(self, request_id: str, *, timeout_s: float,
                          cancel_token: CancelToken | None = None) -> dict[str, Any]: ...
```

**实现规则：**

- `_atomic_write_json()` 必须在目标目录创建唯一 `.tmp` 文件，再调用 `Path.replace()`。
- `write_response()` 必须先确认请求存在；未知 ID 抛 `ValueError("找不到请求: ...")`。
- `read_request()` 拒绝未知协议版本、ID 不匹配和损坏 JSON。
- `wait_for_response()` 使用 `time.monotonic()` 计算超时。
- `cancel_token.is_set()` 或取消标记存在时抛现有 `CancelledError`。
- `CODEX_BRIDGE_DIR = PROJECT_ROOT / "runtime" / "codex_bridge"`。
- `.gitignore` 增加 `runtime/codex_bridge/`。

- [ ] 分别写以下失败测试：创建请求、原子文件无残留、列出 pending、匹配响应、未知请求、协议版本错误、超时、取消、损坏半成品忽略。
- [ ] 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_codex_bridge.py -q
```

预期 RED：模块不存在。

- [ ] 最小实现并重跑，预期全部 PASS。
- [ ] 验证忽略规则：

```powershell
git check-ignore runtime/codex_bridge/requests/example.json
```

预期输出该路径。

- [ ] 提交：

```powershell
git add .gitignore pa_agent/config/paths.py pa_agent/ai/codex_bridge.py tests/unit/test_codex_bridge.py
git commit -m "feat: add atomic Codex bridge protocol"
```

---

## Task 3：CodexBridgeClient 与阶段上下文

**文件：**

- 修改：`pa_agent/ai/codex_bridge.py`
- 修改：`pa_agent/orchestrator/two_stage.py`
- 修改：`tests/unit/test_codex_bridge.py`
- 新建或修改：`tests/unit/test_two_stage_bridge_context.py`

**接口：**

```python
class CodexBridgeClient:
    def __init__(self, settings: AIProviderSettings, *,
                 store: CodexBridgeStore | None = None,
                 bridge_dir: Path | None = None,
                 logger_: logging.Logger | None = None) -> None: ...
    def update_provider(self, settings: AIProviderSettings) -> None: ...
    def set_stage_context(self, stage: Literal["stage1", "stage2"]) -> None: ...
    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> AIReply: ...
    def stream_chat(self, messages: list[dict[str, Any]], *,
                    on_reasoning_token: Callable[[str], None] | None = None,
                    on_content_token: Callable[[str], None] | None = None,
                    cancel_token: CancelToken | None = None,
                    timeout_s: float = 600.0, **kwargs: Any) -> AIReply: ...
```

**编排器改动：**

在 `TwoStageOrchestrator` 增加私有方法：

```python
def _set_client_stage_context(self, stage: str) -> None:
    setter = getattr(self._client, "set_stage_context", None)
    if callable(setter):
        setter(stage)
```

必须在以下调用前设置：

- 首次阶段一 `stream_chat()` 前：`stage1`。
- 每次阶段一重试前：`stage1`。
- 首次阶段二 `stream_chat()` 前：`stage2`。
- 每次阶段二重试前：`stage2`。

普通 `DeepSeekClient`、`CursorSdkClient` 不增加该方法，编排器通过鸭子类型保持兼容。

**AIReply 规则：**

- `content` 与 `reasoning_content` 来自响应文件。
- `request_id` 使用桥接请求 ID。
- `model` 固定为 `codex-conversation`。
- token usage 全部为 `0`，不得伪造 Codex token 统计。
- 响应到达后分别调用一次 reasoning/content 回调，以复用现有实时页。

- [ ] 写失败测试：stage1/stage2 请求阶段正确。
- [ ] 写失败测试：响应转换为 `AIReply`。
- [ ] 写失败测试：取消、超时向编排器传播。
- [ ] 写失败测试：现有非桥接假客户端没有 `set_stage_context` 仍能运行。
- [ ] 运行定向测试并确认 RED。
- [ ] 最小实现，重跑确认 PASS。
- [ ] 运行现有编排器测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_validation_retry.py tests\integration\test_switch_mid_analysis.py -q
```

- [ ] 提交：

```powershell
git add pa_agent/ai/codex_bridge.py pa_agent/orchestrator/two_stage.py tests/unit/test_codex_bridge.py tests/unit/test_two_stage_bridge_context.py
git commit -m "feat: route two-stage model calls through Codex bridge"
```

---

## Task 4：桥接 CLI

**文件：**

- 新建：`pa_agent/codex_bridge_cli.py`
- 修改：`pyproject.toml`
- 新建：`tests/unit/test_codex_bridge_cli.py`

**命令：**

```text
pa-agent-codex [--bridge-dir PATH] list
pa-agent-codex [--bridge-dir PATH] show REQUEST_ID
pa-agent-codex [--bridge-dir PATH] respond REQUEST_ID --content-file FILE [--reasoning-file FILE]
pa-agent-codex [--bridge-dir PATH] cancel REQUEST_ID
pa-agent-codex [--bridge-dir PATH] doctor
```

**输出契约：**

- stdout 只输出 UTF-8 JSON，方便 Codex 稳定解析。
- 正常返回码 `0`。
- 用户输入错误、未知请求返回码 `2`。
- 文件或协议损坏返回码 `3`。
- `list` 默认只输出摘要：`request_id/stage/created_at/expires_at`，不输出大 Prompt。
- `show` 输出单个请求的完整 messages。
- `respond` 只接受文件路径，不接受超长命令行 content，避免 Windows 转义和长度问题。
- `doctor` 输出项目根目录、桥接目录、Python 路径、pending 数量和协议版本；不得输出密钥。

`pyproject.toml` 增加：

```toml
[project.scripts]
pa-agent = "pa_agent.main:main"
pa-agent-codex = "pa_agent.codex_bridge_cli:main"
```

- [ ] 写失败测试覆盖五个命令、中文内容、未知 ID、缺失文件和 stdout 纯 JSON。
- [ ] 运行并确认 RED：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_codex_bridge_cli.py -q
```

- [ ] 实现后确认 PASS。
- [ ] 手工执行：

```powershell
.\.venv\Scripts\python.exe -m pa_agent.codex_bridge_cli doctor
```

- [ ] 提交：

```powershell
git add pyproject.toml pa_agent/codex_bridge_cli.py tests/unit/test_codex_bridge_cli.py
git commit -m "feat: add Codex bridge command interface"
```

---

## Task 5：客户端工厂与启动上下文接入

**文件：**

- 修改：`pa_agent/ai/client_factory.py`
- 修改：`pa_agent/app_context.py`
- 修改：`tests/unit/test_client_factory.py`
- 新建：`tests/unit/test_app_context_codex_mode.py`

**工厂接口：**

```python
def create_ai_client(
    settings: AIProviderSettings,
    logger_: logging.Logger | None = None,
    *,
    codex_bridge_dir: Path | None = None,
) -> Any:
```

路由优先级：

1. `runtime_mode == "codex"` → `CodexBridgeClient`。
2. 否则保留现有 Cursor SDK 路由。
3. 其余保留现有 OpenAI 兼容客户端。

`AppContext.bootstrap()` 规则：

- Codex 模式不调用 `sync_qclaw_agent_provider_on_load()`。
- Codex 模式不调用 `sync_workbuddy_provider_on_load()`。
- Codex 模式不调用 `sync_cursor_provider_on_load()`。
- 数据源连接、PromptAssembler、JsonValidator、PendingWriter 和 SessionTokenLedger 仍正常创建。
- `PendingWriter` 可继续接收空 Key，日志脱敏逻辑不变。

- [ ] 写失败测试：Codex 模式返回桥接客户端。
- [ ] 写失败测试：API 模式所有既有路由不变。
- [ ] 写失败测试：Codex 模式启动不调用三个 provider sync。
- [ ] 最小实现并运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_client_factory.py tests\unit\test_app_context_codex_mode.py tests\unit\test_provider_override_by_model.py -q
```

- [ ] 提交：

```powershell
git add pa_agent/ai/client_factory.py pa_agent/app_context.py tests/unit/test_client_factory.py tests/unit/test_app_context_codex_mode.py
git commit -m "feat: bootstrap PA Agent in Codex mode"
```

---

## Task 6：AI 设置界面

**文件：**

- 修改：`pa_agent/gui/ai_model_settings_dialog.py`
- 修改：`pa_agent/gui/settings_dialog.py`
- 新建：`tests/unit/test_codex_mode_ui.py`

**UI 结构：**

在提供商表单第一行增加：

```text
AI 运行模式：[当前 Codex 对话（无需 API Key）▼]
```

ComboBox 数据：

```python
self._runtime_mode_combo.addItem("API 模式", "api")
self._runtime_mode_combo.addItem("当前 Codex 对话（无需 API Key）", "codex")
```

Codex 模式下禁用但不清空：

- 模型名。
- Base URL。
- API Key。
- Thinking。
- Reasoning Effort。
- API Key 帮助按钮。
- 外部智能体教程按钮可保持可用。

切回 API 模式时恢复字段，原值必须保留。

保存规则：

- 先读取并保存 `runtime_mode`。
- Codex 模式跳过所有 Base URL/模型校验和 QClaw/WorkBuddy/Cursor 自动配置。
- API 模式完全沿用原保存分支。

- [ ] 使用 `QT_QPA_PLATFORM=offscreen` 写失败测试：加载 codex、字段禁用、切回恢复、空 API 字段可保存。
- [ ] 写失败测试：API 模式既有校验仍触发。
- [ ] 实现并运行：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest tests\unit\test_codex_mode_ui.py -q
```

- [ ] 提交：

```powershell
git add pa_agent/gui/ai_model_settings_dialog.py pa_agent/gui/settings_dialog.py tests/unit/test_codex_mode_ui.py
git commit -m "feat: expose Codex mode in AI settings"
```

---

## Task 7：主窗口门禁、状态和取消

**文件：**

- 修改：`pa_agent/gui/main_window.py`
- 修改：`tests/unit/test_codex_mode_ui.py`

**行为变更：**

- `_has_api_key_configured()` 不再直接用于提交门禁；改为 `_analysis_runtime_ready()` 并调用 `provider_analysis_ready()`。
- API 模式无 Key：保留原警告和自动打开设置行为。
- Codex 模式无 Key：不显示警告，不自动聚焦 API Key，不锁定提交按钮。
- `_ai_mode_label` 在 Codex 模式显示：`AI：当前 Codex 对话 · 无需 API Key`。
- `_on_status_update()` 收到阶段开始事件时，如果是 Codex 模式，显示：
  - `阶段一请求已生成，等待当前 Codex 对话处理…`
  - `阶段二请求已生成，等待当前 Codex 对话处理…`
- 点击现有取消操作必须设置 `CancelToken`；桥接客户端应在一次轮询周期内退出。
- 现有 `_on_record_ready()`、`_on_analysis_finished()` 和各面板回填不分叉。

**不得实现：** 新建第二套结果渲染逻辑或绕过 `TwoStageOrchestrator` 直接操作面板。

- [ ] 写失败测试：Codex 模式空 Key 可提交。
- [ ] 写失败测试：API 模式空 Key仍锁定。
- [ ] 写失败测试：启动提示只在 API 模式出现。
- [ ] 写失败测试：Codex 等待文案正确。
- [ ] 最小实现并运行相关 GUI 测试。
- [ ] 运行现有主窗口相关测试目录，确认无回归。
- [ ] 提交：

```powershell
git add pa_agent/gui/main_window.py tests/unit/test_codex_mode_ui.py
git commit -m "feat: support Codex mode in the main window"
```

---

## Task 8：两阶段桥接集成测试

**文件：**

- 新建：`tests/integration/test_codex_two_stage_bridge.py`

**测试结构：**

创建真实的：

- `CodexBridgeStore`。
- `CodexBridgeClient`。
- `TwoStageOrchestrator`。
- 固定 `KlineFrame`。
- 项目已有 `PromptAssembler`、`JsonValidator`、策略路由。

测试线程模拟 Codex，只做以下工作：

1. 等待 stage1 请求出现。
2. 断言请求 messages 包含真实 K 线 Prompt。
3. 写回仓库现有测试夹具中可通过校验的阶段一 JSON。
4. 等待 stage2 请求出现。
5. 断言阶段二 Prompt 包含阶段一诊断和命中的策略内容。
6. 写回可通过校验的阶段二 JSON。
7. 等待编排器完成。

断言：

- `record.stage1_diagnosis` 非空。
- `record.stage2_decision` 非空。
- `record.exception is None`。
- `record.strategy_files_used` 非空或符合固定夹具的预期。
- PendingWriter 保存完整记录。
- 模拟过程中没有创建 OpenAI 客户端，也没有网络调用。

另写取消测试：阶段一 pending 后设置 `CancelToken`，线程在 1 秒内退出，记录为取消而非程序错误。

- [ ] 先确认 RED，再实现缺失集成行为。
- [ ] 运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_codex_two_stage_bridge.py -q
```

- [ ] 提交：

```powershell
git add tests/integration/test_codex_two_stage_bridge.py
git commit -m "test: verify Codex two-stage analysis bridge"
```

---

## Task 9：Codex skill 与 Windows 启动脚本

**前置要求：** 实施该任务时必须先读取并遵循 `skill-creator` skill；不要凭记忆编写 SKILL.md。

**文件：**

- 新建：`codex/skills/pa-agent/SKILL.md`
- 新建：`codex/skills/pa-agent/scripts/open_pa_agent.ps1`
- 新建：`codex/skills/pa-agent/scripts/install.ps1`

### SKILL.md 触发范围

自然语言触发包括：

- 打开、启动、运行 PA Agent。
- 查看 PA Agent 界面。
- 分析 PA Agent 当前图表。
- 处理 PA Agent 待分析请求。
- 继续阶段二分析。

### skill 执行规则

1. 优先使用 `PA_AGENT_HOME`；未设置时仅检查仓库中记录的默认路径，不扫描整盘。
2. “打开 PA Agent”调用 `open_pa_agent.ps1`。
3. “处理待分析”先执行 CLI `list`。
4. 没有 pending 请求时说明用户需在 GUI 点击“提交分析”，不伪造请求。
5. 有多个 pending 时只选择最新且未过期的请求，并把 request ID 告知用户。
6. 调用 `show` 读取完整 messages。
7. 严格服从请求中的 system/user Prompt，最终生成单一 JSON 对象；不得添加 Markdown 围栏。
8. 将 JSON 写入工作区临时文件，再使用 `respond --content-file` 回写。
9. 回写 stage1 后再次执行 `list`，等待编排器生成 stage2；最多轮询 30 秒。
10. stage2 回写成功后读取 CLI 状态并报告 GUI 已收到结果。
11. 不在对话中粘贴 API Key，不修改 `config/settings.json` 中的凭据。

### open_pa_agent.ps1

脚本参数：

```powershell
param([string]$ProjectRoot = $env:PA_AGENT_HOME)
```

规则：

- 解析绝对项目路径，确认存在 `pyproject.toml` 和 `pa_agent/main.py`。
- 优先使用 `<ProjectRoot>\.venv\Scripts\python.exe`。
- 缺少虚拟环境时输出 JSON 错误，不自动全局安装依赖。
- 使用 `Start-Process -WindowStyle Hidden` 启动帮助进程；PA Agent 自身窗口由 PyQt6 显示。
- 通过命令行和项目路径检查已有进程，避免重复启动明显相同实例。
- stdout 输出：`{"status":"started|already_running","project_root":"..."}`。

### install.ps1

- 默认安装目标：`$env:CODEX_HOME\skills\pa-agent`；未设置 `CODEX_HOME` 时使用 `$HOME\.codex\skills\pa-agent`。
- 复制前校验源 `SKILL.md` 存在。
- 如果目标已存在，先比较内容；不同则备份到带时间戳目录，不直接删除。
- 安装后输出目标路径和“新任务中验证”的提示。

- [ ] 使用 skill-creator 提供的验证方式检查 skill 元数据和结构。
- [ ] 在临时 `CODEX_HOME` 测试安装脚本，不写真实用户目录。
- [ ] 测试打开脚本的缺失路径、缺失虚拟环境和重复启动分支。
- [ ] 提交：

```powershell
git add codex/skills/pa-agent
git commit -m "feat: add installable PA Agent Codex skill"
```

---

## Task 10：完整回归、安全审计与人工验收

**不得在测试中使用真实 API Key 或产生真实模型费用。**

### 自动验证

- [ ] 安装完整开发依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

- [ ] 运行桥接定向测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_codex_bridge.py tests\unit\test_codex_bridge_cli.py tests\unit\test_codex_mode_ui.py tests\integration\test_codex_two_stage_bridge.py -q
```

- [ ] 运行全部非 live 测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live" -q
```

- [ ] 运行静态检查：

```powershell
.\.venv\Scripts\python.exe -m ruff check pa_agent tests
```

- [ ] 检查敏感数据和桥接目录未被跟踪：

```powershell
git status --short
git ls-files runtime config/settings.json
rg -n "api_key_encrypted|sk-[A-Za-z0-9]" runtime codex pa_agent tests
```

预期：`git ls-files` 不列出运行时或设置文件；`rg` 不出现真实密钥。

- [ ] 检查远程安全边界：

```powershell
git remote -v
```

预期：`upstream` push 为 `DISABLED`。

### 人工验收

- [ ] 在测试配置中选择“当前 Codex 对话（无需 API Key）”并保存。
- [ ] 清空模型 API Key，重启 PA Agent，确认不出现 Key 强制提示。
- [ ] 从 Codex 输入“打开 PA Agent”，确认只打开一个窗口。
- [ ] GUI 加载行情后点击“提交分析”，确认显示阶段一等待状态。
- [ ] 从 Codex 输入“处理 PA Agent 待分析请求”，完成两个阶段。
- [ ] 确认诊断、决策、决策树、支撑阻力和未来走势回填。
- [ ] 处理中点击取消，确认迟到响应不回填。
- [ ] 切回 API 模式，确认空 Key 再次正确锁定提交。
- [ ] 使用测试假客户端验证 API 模式原两阶段链路不变。

### 最终提交与上传

- [ ] 确认工作区仅包含预期功能文件。
- [ ] 创建最终整体验证提交（仅当存在验证修正）：

```powershell
git add <仅本次验证修正文件>
git commit -m "test: complete Codex mode verification"
```

- [ ] 只推送用户 fork：

```powershell
git push -u origin codex/codex-controller-mode
```

- [ ] 禁止执行：

```text
git push upstream ...
gh pr create --repo rosemarycox5334-debug/PA_Agent ...
```

---

## 四、完成定义

以下条件必须全部成立：

1. Codex 模式空 API Key 时可启动、加载行情并提交分析。
2. Codex 能通过 skill 打开或复用独立 PA Agent 窗口。
3. 阶段一和阶段二都由当前 Codex 对话处理，不调用 PA Agent 的模型 API。
4. 两阶段输出仍经过现有 JsonValidator、归一化、策略路由和记录落盘。
5. GUI 使用现有回填链路显示完整结果，没有第二套并行渲染逻辑。
6. 请求取消、超时、损坏文件、未知协议和迟到响应都有自动测试。
7. 原 API、QClaw、WorkBuddy 和 Cursor 路由测试继续通过。
8. 交换目录、配置文件和分析实例不进入 Git。
9. skill 能在临时 Codex Home 中安装并通过结构校验。
10. 代码只上传 `Warlock0805/PA_Agent` 的 `codex/codex-controller-mode` 分支，原仓库不发生任何写入。

## 五、Terra 执行纪律

- 每个 Task 开始前重新读取本 Task 的“文件、接口、约束”。
- 每个新行为必须先有失败测试，并记录失败原因确实是功能缺失。
- 一个 Task 完成后只提交该 Task 文件，不夹带下一个 Task。
- 遇到现有测试失败时先判断是否环境依赖；不得为了绿灯删除或放宽既有断言。
- GUI 测试优先使用 offscreen；只有最终人工验收才启动可见窗口。
- 不将 Codex 隐藏推理写入 `reasoning_content`；该字段可以为空或只写简短可展示摘要。
- 不把 Codex 订阅能力描述成免费或无限；仅说明 PA Agent 无需单独 API Key。
- 任何需要扩大到持续盯盘、自动唤醒或多请求并发的需求，另建计划，不并入本实现。
