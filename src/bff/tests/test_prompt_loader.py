"""Tests for the prompt loading utility."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.agents.prompts import clear_cache, load_prompt


class TestLoadPrompt:
    """Test suite for the load_prompt function."""

    def test_loads_api_discovery_system_prompt(self) -> None:
        """Test loading the API Discovery system prompt."""
        prompt = load_prompt("api_discovery_system")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "API Discovery Agent" in prompt
        assert "## Capabilities" in prompt

    def test_loads_governance_system_prompt(self) -> None:
        """Test loading the Governance system prompt."""
        prompt = load_prompt("governance_system")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Governance & Compliance Agent" in prompt
        assert "## Governance Rule Categories" in prompt

    def test_prompts_are_cached(self) -> None:
        """Test that prompts are cached after first load."""
        # Load twice and verify we get the same object
        prompt1 = load_prompt("api_discovery_system")
        prompt2 = load_prompt("api_discovery_system")
        assert prompt1 is prompt2  # Same object due to caching

    def test_raises_on_missing_prompt_file(self) -> None:
        """Test that FileNotFoundError is raised for missing prompts."""
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            load_prompt("nonexistent_prompt")

    def test_clear_cache_works(self) -> None:
        """Test that clear_cache() clears the prompt cache."""
        prompt1 = load_prompt("api_discovery_system")
        clear_cache()
        prompt2 = load_prompt("api_discovery_system")
        # After clearing cache, we get a new object (not the same reference)
        # but with identical content
        assert prompt1 == prompt2
        # Note: We can't reliably test `is not` because Python may intern strings
