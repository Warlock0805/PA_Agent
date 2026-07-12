# TradingView 专用代理设置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 PA Agent 增加仅作用于 TradingView 的 HTTP/HTTPS 与 SOCKS5 代理设置。

**Architecture:** 新建 `tradingview_proxy`，提供配置校验和受锁保护的 WebSocket 代理补丁；TradingViewSource 与连通性探测共用它。PyQt 对话框编辑 GeneralSettings，并异步测试连接。

**Tech Stack:** Python 3.12、PyQt6、Pydantic、pytest、websocket-client、tvDatafeed。

## Global Constraints

- 代理不得修改进程环境变量，且不得影响 MT5、Codex bridge 或其他数据源。
- 仅支持无需账号密码的 HTTP/HTTPS、SOCKS5。
- 不提交 `config/settings.json`，不运行真实 TradingView、MT5 或 live 测试。
- 每项行为先写失败测试，再实现最小代码。

---

### Task 1: 代理配置模型与持久化

**Files:**
- Create: `pa_agent/data/tradingview_proxy.py`
- Modify: `pa_agent/config/settings.py:60-105`
- Test: `tests/unit/test_tradingview_proxy.py`
- Test: `tests/unit/test_settings_round_trip.py`

**Interfaces:**
- Produces: `TradingViewProxy(enabled: bool, proxy_type: Literal["http", "socks5"], host: str, port: int)`
- Produces: `TradingViewProxy.websocket_options() -> dict[str, object]`
- Produces: `TradingViewProxy.from_general(general: GeneralSettings) -> TradingViewProxy`

- [ ] **Step 1: 写入失败测试**

```python
def test_enabled_socks5_proxy_maps_to_websocket_options() -> None:
    proxy = TradingViewProxy(True, "socks5", "127.0.0.1", 7890)
    assert proxy.websocket_options() == {
        "http_proxy_host": "127.0.0.1",
        "http_proxy_port": 7890,
        "proxy_type": "socks5",
    }

def test_disabled_proxy_emits_no_options() -> None:
    assert TradingViewProxy(False, "http", "", 0).websocket_options() == {}
```

在 `test_settings_round_trip.py` 增加保存和加载四个代理字段的测试，并添加启用且空主机或端口 0 时抛出 `ValueError("TradingView 代理地址无效")` 的测试。

- [ ] **Step 2: 运行红灯**

Run: `D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy.py tests\unit\test_settings_round_trip.py -q`

Expected: FAIL，原因是代理类和设置字段尚不存在。

- [ ] **Step 3: 最小实现**

在 `GeneralSettings` 添加：

```python
tradingview_proxy_enabled: bool = False
tradingview_proxy_type: Literal["http", "socks5"] = "http"
tradingview_proxy_host: str = ""
tradingview_proxy_port: int = Field(default=0, ge=0, le=65535)
```

实现不可变 `TradingViewProxy`；禁用返回空字典，启用时检查主机与 1–65535 端口并映射为 websocket-client 选项。

- [ ] **Step 4: 运行绿灯**

Run: `D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy.py tests\unit\test_settings_round_trip.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add pa_agent/data/tradingview_proxy.py pa_agent/config/settings.py tests/unit/test_tradingview_proxy.py tests/unit/test_settings_round_trip.py
git commit -m "feat: add TradingView proxy configuration"
```

### Task 2: 代理注入、K 线抓取与连通性探测

**Files:**
- Modify: `pa_agent/data/tradingview_proxy.py`
- Modify: `pa_agent/data/tradingview.py:76-125,176-222`
- Modify: `pa_agent/data/tradingview_connectivity.py:14-83`
- Test: `tests/unit/test_tradingview_proxy.py`
- Test: `tests/unit/test_tradingview_connectivity.py`
- Test: `tests/unit/test_tradingview_socket.py`

