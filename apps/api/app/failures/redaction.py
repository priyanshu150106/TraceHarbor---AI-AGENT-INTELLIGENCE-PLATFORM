"""
TraceHarbor API — Failure Text Redaction and Sanitization

Strips PII, credentials, file paths, and sensitive parameters from error
messages before persistence or embedding. All failure text passes through
this module before being stored as normalized_text.
"""

import re

# Pre-compiled URL credential pattern
_URL_CREDS_PATTERN = re.compile(r"(https?://)([^@]+)@")
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")


def _redact_url_match(match: re.Match) -> str:
    """Redact credentials from URLs while preserving the host."""
    url = match.group(0)
    url = _URL_CREDS_PATTERN.sub(r"\1[CREDENTIALS_REDACTED]@", url)
    if "?" in url:
        base = url.split("?")[0]
        url = f"{base}?[PARAMS_REDACTED]"
    return url


# Compiled redaction patterns (order matters)
_COMPILED_PATTERNS: list[tuple[re.Pattern, str]] = [
    # API keys and tokens
    (
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|bearer|authorization)[=:\s]+\S+"
        ),
        r"\1=[REDACTED]",
    ),
    # Email addresses
    (
        re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
        "[EMAIL_REDACTED]",
    ),
    # IP addresses (IPv4)
    (
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b"),
        "[IP_REDACTED]",
    ),
    # Phone numbers
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE_REDACTED]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    # Credit card patterns
    (
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "[CARD_REDACTED]",
    ),
    # Base64 encoded blobs (long sequences)
    (
        re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9])"),
        "[BASE64_REDACTED]",
    ),
]

# File path patterns
_PATH_PATTERN = re.compile(
    r"(?:[A-Z]:\\|/(?:home|Users|tmp|var|etc)/)\S+"
)


def redact_text(text: str) -> str:
    """
    Apply all redaction patterns to the input text.
    Returns sanitized text safe for embedding and storage.
    """
    if not text:
        return text

    result = text

    # Redact URLs first (handles credentials and params)
    result = _URL_PATTERN.sub(_redact_url_match, result)

    # Redact file paths
    result = _PATH_PATTERN.sub("[PATH_REDACTED]", result)

    # Apply remaining patterns
    for pattern, replacement in _COMPILED_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def normalize_error_text(text: str) -> str:
    """
    Normalize error text for consistent embedding comparison:
    1. Redact sensitive content
    2. Collapse whitespace
    3. Remove line numbers and memory addresses
    4. Lowercase for consistency
    5. Truncate to bounded length
    """
    if not text:
        return ""

    result = redact_text(text)

    # Remove specific line numbers and memory addresses
    result = re.sub(r"\bline \d+\b", "line N", result, flags=re.IGNORECASE)
    result = re.sub(r"\b0x[0-9a-fA-F]+\b", "0xADDR", result)
    result = re.sub(r"at \d+:\d+", "at N:N", result)

    # Collapse whitespace
    result = re.sub(r"\s+", " ", result).strip()

    # Lowercase
    result = result.lower()

    # Truncate to 2000 chars to bound embedding input
    max_len = 2000
    if len(result) > max_len:
        result = result[:max_len]

    return result


def sanitize_error_summary(text: str, max_length: int = 500) -> str:
    """
    Create a human-readable error summary from raw error text.
    Redacts sensitive content but preserves casing and structure.
    """
    if not text:
        return "Unknown error"

    result = redact_text(text)

    # Collapse excess whitespace but preserve some structure
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r"[ \t]+", " ", result)
    result = result.strip()

    if len(result) > max_length:
        result = result[: max_length - 3] + "..."

    return result or "Unknown error"
