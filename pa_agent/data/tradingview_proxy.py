"""TradingView-only WebSocket proxy configuration."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pa_agent.config.settings import GeneralSettings


ProxyType = Literal["http", "socks5"]
_PATCH_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class TradingViewProxy:
    """A local proxy used only while TradingView opens a WebSocket."""

    enabled: bool = False
    proxy_type: ProxyType = "http"
    host: str = ""
    port: int = 0

    @classmethod
    def from_general(cls, general: GeneralSettings) -> TradingViewProxy:
        return cls(
            enabled=bool(general.tradingview_proxy_enabled),
            proxy_type=general.tradingview_proxy_type,
            host=general.tradingview_proxy_host,
            port=general.tradingview_proxy_port,
        )

    def websocket_options(self) -> dict[str, object]:
        """Return websocket-client options, validating enabled configurations."""
        if not self.enabled:
            return {}
        host = self.host.strip()
        if not host or not 1 <= self.port <= 65535:
            raise ValueError("TradingView 代理地址无效")
        return {
            "http_proxy_host": host,
            "http_proxy_port": self.port,
            "proxy_type": self.proxy_type,
        }


@contextmanager
def use_tradingview_proxy(proxy: TradingViewProxy | None):
    """Temporarily apply *proxy* to tvDatafeed WebSocket creation only."""
    if proxy is None or not proxy.enabled:
        yield
        return

    import tvDatafeed.main as tv_main

    options = proxy.websocket_options()
    with _PATCH_LOCK:
        original = tv_main.create_connection

        def create_connection_with_proxy(*args, **kwargs):
            return original(*args, **{**kwargs, **options})

        tv_main.create_connection = create_connection_with_proxy
        try:
            yield
        finally:
            tv_main.create_connection = original
