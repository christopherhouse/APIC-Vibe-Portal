"""Token usage metrics — pre-call estimation (tiktoken) + post-call actuals.

Pre-call estimation uses ``tiktoken`` to count tokens before sending a request
to Azure OpenAI.  After the call, actual usage is recorded from the OpenAI
response ``usage`` object.  A drift warning is logged when the estimate is
off by more than 10 %.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai.types.completion_usage import CompletionUsage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-model token pricing (USD per 1K tokens, configurable)
# These are approximate GPT-4o prices as defaults.
# ---------------------------------------------------------------------------
_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "default": {"prompt": 0.005, "completion": 0.015},
}


def _get_pricing(model: str) -> dict[str, float]:
    return _PRICING.get(model, _PRICING["default"])


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in *text* for the given *model* using tiktoken.

    Falls back to a rough character-based estimate (chars / 4) when tiktoken
    cannot find an encoding for the model.
    """
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception as exc:  # noqa: BLE001
        logger.debug("tiktoken estimate failed (%s) — using fallback", exc)
        return max(1, len(text) // 4)


def record_estimated_tokens(
    token_count: int,
    *,
    model: str = "gpt-4o",
    component: str = "total",
) -> None:
    """Emit the ``apic.llm.tokens.estimated`` histogram entry.

    Args:
        token_count: Estimated number of tokens.
        model: Model name used for the attribute.
        component: Label for which part of the prompt this estimate covers
            (``system_prompt``, ``history``, ``rag_context``, ``user_message``,
            ``total``).
    """
    from apic_vibe_portal_bff.telemetry.metrics import get_tokens_estimated_histogram

    get_tokens_estimated_histogram().record(
        token_count,
        {"model": model, "component": component},
    )


def record_actual_token_usage(
    usage: CompletionUsage,
    *,
    model: str = "gpt-4o",
    estimated_total: int | None = None,
) -> None:
    """Emit actual token histograms from an OpenAI ``usage`` object.

    Also emits the estimated-cost histogram and logs a drift warning when
    the pre-call estimate is off by more than 10 %.

    Args:
        usage: ``CompletionUsage`` object from the OpenAI response.
        model: Model name used for histogram attributes.
        estimated_total: Optional pre-call estimate for drift tracking.
    """
    from apic_vibe_portal_bff.telemetry.metrics import (
        get_cost_estimated_histogram,
        get_tokens_completion_histogram,
        get_tokens_prompt_histogram,
        get_tokens_total_histogram,
    )

    attrs = {"model": model}

    prompt_tokens: int = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens: int = getattr(usage, "completion_tokens", 0) or 0
    total_tokens: int = getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)

    get_tokens_prompt_histogram().record(prompt_tokens, attrs)
    get_tokens_completion_histogram().record(completion_tokens, attrs)
    get_tokens_total_histogram().record(total_tokens, attrs)

    # --- Cost estimation ------------------------------------------------
    pricing = _get_pricing(model)
    estimated_cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1000.0
    get_cost_estimated_histogram().record(estimated_cost, attrs)

    # --- Drift tracking -------------------------------------------------
    if estimated_total is not None and total_tokens > 0:
        drift_pct = abs(estimated_total - total_tokens) / total_tokens * 100
        if drift_pct > 10:
            logger.warning(
                "Token count drift > 10%%: estimated=%d actual=%d drift=%.1f%%",
                estimated_total,
                total_tokens,
                drift_pct,
            )
