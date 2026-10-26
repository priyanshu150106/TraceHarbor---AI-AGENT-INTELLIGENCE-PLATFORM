"""
TraceHarbor API — Outbound Notification Service

Safe notification dispatcher with SSRF protection, HMAC signing, strict timeouts,
and error handling. Guarantees zero credential leakage in logs.
"""

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("traceharbor.notifications")


class NotificationDeliveryError(Exception):
    """Raised when notification delivery fails."""
    pass


class SSRFValidationError(Exception):
    """Raised when destination URL targets an unsafe private or loopback address."""
    pass


def validate_webhook_url(url: str) -> str:
    """
    Validate webhook URL against SSRF attacks.
    Rejects localhost, private IP subnets, link-local addresses, and cloud metadata IPs.
    """
    if not url:
        raise SSRFValidationError("Webhook URL cannot be empty.")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFValidationError(f"Invalid URL structure: {e}") from e

    if parsed.scheme not in ("http", "https"):
        raise SSRFValidationError(f"Unsupported scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL must include a valid hostname.")

    hostname_clean = hostname.strip().lower()

    # Reject localhost aliases
    if hostname_clean in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise SSRFValidationError("Delivery to localhost/loopback addresses is prohibited.")

    # Resolve hostname to IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname_clean, None)
    except socket.gaierror as e:
        # If DNS lookup fails during testing or hostname is unresolvable
        raise SSRFValidationError(f"Failed to resolve hostname '{hostname_clean}': {e}") from e

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Explicit check for AWS/GCP/Azure link-local metadata IP (169.254.169.254)
        if ip_str == "169.254.169.254":
            raise SSRFValidationError("Destination targets cloud instance metadata service.")

        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
        ):
            raise SSRFValidationError(
                f"Destination IP '{ip_str}' resolved for '{hostname_clean}' is in a private or restricted network range."
            )


    return url


class NotificationService:
    """Dispatches alert notifications to in-app stores or validated outbound webhooks."""

    @staticmethod
    async def dispatch_webhook(
        webhook_url: str,
        payload: dict[str, Any],
        webhook_secret: str | None = None,
        mock_mode: bool = False,
    ) -> tuple[str, str | None]:
        """
        Send signed HTTP POST to webhook URL.
        Returns tuple of (delivery_status: 'delivered' | 'failed', error_message: str | None).
        """
        # 1. SSRF Validation
        try:
            validate_webhook_url(webhook_url)
        except SSRFValidationError as e:
            return "failed", f"SSRF Protection blocked delivery: {str(e)}"

        # 2. Mock mode for unit tests
        if mock_mode:
            return "delivered", None

        # 3. Payload preparation and HMAC signature
        body_bytes = json.dumps(payload, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TraceHarbor-Alert-Notifier/1.0",
        }

        if webhook_secret:
            sig = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
            headers["X-TraceHarbor-Signature"] = f"sha256={sig}"

        # 4. Outbound dispatch with strict timeout
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(webhook_url, content=body_bytes, headers=headers)
                if res.status_code >= 400:
                    return "failed", f"Webhook endpoint returned HTTP {res.status_code}"
                return "delivered", None
        except httpx.TimeoutException:
            return "failed", "Webhook request timed out after 5.0 seconds"
        except Exception as e:
            # Mask any internal details
            return "failed", f"Webhook connection error: {type(e).__name__}"
