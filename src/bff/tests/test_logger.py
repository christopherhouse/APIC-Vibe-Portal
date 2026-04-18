"""Unit tests for the logger utility module."""

from __future__ import annotations

import logging

from apic_vibe_portal_bff.utils.logger import configure_logging, get_logger, sanitize_for_log


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


class TestSanitizeForLog:
    def test_returns_safe_string_unchanged(self):
        assert sanitize_for_log("hello world") == "hello world"

    def test_strips_newline(self):
        assert sanitize_for_log("line1\nline2") == "line1line2"

    def test_strips_carriage_return(self):
        assert sanitize_for_log("line1\rline2") == "line1line2"

    def test_strips_crlf(self):
        assert sanitize_for_log("line1\r\nline2") == "line1line2"

    def test_strips_multiple_newlines(self):
        assert sanitize_for_log("a\nb\nc") == "abc"

    def test_empty_string(self):
        assert sanitize_for_log("") == ""

    def test_preserves_tabs_and_spaces(self):
        assert sanitize_for_log("hello\tworld  ") == "hello\tworld  "
