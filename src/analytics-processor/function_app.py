"""Analytics Processor — Service Bus to Cosmos DB event pipeline.

Consumes batches of analytics events from the ``analytics-events`` Service Bus
topic and writes them to the ``analytics-events`` Cosmos DB container using the
Cosmos DB output binding.

Enrichment (PII sanitisation, user ID hashing, timestamp, document
construction) is performed by the BFF before the message is sent to Service
Bus.  This function validates document structure and sanitises string values as
a defence-in-depth measure before persisting to Cosmos DB.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any, List  # noqa: UP035  # Functions Python worker rejects PEP 585 generics in binding annotations

import azure.functions as func
from azure.functions import Document, DocumentList

app = func.FunctionApp()

logger = logging.getLogger(__name__)

_COSMOS_DB_NAME = "apic-vibe-portal"
_COSMOS_CONTAINER_NAME = "analytics-events"

# ---------------------------------------------------------------------------
# Validation & sanitisation helpers
# ---------------------------------------------------------------------------

_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "eventType",
        "timestamp",
        "userId",
        "apiId",
        "metadata",
        "schemaVersion",
        "isDeleted",
        "deletedAt",
        "ttl",
    }
)

_REQUIRED_KEYS: frozenset[str] = frozenset({"id", "eventType", "timestamp"})

# Only word characters (letters, digits, underscore)
_EVENT_TYPE_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_]+$")

# Control characters excluding common whitespace (tab, newline, carriage-return)
_CONTROL_CHAR_RE: re.Pattern[str] = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_MAX_STRING_LENGTH = 2048
_MAX_EVENT_TYPE_LENGTH = 100
_MAX_ID_LENGTH = 255  # Cosmos DB document ID limit
_MAX_METADATA_KEY_LENGTH = 256
_MAX_METADATA_DEPTH = 10


def _sanitize_string(value: str, max_length: int = _MAX_STRING_LENGTH) -> str:
    """Strip control characters and enforce a maximum length."""
    return _CONTROL_CHAR_RE.sub("", value)[:max_length]


def _sanitize_metadata(meta: dict[str, Any], *, _depth: int = 0) -> dict[str, Any]:
    """Recursively sanitise metadata values, capped at ``_MAX_METADATA_DEPTH``."""
    if _depth >= _MAX_METADATA_DEPTH:
        return {}

    result: dict[str, Any] = {}
    for raw_key, value in meta.items():
        if not isinstance(raw_key, str):
            continue
        sanitized_key = _sanitize_string(raw_key, max_length=_MAX_METADATA_KEY_LENGTH)
        if isinstance(value, str):
            result[sanitized_key] = _sanitize_string(value)
        elif isinstance(value, dict):
            result[sanitized_key] = _sanitize_metadata(value, _depth=_depth + 1)
        elif isinstance(value, list):
            result[sanitized_key] = [
                _sanitize_string(item)
                if isinstance(item, str)
                else (_sanitize_metadata(item, _depth=_depth + 1) if isinstance(item, dict) else item)
                for item in value
            ]
        else:
            result[sanitized_key] = value
    return result


def _is_valid_timestamp(value: str) -> bool:
    """Return ``True`` if *value* is a parseable ISO-8601 timestamp."""
    try:
        dt = datetime.fromisoformat(value)
        # Reject dates far in the future or before 2020 (basic sanity)
        if dt.year < 2020 or dt > datetime.now(UTC).replace(year=datetime.now(UTC).year + 2):
            return False
    except (ValueError, OverflowError):
        return False
    return True


def _validate_and_sanitize(doc: Any) -> dict[str, Any] | None:
    """Validate document structure and sanitise string values.

    Returns the sanitised document ready for Cosmos DB, or ``None`` if the
    document fails structural validation.
    """
    if not isinstance(doc, dict):
        return None

    # Required keys must be present
    if not _REQUIRED_KEYS.issubset(doc.keys()):
        return None

    # ``id`` must be a non-empty string within Cosmos DB's 255-char limit
    raw_id = doc.get("id")
    if not isinstance(raw_id, str) or not raw_id or len(raw_id) > _MAX_ID_LENGTH:
        return None

    # ``timestamp`` must be a non-empty, parseable ISO-8601 string
    raw_ts = doc.get("timestamp")
    if not isinstance(raw_ts, str) or not raw_ts or not _is_valid_timestamp(raw_ts):
        return None

    # ``eventType`` must match the allowed pattern
    event_type = doc.get("eventType")
    if (
        not isinstance(event_type, str)
        or not _EVENT_TYPE_RE.match(event_type)
        or len(event_type) > _MAX_EVENT_TYPE_LENGTH
    ):
        return None

    # Strip unknown top-level keys
    sanitized: dict[str, Any] = {k: v for k, v in doc.items() if k in _ALLOWED_KEYS}

    # Sanitise string fields (skip eventType — already validated by regex)
    for key in ("id", "timestamp", "userId", "apiId", "deletedAt"):
        if key in sanitized and isinstance(sanitized[key], str):
            sanitized[key] = _sanitize_string(sanitized[key])

    # Validate / sanitise typed fields
    if "metadata" in sanitized:
        if isinstance(sanitized["metadata"], dict):
            sanitized["metadata"] = _sanitize_metadata(sanitized["metadata"])
        else:
            sanitized["metadata"] = {}

    if "schemaVersion" in sanitized and not isinstance(sanitized["schemaVersion"], int):
        sanitized.pop("schemaVersion")

    if "isDeleted" in sanitized and not isinstance(sanitized["isDeleted"], bool):
        sanitized.pop("isDeleted")

    if "ttl" in sanitized and not isinstance(sanitized["ttl"], int):
        sanitized.pop("ttl")

    return sanitized


# ---------------------------------------------------------------------------
# Function trigger
# ---------------------------------------------------------------------------

# OTel metrics — emitted as custom dimensions in App Insights via structured
# logging.  Azure Functions host forwards these to the configured
# APPLICATIONINSIGHTS_CONNECTION_STRING automatically.
_total_processed = 0
_total_failed = 0


@app.function_name(name="ProcessAnalyticsEvents")
@app.service_bus_topic_trigger(
    arg_name="messages",
    topic_name="analytics-events",
    subscription_name="cosmos-writer",
    connection="ServiceBusConnection",
    is_batched=True,
)
@app.cosmos_db_output(
    arg_name="documents",
    database_name=_COSMOS_DB_NAME,
    container_name=_COSMOS_CONTAINER_NAME,
    connection="CosmosDBConnection",
    create_if_not_exists=False,
)
def process_analytics_events(
    messages: List[func.ServiceBusMessage],  # noqa: UP006  # Functions worker rejects PEP 585 generics here
    documents: func.Out[DocumentList],
) -> None:
    """Process a batch of Service Bus messages and write them to Cosmos DB.

    Each message body is expected to be a JSON-serialised Cosmos document
    produced by the BFF ``AnalyticsService.record_events`` method.  Documents
    are validated and sanitised before being forwarded to the Cosmos output
    binding.
    """
    global _total_processed, _total_failed  # noqa: PLW0603
    start_time = time.monotonic()
    output_docs: list[str] = []
    failed = 0

    for message in messages:
        try:
            body = message.get_body().decode("utf-8")
            raw = json.loads(body)
            sanitized = _validate_and_sanitize(raw)
            if sanitized is None:
                failed += 1
                logger.warning(
                    "analytics.processor.validation_failed",
                    extra={
                        "message_id": message.message_id,
                        "event_type": raw.get("eventType", "<unknown>") if isinstance(raw, dict) else "<non-dict>",
                        "has_id": isinstance(raw, dict) and bool(raw.get("id")),
                        "has_timestamp": isinstance(raw, dict) and bool(raw.get("timestamp")),
                    },
                )
                continue
            output_docs.append(json.dumps(sanitized))
        except Exception:
            failed += 1
            logger.warning(
                "analytics.processor.message_failed",
                extra={"message_id": message.message_id},
                exc_info=True,
            )

    if output_docs:
        documents.set(DocumentList([Document.from_json(d) for d in output_docs]))

    _total_processed += len(output_docs)
    _total_failed += failed
    duration_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "analytics.processor.batch_complete",
        extra={
            "processed": len(output_docs),
            "failed": failed,
            "total": len(messages),
            "batch_size": len(messages),
            "duration_ms": round(duration_ms, 2),
            "cumulative_processed": _total_processed,
            "cumulative_failed": _total_failed,
        },
    )
