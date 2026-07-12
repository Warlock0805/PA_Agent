"""Tests for API key presence helper."""
from __future__ import annotations

from pa_agent.config.settings import Settings, provider_api_key_configured


def test_provider_api_key_configured_empty() -> None:
    s = Settings()
    s.provider.api_key = ""
    assert not provider_api_key_configured(s)
    assert not provider_api_key_configured(None)


def test_provider_api_key_configured_whitespace() -> None:
    s = Settings()
    s.provider.api_key = "   "
    assert not provider_api_key_configured(s)


def test_provider_api_key_configured_present() -> None:
    s = Settings()
    s.provider.api_key = "sk-test"
    assert provider_api_key_configured(s)


def test_provider_analysis_ready_without_key_in_codex_mode() -> None:
    from pa_agent.config.settings import provider_analysis_ready

    settings = Settings()
    settings.provider.runtime_mode = "codex"
    settings.provider.api_key = ""
    assert provider_analysis_ready(settings)


def test_provider_analysis_ready_requires_key_in_api_mode() -> None:
    from pa_agent.config.settings import provider_analysis_ready

    settings = Settings()
    settings.provider.runtime_mode = "api"
    settings.provider.api_key = ""
    assert not provider_analysis_ready(settings)