**Interfaces:**
- Produces: `use_tradingview_proxy(proxy: TradingViewProxy | None) -> ContextManager[None]`
- Updates: `TradingViewSource.__init__(..., proxy: TradingViewProxy | None = None)` and `set_proxy(proxy)`
- Updates: `check_tradingview_connectivity(..., proxy: TradingViewProxy | None = None)`

- [ ] **Step 1: 写入失败测试**

```python
def test_proxy_context_forwards_options_and_restores_factory(monkeypatch) -> None:
    import tvDatafeed.main as tv_main
    seen: dict[str, object] = {}

    def fake_connection(*args, **kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(tv_main, "create_connection", fake_connection)
    proxy = TradingViewProxy(True, "http", "127.0.0.1", 7890)
    with use_tradingview_proxy(proxy):
        tv_main.create_connection("wss://example.invalid")
    assert seen["http_proxy_host"] == "127.0.0.1"
    assert tv_main.create_connection is fake_connection
```

增加测试：`TradingViewSource._fetch_hist_with_retry` 与 `check_tradingview_connectivity(proxy=...)` 都进入代理上下文；禁用代理时不传代理选项。

- [ ] **Step 2: 运行红灯**

Run: `D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy.py tests\unit\test_tradingview_connectivity.py tests\unit\test_tradingview_socket.py -q`

Expected: FAIL，原因是上下文或新参数不存在。

- [ ] **Step 3: 最小实现**

实现模块级 `threading.RLock` 和上下文管理器：

```python
@contextmanager
def use_tradingview_proxy(proxy: TradingViewProxy | None):
    if proxy is None or not proxy.enabled:
        yield
        return
    import tvDatafeed.main as tv_main
    options = proxy.websocket_options()
    with _PATCH_LOCK:
        original = tv_main.create_connection
        def patched(*args, **kwargs):
            return original(*args, **kwargs, **options)
        tv_main.create_connection = patched
        try:
            yield
        finally:
            tv_main.create_connection = original
```

在每次 `TvDatafeed.get_hist()` 调用外包裹该上下文。不要设置 `HTTP_PROXY`、`HTTPS_PROXY` 或 `ALL_PROXY`。源对象仅保存自己的代理；探测函数仅使用传入参数。

- [ ] **Step 4: 运行绿灯**

Run: `D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy.py tests\unit\test_tradingview_connectivity.py tests\unit\test_tradingview_socket.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add pa_agent/data/tradingview_proxy.py pa_agent/data/tradingview.py pa_agent/data/tradingview_connectivity.py tests/unit/test_tradingview_proxy.py tests/unit/test_tradingview_connectivity.py tests/unit/test_tradingview_socket.py
git commit -m "feat: route TradingView through configured proxy"
```

### Task 3: TradingView 代理设置界面

**Files:**
- Create: `pa_agent/gui/tradingview_proxy_dialog.py`
- Modify: `pa_agent/gui/main_window.py:400-520,1188-1268,1455-1468`
- Test: `tests/unit/test_tradingview_proxy_dialog.py`

**Interfaces:**
- Produces: `TradingViewProxyDialog(settings: Settings, parent: QWidget | None = None)`
- Produces: `current_proxy() -> TradingViewProxy`
- Consumes: `check_tradingview_connectivity(proxy=proxy)`
- Updates: `MainWindow._open_tradingview_proxy_dialog()`

- [ ] **Step 1: 写入失败 offscreen 测试**

```python
def test_proxy_dialog_saves_enabled_socks5_proxy(qapp) -> None:
    settings = Settings()
    dialog = TradingViewProxyDialog(settings)
    dialog._enabled_check.setChecked(True)
    dialog._type_combo.setCurrentIndex(1)
    dialog._host_edit.setText("127.0.0.1")
    dialog._port_spin.setValue(7890)
    dialog._on_save()
    assert settings.general.tradingview_proxy_type == "socks5"
    assert settings.general.tradingview_proxy_port == 7890
```

