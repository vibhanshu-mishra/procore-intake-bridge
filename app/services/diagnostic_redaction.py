import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEY_TERMS = (
    "authorization",
    "client_id",
    "client_secret",
    "credential",
    "database_url",
    "db_url",
    "password",
    "payload",
    "secret",
    "signature",
    "signed_url",
    "source_url",
    "token",
)

PATTERNS = {
    "authorization": re.compile(r"(?i)\bauthorization\s*[:=]\s*[^\s,;}]+(?:\s+[^\s,;}]+)?"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{4,}"),
    "secret_assignment": re.compile(
        r"(?i)\b[\w-]*(?:secret|token|password|credential|app[_ ]?version[_ ]?key)"
        r"\s*[:=]\s*[^\s,;}]+"
    ),
    "database_url": re.compile(
        r"(?i)\b(?:postgresql|postgres|mysql|mariadb|sqlite)(?:\+\w+)?://[^\s\"']+"
    ),
    "signed_url": re.compile(
        r"(?i)https?://[^\s\"']+[?&](?:signature|signed|token|expires)=[^\s\"']+"
    ),
    "cloud_url": re.compile(
        r"(?i)https?://[^\s\"']*(?:amazonaws|blob\.core|storage\.googleapis)[^\s\"']*"
    ),
    "absolute_path": re.compile(
        r"(?<![\w.-])(?:/Users/|/home/|/private/|/tmp/|/var/folders/)"
        r"[^\s\"'<>]*|[A-Za-z]:\\[^\s\"'<>]+"
    ),
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
    "env_assignment": re.compile(
        r"(?m)^(?:export\s+)?[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|KEY)"
        r"[A-Z0-9_]*\s*=\s*\S+"
    ),
    "support_output": re.compile(
        r"(?i)(?:customer-output|support-output|diagnostics-output)/[^\s\"']+"
    ),
}


class DiagnosticRedactionError(ValueError):
    """Diagnostics contain material that cannot be safely returned or written."""


def detect_sensitive_patterns(text: str) -> list[str]:
    if REDACTED in text and text.strip() == REDACTED:
        return []
    return sorted(name for name, pattern in PATTERNS.items() if pattern.search(text))


def redact_text(text: str) -> str:
    redacted = text
    for pattern in PATTERNS.values():
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def _key_sensitive(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    if normalized in {"values_exposed", "environment_values_included"} or normalized.endswith(
        ("_included", "_required", "_configured", "_provider_kind", "_health_checks")
    ):
        return False
    return any(term in normalized for term in SENSITIVE_KEY_TERMS)


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in mapping.items():
        text_key = str(key)
        normalized = text_key.casefold().replace("-", "_")
        if _key_sensitive(text_key):
            result[text_key] = REDACTED
        elif normalized in {"raw_record", "raw_records", "file_contents", "environment_values"}:
            result[text_key] = REDACTED
        elif normalized.endswith(("_company_id", "_project_id", "_procore_id")):
            result[text_key] = REDACTED
        else:
            result[text_key] = redact_diagnostic_value(value)
    return result


def redact_diagnostic_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return [redact_diagnostic_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        return redact_text(value)
    return value


def contains_sensitive_material(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            safe_value = item == REDACTED or item is False or item is None or item == ""
            if _key_sensitive(str(key)) and not safe_value:
                return True
            if contains_sensitive_material(item):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(contains_sensitive_material(item) for item in value)
    if isinstance(value, Path):
        return value.is_absolute()
    if isinstance(value, str):
        return bool(detect_sensitive_patterns(value))
    return False


def assert_diagnostics_safe(value: Any) -> None:
    if contains_sensitive_material(value):
        raise DiagnosticRedactionError(
            "Diagnostics safety validation found sensitive material; values were suppressed."
        )


def summarize_redaction(original: Any, redacted: Any) -> dict[str, Any]:
    original_text = json.dumps(original, default=str, sort_keys=True)
    redacted_text = json.dumps(redacted, default=str, sort_keys=True)
    return {
        "changed": original_text != redacted_text,
        "redacted_count": redacted_text.count(REDACTED),
        "safe": not contains_sensitive_material(redacted),
        "patterns_detected": detect_sensitive_patterns(original_text),
    }
