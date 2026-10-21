"""
TraceHarbor SDK — Truncation and Redaction Utilities
"""

import json
from typing import Any

# Default case-insensitive sensitive key patterns
DEFAULT_SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "access_token",
    "refresh_token",
    "private_key",
}


def redact_sensitive_data(
    data: Any,
    sensitive_keys: set[str] | None = None,
    mask: str = "[REDACTED]",
) -> Any:
    """
    Recursively traverse dictionaries and lists, masking values
    associated with sensitive keys.
    """
    if sensitive_keys is None:
        sensitive_keys = DEFAULT_SENSITIVE_KEYS

    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key).lower()
            if any(s in key_str for s in sensitive_keys):
                redacted[key] = mask
            else:
                redacted[key] = redact_sensitive_data(value, sensitive_keys, mask)
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item, sensitive_keys, mask) for item in data]
    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item, sensitive_keys, mask) for item in data)
    return data


def truncate_value(value: Any, limit: int = 10000) -> Any:
    """
    Truncate large text strings or serialized payloads to avoid excessive telemetry sizes.
    """
    if isinstance(value, str):
        if len(value) > limit:
            return value[:limit] + f"... [truncated {len(value) - limit} chars]"
        return value
    elif isinstance(value, (dict, list)):
        try:
            dumped = json.dumps(value, default=str)
            if len(dumped) > limit:
                return {"_raw_truncated": dumped[:limit] + f"... [truncated {len(dumped) - limit} chars]"}
        except Exception:
            pass
    return value
