"""
TraceHarbor API — Safety Evidence Redaction Utilities

Safely scrubs synthetic canaries, API keys, credentials, and sensitive test tokens
from evaluator evidence and displayed test logs to prevent secondary leakage.
"""

import json
import re
from typing import Any

# Regex patterns for common sensitive tokens and canary formats
COMMON_CANARY_PATTERNS = [
    re.compile(r"(TR_CANARY_[A-Za-z0-9_\-]+)", re.IGNORECASE),
    re.compile(r"(CANARY_[A-Za-z0-9_\-]+)", re.IGNORECASE),
    re.compile(r"(SECRET_CANARY_[A-Za-z0-9_\-]+)", re.IGNORECASE),
]

CREDENTIAL_PATTERNS = [
    (re.compile(r"(th_live_[A-Za-z0-9_\-]{8,})", re.IGNORECASE), "th_live_***[REDACTED]"),
    (re.compile(r"(sk-[A-Za-z0-9_\-]{16,})", re.IGNORECASE), "sk-***[REDACTED]"),
    (re.compile(r"(ghp_[A-Za-z0-9_\-]{16,})", re.IGNORECASE), "ghp_***[REDACTED]"),
    (re.compile(r"(xox[baprs]-[A-Za-z0-9_\-]{10,})", re.IGNORECASE), "slack_token_***[REDACTED]"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{16,}", re.IGNORECASE), r"\1***[REDACTED]"),
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "****-****-****-[REDACTED]"),
    (
        re.compile(r'("(?:password|secret|api_key|token|access_token)":\s*")[^"]+(")', re.IGNORECASE),
        r"\1***[REDACTED]\2",
    ),
    (
        re.compile(r"((?:password|secret|api_key|token)=\s*)[^\s&;,]+", re.IGNORECASE),
        r"\1***[REDACTED]",
    ),
]


def redact_sensitive_content(
    val: Any,
    custom_canaries: list[str] | None = None,
) -> Any:
    """
    Recursively sanitize sensitive values from text, dicts, or lists.
    Guarantees that known canaries and secret patterns are redacted before storage or display.
    """
    if val is None:
        return None
    if isinstance(val, bool | int | float):
        return val

    if isinstance(val, dict):
        return {
            k: redact_sensitive_content(v, custom_canaries=custom_canaries)
            for k, v in val.items()
        }

    if isinstance(val, list):
        return [redact_sensitive_content(item, custom_canaries=custom_canaries) for item in val]

    if not isinstance(val, str):
        try:
            text = json.dumps(val, default=str)
        except Exception:
            text = str(val)
    else:
        text = val

    redacted_text = text

    # 1. Redact explicit custom canaries configured on test cases
    if custom_canaries:
        for canary in custom_canaries:
            if not canary or len(canary.strip()) < 3:
                continue
            canary_stripped = canary.strip()
            # Replace exact substring matches case-insensitively
            pattern = re.compile(re.escape(canary_stripped), re.IGNORECASE)
            masked = canary_stripped[:4] + "***[REDACTED]" if len(canary_stripped) > 4 else "***[REDACTED]"
            redacted_text = pattern.sub(masked, redacted_text)

    # 2. Redact common canary formats (TR_CANARY_..., CANARY_...)
    for pat in COMMON_CANARY_PATTERNS:
        def _mask_canary(match: re.Match) -> str:
            full = match.group(1)
            prefix = full[:6]
            return f"{prefix}***[REDACTED]"

        redacted_text = pat.sub(_mask_canary, redacted_text)

    # 3. Redact credentials and tokens
    for pat, repl in CREDENTIAL_PATTERNS:
        redacted_text = pat.sub(repl, redacted_text)

    return redacted_text
