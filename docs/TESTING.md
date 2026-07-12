# 验证与测试

## 环境

- Windows 10/11。
- Python 3.11+。
- 推荐使用项目虚拟环境 `.venv`。
- 开发依赖：`.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`。

真实 MT5、TradingView 登录和模型 API 不属于默认测试前置条件。

## 分层命令

### 快速结构检查

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_project_harness.ps1
```

用于检查 Harness 入口、文档链接、命令一致性、eval 结构、忽略规则和敏感路径跟踪状态。

### 定向单元测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_target.py -q
```

新增或修复行为时先运行最小目标测试，再扩大范围。

### 默认离线回归

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q
```

这是普通代码改动的默认回归命令。它排除真实外部服务与端到端 UI 冒烟。

### 静态检查

```powershell
.\.venv\Scripts\python.exe -m ruff check pa_agent tests
```

格式化不是默认自动动作；只格式化本次改动文件，避免无关 diff。

### GUI 自动测试

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest <GUI相关测试路径> -q
```

不要把 offscreen 通过等同于人工视觉验收。布局、窗口焦点和系统对话框仍需要明确授权后的可见窗口检查。

### e2e 与 live

只有任务明确要求并授权真实外部影响时运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -m e2e -q
.\.venv\Scripts\python.exe -m pytest -m live -q
```

运行前必须确认：

- 使用哪个数据源、账号和模型。
- 是否会产生费用、通知或外部记录。
- Key 来自环境变量，不读取或打印 `config/settings.json`。
- 结果中不包含可识别账号信息。

## 改动到验证的映射

| 改动 | 最小验证 |
|---|---|
| 设置模型/持久化 | `test_settings_round_trip.py`、相关迁移测试 |
| AI 客户端/路由 | `test_client_factory.py`、provider route 测试 |
| Prompt/策略文件 | `test_prompt_assembler.py`、`test_prompt_txt_files.py`、路由测试 |
| JSON schema/归一化 | validator、stage1/stage2 normalizer 测试 |
| K 线快照/指标 | snapshot、kline、indicator 测试 |
| 主窗口/线程 | 目标 GUI 测试 + `test_switch_mid_analysis.py` |
| 敏感数据/记录 | pending writer、mask、pre-commit 与 Harness 检查 |
| Harness 文档/模板 | `tools/check_project_harness.ps1` |

## 证据格式

交付时记录：

```text
命令：<完整命令>
结果：PASS/FAIL，测试数或错误数
范围：该命令证明什么
未覆盖：仍需人工/live 验证的内容
```

“文件已修改”“命令应当能运行”或旧任务的测试结果不能作为本轮完成证据。
