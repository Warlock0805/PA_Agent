from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from pa_agent.config.settings import Settings

_APPLICATION: QApplication | None = None


def _app() -> QApplication:
    global _APPLICATION
    _APPLICATION = QApplication.instance() or QApplication([])
    return _APPLICATION


def test_proxy_dialog_saves_enabled_socks5_proxy(monkeypatch) -> None:
    import pa_agent.gui.tradingview_proxy_dialog as dialog_module

    _app()
    settings = Settings()
    monkeypatch.setattr(dialog_module, "save_settings", lambda *_args, **_kwargs: None)
    dialog = dialog_module.TradingViewProxyDialog(settings)
    try:
        dialog._enabled_check.setChecked(True)
        dialog._type_combo.setCurrentIndex(dialog._type_combo.findData("socks5"))
        dialog._host_edit.setText("127.0.0.1")
        dialog._port_spin.setValue(7890)

        dialog._on_save()

        assert settings.general.tradingview_proxy_enabled is True
        assert settings.general.tradingview_proxy_type == "socks5"
        assert settings.general.tradingview_proxy_host == "127.0.0.1"
        assert settings.general.tradingview_proxy_port == 7890
    finally:
        dialog.close()


def test_proxy_dialog_rejects_empty_host_when_enabled(monkeypatch) -> None:
    import pa_agent.gui.tradingview_proxy_dialog as dialog_module

    _app()
    settings = Settings()
    dialog = dialog_module.TradingViewProxyDialog(settings)
    monkeypatch.setattr(dialog_module.QMessageBox, "warning", lambda *_args: None)
    try:
        dialog._enabled_check.setChecked(True)
        dialog._host_edit.setText("")
        dialog._port_spin.setValue(7890)

        dialog._on_save()

        assert settings.general.tradingview_proxy_enabled is False
    finally:
        dialog.close()
