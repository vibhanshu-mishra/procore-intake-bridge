import hmac
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.security.secret_provider_factory import build_secret_provider
from app.security.secret_refs import mask_secret_ref
from app.security.secrets import SecretProvider, SecretProviderError

ADMIN_TOKEN_HEADER = "x-procore-intake-admin-token"
ADMIN_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


class AdminAccessError(PermissionError):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class AdminAuthDisabledError(AdminAccessError):
    def __init__(self):
        super().__init__("Admin access is disabled.", 404)


class AdminAuthRequiredError(AdminAccessError):
    def __init__(self):
        super().__init__("Admin token is required.", 401)


class AdminAuthInvalidError(AdminAccessError):
    def __init__(self):
        super().__init__("Admin token is invalid.", 403)


class AdminAuthMisconfiguredError(AdminAccessError):
    def __init__(self):
        super().__init__("Admin authentication is unavailable or misconfigured.", 503)


class AdminAuthResult(BaseModel):
    authenticated: bool
    mode: str
    token_used: bool


class AdminAuthConfigSummary(BaseModel):
    mode: str
    token_required: bool
    token_header_name: str
    primary_token_ref_configured: bool
    rotation_token_ref_configured: bool
    provider_health_status: str
    deployment_routes_protected: bool
    fail_closed: bool
    cache_seconds: int


def effective_admin_auth_mode(settings: Settings) -> str:
    if not settings.admin_dashboard_enabled or settings.admin_auth_mode == "disabled":
        return "disabled"
    if settings.admin_auth_mode == "token_required" or settings.admin_require_token:
        return "token_required"
    if settings.admin_auth_mode == "local_optional":
        return "local_optional"
    return "invalid"


def primary_admin_ref(settings: Settings) -> str:
    return settings.admin_token_secret_ref or settings.admin_token_secret_name


def rotation_admin_ref(settings: Settings) -> str:
    return settings.admin_token_rotation_secret_ref


def compare_admin_token(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate.encode(), expected.encode())


def mask_admin_ref(ref: str, settings: Settings | None = None) -> str:
    return mask_secret_ref(ref, settings or get_settings())


def sanitize_admin_auth_error(error: AdminAccessError) -> str:
    return str(error)


def _provider_health_status(settings: Settings, refs: list[str]) -> str:
    try:
        provider = build_secret_provider(settings)
        return provider.health_check(refs).status
    except SecretProviderError:
        return "unavailable"


def get_admin_auth_config_summary(settings: Settings) -> AdminAuthConfigSummary:
    mode = effective_admin_auth_mode(settings)
    refs = [ref for ref in (primary_admin_ref(settings), rotation_admin_ref(settings)) if ref]
    return AdminAuthConfigSummary(
        mode=mode,
        token_required=mode == "token_required",
        token_header_name=settings.admin_token_header,
        primary_token_ref_configured=bool(primary_admin_ref(settings)),
        rotation_token_ref_configured=bool(rotation_admin_ref(settings)),
        provider_health_status=_provider_health_status(settings, refs),
        deployment_routes_protected=settings.admin_auth_protect_deployment_routes,
        fail_closed=settings.admin_auth_fail_closed,
        cache_seconds=settings.admin_auth_cache_seconds,
    )


def _get_request_header(request: Request, header_name: str) -> str | None:
    value = request.headers.get(header_name)
    if value is not None:
        return value
    target = header_name.casefold()
    return next(
        (
            candidate
            for name, candidate in request.headers.items()
            if str(name).casefold() == target
        ),
        None,
    )


def require_admin_access(
    request: Request,
    settings: Settings,
    secret_provider: SecretProvider,
) -> AdminAuthResult:
    mode = effective_admin_auth_mode(settings)
    if mode == "disabled":
        raise AdminAuthDisabledError()
    if mode == "local_optional":
        if settings.environment == "local":
            return AdminAuthResult(
                authenticated=True, mode=mode, token_used=False
            )
        if settings.admin_auth_fail_closed:
            raise AdminAuthMisconfiguredError()
        return AdminAuthResult(authenticated=True, mode=mode, token_used=False)
    if mode != "token_required":
        raise AdminAuthMisconfiguredError()
    candidate = _get_request_header(request, settings.admin_token_header)
    if not candidate:
        raise AdminAuthRequiredError()
    primary_ref = primary_admin_ref(settings)
    if not primary_ref:
        raise AdminAuthMisconfiguredError()
    refs = [primary_ref]
    if rotation_ref := rotation_admin_ref(settings):
        refs.append(rotation_ref)
    try:
        expected_values = [secret_provider.get_secret(ref) for ref in refs]
    except SecretProviderError as exc:
        raise AdminAuthMisconfiguredError() from exc
    matches = [
        compare_admin_token(candidate, expected) for expected in expected_values
    ]
    if not any(matches):
        raise AdminAuthInvalidError()
    return AdminAuthResult(authenticated=True, mode=mode, token_used=True)


def add_admin_security_headers(response: Response) -> None:
    for name, value in ADMIN_SECURITY_HEADERS.items():
        response.headers[name] = value


def require_admin_access_dependency(
    request: Request, response: Response
) -> AdminAuthResult:
    settings = get_settings()
    try:
        result = require_admin_access(
            request, settings, build_secret_provider(settings)
        )
    except AdminAccessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=sanitize_admin_auth_error(exc),
            headers=ADMIN_SECURITY_HEADERS,
        ) from exc
    add_admin_security_headers(response)
    return result


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
