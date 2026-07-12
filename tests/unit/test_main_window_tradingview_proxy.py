"""Regression coverage for TradingView proxy use when fetching data."""
from __future__ import annotations

from types import SimpleNamespace

from pa_agent.config.settings import Settings
from pa_agent.gui.main_window import MainWindow


def test_fetch_data_passes_saved_proxy_to_connectivity_probe(monkeypatch) -> None:
    settings = Settings()
    settings.general.tradingview_proxy_enabled = True
    settings.general.tradingview_proxy_type = "socks5"
    settings.general.tradingview_proxy_host = "127.0.0.1"
    settings.general.tradingview_proxy_port = 7890
    source = SimpleNamespace(_connected=True, _symbol="XAUUSD", _timeframe="1m")
    window = SimpleNamespace(
        _ctx=SimpleNamespace(data_source=source, settings=settings),
        _symbol_combo=SimpleNamespace(currentText=lambda: "XAUUSD"),
        _tf_combo=SimpleNamespace(currentText=lambda: "1m"),
        _current_data_source_kind=lambda: "tradingview",
        _stop_refresh_loop=lambda: None,
        _set_chart_refresh_paused=lambda _paused: None,
        _start_refresh_loop=lambda: None,
    )
    seen: dict[str, object] = {}

    def fake_probe(**kwargs):
        seen.update(kwargs)
        return True, None

    monkeypatch.setattr(
        "pa_agent.data.tradingview_connectivity.check_tradingview_connectivity",
        fake_probe,
    )
    monkeypatch.setattr("time.sleep", lambda *_args: None)

    MainWindow._on_fetch_data_clicked(window)

    proxy = seen["proxy"]
    assert proxy.enabled is True
    assert proxy.proxy_type == "socks5"
    assert proxy.host == "127.0.0.1"
    assert proxy.port == 7890
