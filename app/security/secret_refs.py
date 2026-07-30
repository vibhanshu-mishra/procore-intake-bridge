import re
from dataclasses import dataclass

from app.config import Settings

SECRET_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./:-]{1,254}$")
UNSAFE_REF = re.compile(
    r"(?i)(authorization|bearer|(?:sqlite|postgres(?:ql)?|mysql|mongodb)://|"
    r"https?://|[?&](?:signature|token|expires)=)"
)
AWS_ARN = re.compile(r"(?i)^arn:aws[a-z-]*:secretsmanager:")
AZURE_VAULT_URL = re.compile(r"(?i)^https://[a-z0-9-]+\.vault\.azure\.net/?")
GCP_RESOURCE_NAME = re.compile(r"(?i)^projects/[^/]+/secrets/[^/]+(?:/versions/[^/]+)?$")
UNSAFE_CLOUD_REF = re.compile(
    r"(?is)(BEGIN [A-Z ]*PRIVATE KEY|"
    r'"(?:private_key|private_key_id|client_email|client_id)"\s*:|'
    r"(?:aws_access_key_id|aws_secret_access_key)\s*=|"
    r"(?:credentials|application_default_credentials)\.(?:json|pem)|"
    r"(?:^|/)\.(?:aws|azure|config/gcloud)(?:/|$)|"
    r"^[A-F0-9-]{32,36}$|^\d{12}$)"
)
PLACEHOLDER_MARKERS = (
    "demo",
    "example",
    "fake",
    "missing",
    "placeholder",
    "synthetic",
    "test",
)


class SecretRefError(ValueError):
    """A secret reference was invalid; messages never echo the supplied value."""


@dataclass(frozen=True)
class SecretRef:
    name: str


def is_placeholder_secret_ref(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def parse_secret_ref(value: str) -> SecretRef:
    candidate = value.strip()
    if not SECRET_REF_PATTERN.fullmatch(candidate):
        raise SecretRefError("Secret reference has an invalid format.")
    if (
        candidate.casefold().startswith(("bearer", "sk-", "http://", "https://"))
        or UNSAFE_REF.search(candidate)
        or "=" in candidate
        or any(character.isspace() for character in candidate)
    ):
        raise SecretRefError("Secret reference resembles an inline value.")
    return SecretRef(name=candidate)


def validate_cloud_secret_ref(
    value: str,
    provider: str,
    *,
    allow_aws_arn: bool = False,
    allow_azure_vault_url: bool = False,
    allow_gcp_resource_name: bool = False,
) -> SecretRef:
    candidate = value.strip()
    if not candidate or UNSAFE_CLOUD_REF.search(candidate):
        raise SecretRefError("Cloud secret reference is unsafe.")
    if AWS_ARN.match(candidate) and not allow_aws_arn:
        raise SecretRefError("AWS resource identifiers are disabled.")
    if AZURE_VAULT_URL.match(candidate) and not allow_azure_vault_url:
        raise SecretRefError("Azure vault URLs are disabled.")
    if GCP_RESOURCE_NAME.match(candidate) and not allow_gcp_resource_name:
        raise SecretRefError("GCP resource names are disabled.")
    if provider == "aws_secrets_manager" and AWS_ARN.match(candidate):
        return SecretRef(name=candidate)
    if provider == "azure_key_vault" and AZURE_VAULT_URL.match(candidate):
        return SecretRef(name=candidate)
    if provider == "gcp_secret_manager" and GCP_RESOURCE_NAME.match(candidate):
        return SecretRef(name=candidate)
    return parse_secret_ref(candidate)


def validate_secret_ref(value: str, settings: Settings) -> SecretRef:
    parsed = parse_secret_ref(value)
    if (
        settings.secret_require_prefix
        and not parsed.name.startswith(settings.secret_ref_prefix)
        and not is_placeholder_secret_ref(parsed.name)
    ):
        raise SecretRefError("Secret reference is missing the configured prefix.")
    return parsed


def normalize_secret_ref(value: str, settings: Settings) -> SecretRef:
    parsed = validate_secret_ref(value, settings)
    if parsed.name.startswith(settings.secret_ref_prefix):
        return parsed
    normalized = re.sub(r"[^A-Z0-9]+", "_", parsed.name.upper()).strip("_")
    return SecretRef(name=f"{settings.secret_ref_prefix}{normalized}")


def mask_secret_ref(value: str, settings: Settings) -> str:
    try:
        name = normalize_secret_ref(value, settings).name
    except SecretRefError:
        return "[invalid-secret-ref]"
    visible = name[-4:] if len(name) > 4 else ""
    prefix = settings.secret_ref_prefix if name.startswith(settings.secret_ref_prefix) else ""
    hidden_length = max(len(name) - len(prefix) - len(visible), 8)
    return f"{prefix}{'*' * hidden_length}{visible}"
