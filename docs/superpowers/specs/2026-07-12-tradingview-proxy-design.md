# TradingView 专用代理设置设计

## 目标

让 Windows 版 PA Agent 在不依赖系统全局 VPN/TUN 的情况下，通过用户配置的本地 HTTP/HTTPS 或 SOCKS5 代理访问 TradingView。代理仅用于 TradingView 的连通性探测和 K 线 WebSocket 请求，不影响 MT5、Codex bridge 或其他数据源。

## 范围

- 支持启用/关闭、协议（HTTP/HTTPS、SOCKS5）、主机和端口。
- 不支持代理账号密码认证。
- 配置保存在本地 `config/settings.json`，该文件继续被 Git 忽略。
- 在 TradingView 数据源界面提供代理设置入口和连接测试。
- 连接探测与实际 `tvDatafeed` 请求共享同一代理适配逻辑。

## 方案选择

采用 TradingView 专用适配层：在调用 `tvDatafeed` 的 WebSocket 建连时传入 `websocket-client` 的代理参数。该层以短生命周期、受锁保护的方式覆盖 `tvDatafeed.main.create_connection`，避免修改环境变量或影响其他网络调用。

不采用系统全局代理或进程级 `HTTP_PROXY`：两者均会扩大作用范围，且不能可靠覆盖 SOCKS5 WebSocket。

## 配置与界面

`GeneralSettings` 新增以下字段：

- `tradingview_proxy_enabled`：默认 `false`。
- `tradingview_proxy_type`：`http` 或 `socks5`，默认 `http`。
- `tradingview_proxy_host`：默认空字符串。
- `tradingview_proxy_port`：默认 `0`。

新增“TradingView 代理设置”对话框，包含启用开关、协议下拉框、主机、端口与“测试连接”按钮。关闭代理时不校验主机和端口；启用时要求主机非空且端口在 1–65535 内。保存后，下一次 TradingView 获取数据使用新配置。

## 数据流

1. 用户保存代理设置。
2. TradingView 切换、连通性探测或 K 线抓取从设置创建代理配置。
3. 代理适配层验证并转成 `websocket-client` 参数。
4. 仅在 `tvDatafeed` 创建 WebSocket 的调用期间注入这些参数。
5. 调用结束后恢复原始连接函数；互斥锁保证没有并发泄漏。

无代理或禁用时，调用路径保持现有直连行为。

## 失败处理

- 配置错误：阻止保存并指出无效字段。
- 代理连接失败：提示“TradingView 代理不可达或协议不匹配”。
- TradingView 仍不可达：保留当前“无法使用 TradingView”处理，但不再建议必须使用全局 TUN。
- 不记录代理认证信息（本功能不支持认证）；日志仅可包含协议、主机和端口。

## 验收与测试

- 配置默认值、保存/加载和非法端口测试。
- HTTP 与 SOCKS5 代理参数映射测试。
- 禁用代理时不修改 WebSocket 调用测试。
- 连通性探测与历史 K 线抓取均使用同一代理适配器的测试。
- PyQt offscreen 测试：打开、保存、校验错误与测试连接入口。
- 不运行真实 TradingView 连通性测试；人工验收时由用户配置本机代理后点击测试连接。
