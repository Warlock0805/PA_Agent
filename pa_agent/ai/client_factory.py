"""Construct the correct AI client for the configured provider route."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pa_agent.ai.cursor_connector import is_openclaw_cs_model
from pa_agent.config.settings import AIProviderSettings


def create_ai_client(
    settings: AIProviderSettings,
    logger_: logging.Logger | None = None,
    *,
    codex_bridge_dir: Path | None = None,
) -> Any:
    """Return the client selected by runtime mode and provider route."""
    log = logger_ or logging.getLogger(__name__)
    if settings.runtime_mode == "codex":
        from pa_agent.ai.codex_bridge import CodexBridgeClient

        log.info("AI client route: current Codex conversation")
        return CodexBridgeClient(settings=settings, bridge_dir=codex_bridge_dir)
    if is_openclaw_cs_model(settings.model):
        from pa_agent.ai.cursor_sdk_client import CursorSdkClient

        log.info("AI client route: Cursor SDK (model=%s)", settings.model)
        return CursorSdkClient(settings=settings, logger_=log)

    from pa_agent.ai.deepseek_client import DeepSeekClient

    log.info(
        "AI client route: OpenAI-compatible (model=%s base_url=%s)",
        settings.model,
        settings.base_url or "(empty)",
    )
    return DeepSeekClient(settings=settings, logger_=log)
