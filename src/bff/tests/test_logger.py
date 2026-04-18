"""Unit tests for the logger utility module."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.utils.logger import sanitize_for_log


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
