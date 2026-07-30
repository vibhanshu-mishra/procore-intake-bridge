from app.config import Settings
from app.schemas.secrets import (
    CloudSecretProviderFinding,
    CloudSecretProviderHealth,
    CloudSecretProviderKind,
    CloudSecretProviderStatus,
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
    AwsSecretsManagerProvider,
    AzureKeyVaultSecretProvider,
    DisabledSecretProvider,
    EnvSecretProvider,
    ExternalPlaceholderSecretProvider,
    FileSecretProvider,
    GcpSecretManagerProvider,
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


_CLOUD_PROVIDERS = {
    CloudSecretProviderKind.AWS_SECRETS_MANAGER: AwsSecretsManagerProvider,
    CloudSecretProviderKind.AZURE_KEY_VAULT: AzureKeyVaultSecretProvider,
    CloudSecretProviderKind.GCP_SECRET_MANAGER: GcpSecretManagerProvider,
}


def build_cloud_secret_provider_health(
    kind: CloudSecretProviderKind | str,
    settings: Settings,
) -> CloudSecretProviderHealth:
    provider_kind = CloudSecretProviderKind(kind)
    provider = _CLOUD_PROVIDERS[provider_kind](settings)
    enabled = provider._enabled()
    dependency_available = provider._dependency_present()
    configured = provider._config_ready()
    confirmation_present = provider._confirmation_present()
    resolution_allowed = bool(
        enabled
        and dependency_available
        and configured
        and settings.secret_provider_cloud_network_enabled
        and confirmation_present
    )
    findings: list[CloudSecretProviderFinding] = []
    next_steps: list[str] = []
    if not enabled:
        status = CloudSecretProviderStatus.DISABLED
        findings.append(
            CloudSecretProviderFinding(
                code="provider_disabled",
                severity="info",
                message="Cloud provider is disabled by default.",
            )
        )
        next_steps.append("Keep disabled unless an operator selects this provider.")
    elif not dependency_available:
        status = CloudSecretProviderStatus.DEPENDENCY_MISSING
        findings.append(
            CloudSecretProviderFinding(
                code="dependency_missing",
                severity="warning",
                message="Optional provider dependency is not installed.",
            )
        )
        next_steps.append("Install the matching optional dependency in the private runtime.")
    elif not configured:
        status = CloudSecretProviderStatus.NEEDS_CONFIGURATION
        findings.append(
            CloudSecretProviderFinding(
                code="needs_configuration",
                severity="warning",
                message="Required private configuration references are unresolved.",
            )
        )
        next_steps.append("Configure private environment references; do not paste their values.")
    elif not resolution_allowed:
        status = CloudSecretProviderStatus.BLOCKED
        findings.append(
            CloudSecretProviderFinding(
                code="resolution_gated",
                severity="info",
                message="Resolution remains blocked by network and confirmation gates.",
            )
        )
        next_steps.append("Use env or file first; cloud resolution requires deliberate enablement.")
    else:
        status = CloudSecretProviderStatus.READY_FOR_RESOLUTION
        findings.append(
            CloudSecretProviderFinding(
                code="resolution_ready",
                severity="info",
                message="Configuration gates permit resolution; no resolution was attempted.",
            )
        )
    return CloudSecretProviderHealth(
        provider=provider_kind,
        status=status,
        enabled=enabled,
        dependency_available=dependency_available,
        dependency_missing=not dependency_available,
        cloud_network_enabled=settings.secret_provider_cloud_network_enabled,
        cloud_confirmation_present=confirmation_present,
        configured=configured,
        resolution_allowed=resolution_allowed,
        findings=findings,
        recommended_next_steps=next_steps,
    )


def build_all_cloud_secret_provider_health(
    settings: Settings,
) -> list[CloudSecretProviderHealth]:
    return [
        build_cloud_secret_provider_health(kind, settings)
        for kind in CloudSecretProviderKind
    ]


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
    "build_cloud_secret_provider_health",
    "build_all_cloud_secret_provider_health",
    "collect_required_secret_refs",
    "mask_secret_ref",
    "normalize_secret_ref",
    "validate_required_secret_refs",
    "validate_secret_ref",
]
