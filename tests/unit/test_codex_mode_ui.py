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


def test_ai_model_dialog_loads_codex_mode_and_disables_api_fields() -> None:
    from pa_agent.gui.ai_model_settings_dialog import AIModelSettingsDialog

    _app()
    settings = Settings()
    settings.provider.runtime_mode = "codex"
    dialog = AIModelSettingsDialog(settings)
    try:
        assert dialog._runtime_mode_combo.currentData() == "codex"
        assert not dialog._model_edit.isEnabled()
        assert not dialog._base_url_edit.isEnabled()
        assert not dialog._api_key_edit.isEnabled()
    finally:
        dialog.close()


def test_ai_model_dialog_saves_codex_mode_without_validating_api_fields(monkeypatch) -> None:
    import pa_agent.gui.ai_model_settings_dialog as dialog_module

    _app()
    settings = Settings()
    dialog = dialog_module.AIModelSettingsDialog(settings)
    monkeypatch.setattr(dialog_module, "save_settings", lambda *_args, **_kwargs: None)
    dialog._runtime_mode_combo.setCurrentIndex(dialog._runtime_mode_combo.findData("codex"))
    dialog._model_edit.setText("")
    dialog._base_url_edit.setText("")
    dialog._api_key_edit.setText("")
    try:
        dialog._on_save()
        assert settings.provider.runtime_mode == "codex"
    finally:
        dialog.close()
