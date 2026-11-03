"""
TraceHarbor API — CORS Security & Origin Validation

Provides safe, audited CORS origin resolution and strict production validation:
- Multi-origin allowlist support via environment variables
- Development defaults (localhost/127.0.0.1) without leaking into production
- Strict rejection of wildcard '*' origins when credentials are enabled
- URL structure and scheme validation at application startup
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("traceharbor.cors")

DEV_DEFAULT_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


class CorsConfigurationError(ValueError):
    """Raised when CORS configuration violates security rules in production."""

    pass


def validate_single_origin(origin: str, allow_wildcard: bool = False) -> None:
    """
    Validate that an origin string is structurally sound and secure.
    Raises CorsConfigurationError if the origin is invalid.
    """
    clean = origin.strip()
    if not clean:
        raise CorsConfigurationError("CORS origin cannot be empty.")

    if clean == "*":
        if not allow_wildcard:
            raise CorsConfigurationError(
                "Wildcard origin ('*') is strictly prohibited when credentialed access "
                "is enabled. Specify explicit domain origins."
            )
        return

    if not (clean.startswith("http://") or clean.startswith("https://")):
        raise CorsConfigurationError(
            f"Invalid CORS origin '{origin}': Must begin with 'http://' or 'https://'."
        )

    if clean.endswith("/"):
        raise CorsConfigurationError(
            f"Invalid CORS origin '{origin}': Must not contain a trailing slash."
        )


def resolve_cors_origins(settings: "Settings") -> list[str]:
    """
    Compute the active allowed origins list for CORSMiddleware.

    In development (debug=True):
      - Merges any explicitly configured origins with standard local dev origins.

    In production (debug=False):
      - Returns only valid, explicitly configured origins.
      - Returns an empty list if unconfigured (blocking all cross-origin requests).
    """
    raw_configured: list[str] = (
        list(settings.cors_origins) if isinstance(settings.cors_origins, list) else []
    )

    if settings.debug:
        merged = set(raw_configured) | set(DEV_DEFAULT_ORIGINS)
        return sorted(merged)

    # In production mode: validate each configured origin
    valid_origins: list[str] = []
    for o in raw_configured:
        validate_single_origin(o, allow_wildcard=False)
        valid_origins.append(o.strip())

    return valid_origins


def validate_production_cors_at_startup(settings: "Settings") -> None:
    """
    Enforce strict CORS configuration at application startup in production mode.
    Raises CorsConfigurationError if CORS is missing or insecure.
    """
    if settings.debug:
        return

    raw_configured = settings.cors_origins
    if not raw_configured or len(raw_configured) == 0:
        raise CorsConfigurationError(
            "CORS_ORIGINS must be explicitly configured in production (DEBUG=false). "
            "Set CORS_ORIGINS to your frontend domain (e.g. 'https://traceharbor.vercel.app'). "
            "Wildcards and unconfigured fallbacks are prohibited."
        )

    for o in raw_configured:
        validate_single_origin(o, allow_wildcard=False)
        if "localhost" in o or "127.0.0.1" in o:
            logger.warning(
                "PRODUCTION_CONFIG_WARNING: Localhost origin '%s' configured in production. "
                "Ensure this is intentional.",
                o,
            )
