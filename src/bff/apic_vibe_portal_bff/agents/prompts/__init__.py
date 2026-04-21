"""Lazy prompt loader for agent system prompts stored as markdown files.

This module provides utilities to load agent system prompts from external
markdown files with lazy loading and caching for performance.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory containing prompt markdown files
_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_prompt(prompt_name: str) -> str:
    """Load a prompt from a markdown file with caching.

    Prompts are loaded once on first access and cached for the lifetime
    of the process. The cache is thread-safe via functools.lru_cache.

    Parameters
    ----------
    prompt_name:
        Name of the prompt file without extension (e.g., "api_discovery_system").

    Returns
    -------
    str
        The prompt content as a string.

    Raises
    ------
    FileNotFoundError
        If the prompt file does not exist.
    RuntimeError
        If the prompt file is empty or cannot be read.
    """
    prompt_path = _PROMPTS_DIR / f"{prompt_name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        content = prompt_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise RuntimeError(f"Failed to read prompt file {prompt_path}: {exc}") from exc

    if not content:
        raise RuntimeError(f"Prompt file is empty: {prompt_path}")

    logger.debug("Loaded prompt '%s' from %s (%d chars)", prompt_name, prompt_path, len(content))
    return content


def clear_cache() -> None:
    """Clear the prompt cache.

    Useful for testing or when prompts need to be reloaded from disk.
    """
    load_prompt.cache_clear()
    logger.debug("Cleared prompt cache")
