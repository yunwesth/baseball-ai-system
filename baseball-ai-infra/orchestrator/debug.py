"""
Debug tracing utilities for the Baseball AI system.

Debug messages are written to stderr so normal JSON output remains clean.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from config import DEBUG


def _safe_value(value: Any) -> Any:
    """
    Convert values into JSON-safe data and redact secrets.
    """
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}

        for key, item in value.items():
            normalized_key = key.lower()

            if any(
                secret_word in normalized_key
                for secret_word in (
                    "api_key",
                    "authorization",
                    "password",
                    "secret",
                    "token",
                )
            ):
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = _safe_value(item)

        return cleaned

    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return repr(value)


def debug_event(
    source: str,
    destination: str,
    event: str,
    data: Any = None,
) -> None:
    """
    Print one structured debug event when DEBUG is enabled.
    """
    if not DEBUG:
        return

    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "source": source,
        "destination": destination,
        "data": _safe_value(data),
    }

    print(
        "[DEBUG] "
        + json.dumps(
            message,
            ensure_ascii=False,
            default=str,
        ),
        file=sys.stderr,
        flush=True,
    )
