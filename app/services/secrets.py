from app.config import Settings
from app.schemas.secrets import (
    SecretProviderFinding,
    SecretProviderHealth,
    SecretProviderInventoryItem,
    SecretProviderKind,
    SecretProviderReadiness,
    SecretRefStatus,
)
from app.security.secret_provider_factory import build_secret_provider as _build_provider
from app.security.secret_refs import (
    SecretRefError,
)
from app.security.secret_refs import (
    mask_secret_ref as _mask_secret_ref,
)
from app.security.secret_refs import (
    normalize_secret_ref as _normalize_secret_ref,
)
from app.security.secret_refs import (
    validate_secret_ref as _validate_secret_ref,
)
from app.security.secrets import (
    DisabledSecretProvider,
    EnvSecretProvider,
    ExternalPlaceholderSecretProvider,
    FileSecretProvider,
    SecretProviderBlockedError,
    SecretProviderConfigError,
    SecretProviderError,
    SecretProviderResolutionError,
)
from app.services.secret_inventory import (
    collect_required_secret_refs as _collect_required_secret_refs,
)


def normalize_secret_ref(ref: str, settings: Settings | None = None) -> str:
    configured = settings or Settings(_env_file=None)
    return _normalize_secret_ref(ref, configured).name


def mask_secret_ref(ref: str, settings: Settings | None = None) -> str:
    return _mask_secret_ref(ref, settings or Settings(_env_file=None))


def validate_secret_ref(ref: str, settings: Settings | None = None) -> str:
    return _validate_secret_ref(ref, settings or Settings(_env_file=None)).name


def assert_secret_value_never_reported(value: str) -> None:
    if value:
        raise SecretProviderBlockedError(
            "Secret values cannot be included in public or diagnostic output."
        )


def build_secret_provider(kind: str, settings: Settings):
    configured = settings.model_copy(update={"secret_provider": kind})
    return _build_provider(configured)


def _configured_refs(settings: Settings) -> list[str]:
    return [
        ref
        for ref in (
            settings.admin_token_secret_name,
            settings.admin_token_rotation_secret_ref,
            settings.webhook_secret_name,
        )
        if ref
    ]


def build_secret_provider_health(settings: Settings) -> SecretProviderHealth:
    refs = _configured_refs(settings)
    provider = _build_provider(settings)
    raw = provider.health_check(refs)
    kind = SecretProviderKind(settings.secret_provider)
    dependency_missing = raw.status == "dependency_missing"
    items = [
        SecretProviderInventoryItem(
            purpose="configured secret reference",
            masked_ref=item.masked_ref,
            status=SecretRefStatus(item.status),
        )
        for item in raw.refs
    ]
    return SecretProviderHealth(
        provider=kind,
        status=raw.status,
        configured=settings.secret_provider != "disabled",
        available=raw.status in {"healthy", "degraded"},
        dependency_missing=dependency_missing,
        permission_unknown=kind
        in {
            SecretProviderKind.AWS_SECRETS_MANAGER,
            SecretProviderKind.AZURE_KEY_VAULT,
            SecretProviderKind.GCP_SECRET_MANAGER,
        },
        resolution_not_attempted=not bool(refs),
        checked_refs_count=raw.checked_refs_count,
        present_refs_count=raw.present_refs_count,
        missing_refs_count=raw.missing_refs_count,
        refs=items,
    )


def build_secret_provider_readiness(settings: Settings) -> SecretProviderReadiness:
    try:
        health = build_secret_provider_health(settings)
        findings = [
            SecretProviderFinding(
                code="provider_posture",
                severity="info" if health.available else "warning",
                message=(
                    "Secret provider is available; values remain private."
                    if health.available
                    else "Secret provider is unavailable, disabled, or needs private configuration."
                ),
            )
        ]
        ready = health.available and health.missing_refs_count == 0
    except SecretProviderError:
        kind = SecretProviderKind(settings.secret_provider)
        health = SecretProviderHealth(
            provider=kind,
            status="unavailable",
            configured=True,
            available=False,
        )
        findings = [
            SecretProviderFinding(
                code="provider_error",
                severity="blocking",
                message="Secret provider configuration failed closed; details were suppressed.",
            )
        ]
        ready = False
    return SecretProviderReadiness(
        provider=health.provider,
        ready=ready,
        health=health,
        findings=findings,
    )


def collect_required_secret_refs(settings: Settings, db_session=None):
    return _collect_required_secret_refs(settings, db_session=db_session, run_health=False)


def validate_required_secret_refs(settings: Settings, db_session=None):
    return _collect_required_secret_refs(settings, db_session=db_session, run_health=True)


__all__ = [
    "DisabledSecretProvider",
    "EnvSecretProvider",
    "ExternalPlaceholderSecretProvider",
    "FileSecretProvider",
    "SecretProviderBlockedError",
    "SecretProviderConfigError",
    "SecretProviderError",
    "SecretProviderResolutionError",
    "SecretRefError",
    "assert_secret_value_never_reported",
    "build_secret_provider",
    "build_secret_provider_health",
    "build_secret_provider_readiness",
    "collect_required_secret_refs",
    "mask_secret_ref",
    "normalize_secret_ref",
    "validate_required_secret_refs",
    "validate_secret_ref",
]
