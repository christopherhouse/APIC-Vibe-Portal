"""Tests for configuration / settings validation."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.config.settings import Settings


class TestSettings:
    """Test Pydantic Settings loading."""

    def test_defaults(self) -> None:
        """Settings should load with sensible defaults."""
        settings = Settings()
        assert settings.port == 8000
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.frontend_url == "http://localhost:3000"

    def test_override_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables should override defaults."""
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("FRONTEND_URL", "https://portal.example.com")
        monkeypatch.setenv("API_CENTER_ENDPOINT", "https://apic.example.com")

        settings = Settings()
        assert settings.port == 9000
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.frontend_url == "https://portal.example.com"
        assert settings.api_center_endpoint == "https://apic.example.com"

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting names are case-insensitive."""
        monkeypatch.setenv("port", "7777")
        settings = Settings()
        assert settings.port == 7777

    def test_extra_env_vars_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown environment variables should not cause errors."""
        monkeypatch.setenv("TOTALLY_UNKNOWN_VAR", "hello")
        settings = Settings()
        assert settings.port == 8000  # defaults still work
