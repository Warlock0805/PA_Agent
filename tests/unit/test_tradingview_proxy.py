"""Unit tests for TradingView-only proxy configuration."""
from __future__ import annotations

import pytest

from pa_agent.data.tradingview_proxy import TradingViewProxy, use_tradingview_proxy


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
    assert seen["http_proxy_port"] == 7890
    assert seen["proxy_type"] == "http"
    assert tv_main.create_connection is fake_connection


def test_disabled_proxy_context_keeps_factory_unchanged(monkeypatch) -> None:
    import tvDatafeed.main as tv_main

    seen: dict[str, object] = {}

    def fake_connection(*args, **kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(tv_main, "create_connection", fake_connection)

    with use_tradingview_proxy(TradingViewProxy()):
        tv_main.create_connection("wss://example.invalid")

    assert seen == {}
    assert tv_main.create_connection is fake_connection
