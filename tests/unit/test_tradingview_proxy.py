"""Unit tests for TradingView-only proxy configuration."""
from __future__ import annotations

import pytest

from pa_agent.data.tradingview_proxy import TradingViewProxy


def test_enabled_socks5_proxy_maps_to_websocket_options() -> None:
    proxy = TradingViewProxy(True, "socks5", "127.0.0.1", 7890)

    assert proxy.websocket_options() == {
        "http_proxy_host": "127.0.0.1",
        "http_proxy_port": 7890,
        "proxy_type": "socks5",
    }


def test_disabled_proxy_emits_no_options() -> None:
    assert TradingViewProxy(False, "http", "", 0).websocket_options() == {}


@pytest.mark.parametrize(
    ("host", "port"),
    [("", 7890), ("127.0.0.1", 0), ("127.0.0.1", 65536)],
)
def test_enabled_proxy_rejects_invalid_address(host: str, port: int) -> None:
    proxy = TradingViewProxy(True, "http", host, port)

    with pytest.raises(ValueError, match="TradingView 代理地址无效"):
        proxy.websocket_options()
