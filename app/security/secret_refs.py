import re
from dataclasses import dataclass

from app.config import Settings

SECRET_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./:-]{1,254}$")
UNSAFE_REF = re.compile(
    r"(?i)(authorization|bearer|(?:sqlite|postgres(?:ql)?|mysql|mongodb)://|"
    r"https?://|[?&](?:signature|token|expires)=)"
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
