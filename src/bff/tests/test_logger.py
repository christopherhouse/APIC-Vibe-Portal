"""Tests for the structured logging configuration."""

from __future__ import annotations

import logging

from apic_vibe_portal_bff.utils.logger import configure_logging, get_logger


class TestConfigureLogging:
    """Tests for ``configure_logging``."""

    def test_suppresses_uvicorn_access(self) -> None:
        configure_logging(log_level="INFO")
        assert logging.getLogger("uvicorn.access").level == logging.WARNING

    def test_suppresses_azure_identity(self) -> None:
        configure_logging(log_level="INFO")
        assert logging.getLogger("azure.identity").level == logging.WARNING

    def test_suppresses_azure_http_logging_policy(self) -> None:
        configure_logging(log_level="INFO")
        assert logging.getLogger("azure.core.pipeline.policies.http_logging_policy").level == logging.WARNING

    def test_root_logger_level(self) -> None:
        configure_logging(log_level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_get_logger_returns_bound_logger(self) -> None:
        configure_logging(log_level="INFO")
        logger = get_logger("test")
        assert logger is not None
