from __future__ import annotations

from pathlib import Path

import pa_agent.ai.cursor_connector as cursor
import pa_agent.ai.qclaw_connector as qclaw
import pa_agent.ai.workbuddy_connector as workbuddy
from pa_agent.app_context import _sync_provider_routes_on_load
from pa_agent.config.settings import Settings


def test_codex_mode_skips_provider_route_sync(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(qclaw, "sync_qclaw_agent_provider_on_load", lambda *_args, **_kwargs: called.append("qclaw"))
    monkeypatch.setattr(workbuddy, "sync_workbuddy_provider_on_load", lambda *_args, **_kwargs: called.append("workbuddy"))
    monkeypatch.setattr(cursor, "sync_cursor_provider_on_load", lambda *_args, **_kwargs: called.append("cursor"))

    settings = Settings()
    settings.provider.runtime_mode = "codex"
    _sync_provider_routes_on_load(settings, Path("settings.json"))

    assert called == []


def test_api_mode_keeps_provider_route_sync(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(qclaw, "sync_qclaw_agent_provider_on_load", lambda *_args, **_kwargs: called.append("qclaw"))
    monkeypatch.setattr(workbuddy, "sync_workbuddy_provider_on_load", lambda *_args, **_kwargs: called.append("workbuddy"))
    monkeypatch.setattr(cursor, "sync_cursor_provider_on_load", lambda *_args, **_kwargs: called.append("cursor"))

    _sync_provider_routes_on_load(Settings(), Path("settings.json"))

    assert called == ["qclaw", "workbuddy", "cursor"]