再覆盖：启用但空主机时保存失败；测试按钮将当前输入构造的 `TradingViewProxy` 传入探测函数；主窗口在当前源为 `TradingViewSource` 时调用 `set_proxy`。

- [ ] **Step 2: 运行红灯**

Run: `$env:QT_QPA_PLATFORM='offscreen'; D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy_dialog.py -q`

Expected: FAIL，原因是对话框不存在。

- [ ] **Step 3: 最小实现**

创建对话框，控件精确为：

```python
self._enabled_check = QCheckBox("通过代理连接 TradingView")
self._type_combo.addItem("HTTP / HTTPS", "http")
self._type_combo.addItem("SOCKS5", "socks5")
self._host_edit.setPlaceholderText("127.0.0.1")
self._port_spin.setRange(1, 65535)
```

在 TradingView 交易所控件旁放置 `QPushButton("TV 代理…")`，仅 TradingView 数据源时可见。测试按钮使用 `QThread` 调用 `check_tradingview_connectivity(proxy=current_proxy())`，完成后显示成功或包含详细原因的失败消息；不阻塞 GUI。保存调用 `save_settings`，主窗口更新当前 TradingViewSource 的代理，下一次获取数据生效。

- [ ] **Step 4: 运行绿灯**

Run: `$env:QT_QPA_PLATFORM='offscreen'; D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy_dialog.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```powershell
git add pa_agent/gui/tradingview_proxy_dialog.py pa_agent/gui/main_window.py tests/unit/test_tradingview_proxy_dialog.py
git commit -m "feat: add TradingView proxy settings dialog"
```

### Task 4: 错误引导与最终验证

**Files:**
- Modify: `pa_agent/gui/tv_connectivity_dialog.py`
- Modify: `tests/unit/test_tradingview_connectivity.py`
- Modify: `tests/unit/test_tradingview_proxy_dialog.py`

**Interfaces:**
- Preserves: `show_tv_connectivity_blocked_dialog(parent) -> Literal["mt5", "cloud", "cancel"]`

- [ ] **Step 1: 写入失败测试**

```python
def test_connectivity_dialog_mentions_in_app_proxy_setting() -> None:
    from pa_agent.gui.tv_connectivity_dialog import _MESSAGE
    assert "TradingView 代理" in _MESSAGE
```

- [ ] **Step 2: 运行红灯**

Run: `D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_connectivity.py::test_connectivity_dialog_mentions_in_app_proxy_setting -q`

Expected: FAIL，文本尚未包含应用内代理提示。

- [ ] **Step 3: 最小实现**

在既有“解决方案”首项增加：“在 PA Agent 的 TradingView 代理设置中填写本地 HTTP/HTTPS 或 SOCKS5 代理”。保留 MT5 和云服务器建议，且不自动打开外部浏览器。

- [ ] **Step 4: 运行最终验证**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m pytest tests\unit\test_tradingview_proxy.py tests\unit\test_tradingview_proxy_dialog.py tests\unit\test_tradingview_connectivity.py tests\unit\test_tradingview_socket.py tests\unit\test_settings_round_trip.py -q
D:\about-ai\PA_Agent\.venv\Scripts\python.exe -m ruff check pa_agent\data\tradingview_proxy.py pa_agent\data\tradingview.py pa_agent\data\tradingview_connectivity.py pa_agent\gui\tradingview_proxy_dialog.py tests\unit\test_tradingview_proxy.py tests\unit\test_tradingview_proxy_dialog.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_project_harness.ps1
git diff --check
```

Expected: 定向测试、指定文件 lint、Harness 检查与 diff 检查全部通过。

- [ ] **Step 5: 提交**

```powershell
git add pa_agent/gui/tv_connectivity_dialog.py tests/unit/test_tradingview_connectivity.py tests/unit/test_tradingview_proxy_dialog.py
git commit -m "docs: guide TradingView proxy recovery"
```

