import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass

from app.config import Settings
from app.security.secret_provider import SecretNotFoundError, SecretProvider


class WebhookSignatureError(ValueError):
    """Signature verification failed without exposing signature or secret values."""


@dataclass(frozen=True)
class WebhookSignatureResult:
    status: str
    verified: bool
    message: str


def verify_webhook_signature(
    payload_bytes: bytes,
    headers: Mapping[str, str],
    secret_provider: SecretProvider,
    settings: Settings,
) -> WebhookSignatureResult:
    if not settings.require_webhook_signature:
        status = "skipped" if settings.webhook_secret_name else "not_configured"
        return WebhookSignatureResult(
            status=status,
            verified=False,
            message="Webhook signature verification is not required in this runtime.",
        )
    if not settings.webhook_secret_name.strip():
        raise WebhookSignatureError(
            "Webhook signatures are required but no secret reference is configured."
        )

    signature = _get_header(headers, settings.webhook_signature_header)
    if not signature:
        raise WebhookSignatureError("Required webhook signature header is missing.")
    try:
        secret = secret_provider.get_secret(settings.webhook_secret_name)
    except SecretNotFoundError as exc:
        raise WebhookSignatureError(
            "Required webhook signature secret could not be resolved."
        ) from exc

    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    supplied = signature.strip()
    if supplied.casefold().startswith("sha256="):
        supplied = supplied.split("=", 1)[1]
    if not hmac.compare_digest(expected, supplied):
        raise WebhookSignatureError("Webhook signature is invalid.")
    return WebhookSignatureResult(
        status="valid",
        verified=True,
        message="Webhook signature is valid.",
    )


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    target = name.casefold()
    return next(
        (value for key, value in headers.items() if key.casefold() == target),
        None,
    )
