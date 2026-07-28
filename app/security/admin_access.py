import hmac
from pathlib import Path
from typing import Any

from app.config import Settings
from app.security.secret_provider import SecretNotFoundError, SecretProvider

ADMIN_TOKEN_HEADER = "x-procore-intake-admin-token"


class AdminAccessError(PermissionError):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def require_admin_access(
    request,
    settings: Settings,
    secret_provider: SecretProvider,
) -> None:
    if not settings.admin_dashboard_enabled:
        raise AdminAccessError("Admin dashboard is disabled.", 404)
    if not settings.admin_require_token:
        return
    if not settings.admin_token_secret_name.strip():
        raise AdminAccessError(
            "Admin token protection is required but not configured.",
            503,
        )
    try:
        expected = secret_provider.get_secret(settings.admin_token_secret_name)
    except SecretNotFoundError as exc:
        raise AdminAccessError(
            "Admin token protection is required but unavailable.",
            503,
        ) from exc
    supplied = request.headers.get(ADMIN_TOKEN_HEADER)
    if not supplied:
        raise AdminAccessError("Admin token is required.", 401)
    if not hmac.compare_digest(expected, supplied):
        raise AdminAccessError("Admin token is invalid.", 403)


def mask_identifier(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:3]}***{text[-3:]}"


def redact_admin_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if any(
                    marker in str(key).casefold()
                    for marker in (
                        "secret",
                        "token",
                        "authorization",
                        "signature",
                        "payload",
                        "url",
                    )
                )
                else redact_admin_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_admin_value(item) for item in value]
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            return "[REDACTED_URL]"
        if Path(value).is_absolute():
            return "[REDACTED_PATH]"
    return value
