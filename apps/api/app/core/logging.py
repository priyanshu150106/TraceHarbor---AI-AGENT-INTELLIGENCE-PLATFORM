"""
TraceHarbor API — Structured Logging Configuration

Uses structlog for JSON-formatted, context-rich logging with automatic
credential, token, and secret redaction.
"""

import logging
import re
import sys
from typing import Any

import structlog

SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "credentials",
)

SENSITIVE_PATTERN = re.compile(
    r"(th_live_[a-zA-Z0-9_\-]+|th_demo_[a-zA-Z0-9_\-]+|sk-[a-zA-Z0-9_\-]+|Bearer\s+[a-zA-Z0-9_\.\-]+)",
    re.IGNORECASE,
)


def _redact_value(val: Any) -> Any:
    if isinstance(val, str):
        return SENSITIVE_PATTERN.sub("[REDACTED]", val)
    if isinstance(val, dict):
        return {
            k: (
                "[REDACTED]"
                if any(s in k.lower() for s in SENSITIVE_KEY_SUBSTRINGS)
                else _redact_value(v)
            )
            for k, v in val.items()
        }
    if isinstance(val, (list, tuple)):
        return [_redact_value(item) for item in val]
    return val


def redact_sensitive_data(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that sanitizes secrets, authorization tokens, and API keys."""
    for key, value in list(event_dict.items()):
        if any(s in key.lower() for s in SENSITIVE_KEY_SUBSTRINGS):
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _redact_value(value)
    return event_dict


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog for the application with log redaction."""

    # Set the stdlib root logger level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_sensitive_data,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound with the given name."""
    return structlog.get_logger(name)
