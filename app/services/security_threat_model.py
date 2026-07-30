import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.security_threat_model import (
    SecurityThreatBoundary,
    SecurityThreatCategory,
    SecurityThreatControl,
    SecurityThreatFinding,
    SecurityThreatModelArtifactResult,
    SecurityThreatModelDecision,
    SecurityThreatModelReport,
    SecurityThreatModelStatus,
    SecurityThreatRequirement,
    SecurityThreatScenario,
)


class SecurityThreatModelError(ValueError):
    pass


class SecurityThreatModelBlockedError(SecurityThreatModelError):
    pass


BOUNDARY_NAMES = (
    "public_repository",
    "local_demo_runtime",
    "local_sqlite_database",
    "admin_dashboard",
    "review_workspace",
    "lifecycle_local_mutations",
    "export_artifacts",
    "attachment_metadata",
    "webhook_ingress",
    "procore_api_boundary",
    "dmsa_credentials",
    "secret_provider_boundary",
    "storage_provider_boundary",
    "postgres_runtime_boundary",
    "hosted_deployment_boundary",
    "sandbox_evidence_boundary",
    "pilot_review_boundary",
    "generated_output_boundary",
)
REQUIRED_FILES = (
    ("safety_model", "docs/safety-model.md"),
    ("public_safety_audit", "scripts/audit_public_safety.py"),
    ("route_audit", "scripts/audit_routes_read_only.py"),
    ("secret_providers", "docs/secret-providers.md"),
    ("cloud_secret_providers", "docs/cloud-secret-providers.md"),
    ("storage_providers", "docs/storage-providers.md"),
    ("cloud_storage_providers", "docs/cloud-storage-providers.md"),
    ("postgres_runtime", "docs/postgres-runtime-operations.md"),
    ("webhook_planning", "docs/https-webhook-production-planning.md"),
    ("sandbox_read", "docs/sandbox-read-validation.md"),
    ("sandbox_evidence", "docs/sandbox-evidence-linkage.md"),
    ("hosted_deployment", "docs/hosted-deployment-templates.md"),
    ("hosted_pilot_dry_run", "docs/hosted-pilot-dry-run.md"),
    ("final_readiness", "docs/final-public-readiness.md"),
    ("release_readiness", "docs/release-readiness.md"),
    ("intake_review", "docs/intake-review-workspace.md"),
    ("lifecycle", "docs/intake-lifecycle-status-flow.md"),
    ("triage", "docs/operator-triage-queue.md"),
    ("attachment_review", "docs/attachment-review-manifest-ux.md"),
    ("export_pack", "docs/operator-export-pack.md"),
    ("product_dashboard", "docs/product-dashboard.md"),
    ("demo_walkthrough", "docs/demo-product-walkthrough.md"),
)
IGNORED_OUTPUTS = (
    "security-threat-model-output/",
    "threat-model-output/",
    "security-review-output/",
    "security-assessment-output/",
    "*.security-threat-model-report.json",
    "*.security-threat-model-report.md",
    "*.threat-model.md",
    "*.security-boundary-map.md",
    "*.security-review-checklist.md",
)
SAFE_ROOTS = {
    "security-threat-model-output",
    "threat-model-output",
    "security-review-output",
    "security-assessment-output",
}
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|sqlite)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\+?\d[\d(). -]{8,}\d")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:token|password|client_secret|"
    r"webhook_secret)\s*[:=]\s*(?!false\b)\S+)"
)
DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
LONG_ID = re.compile(r"\b(?:\d{12}|[0-9a-f]{8}-[0-9a-f-]{27,})\b", re.I)
CLOUD_ID = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
KEY_MATERIAL = re.compile(
    r"(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE REQUEST)|"
    r"_acme-challenge|registry\S+:\S+)"
)
PRIVATE_CONTENT = re.compile(
    r"(?i)(?:raw report contents?|deployment logs?|sql dumps?|backup contents?|"
    r"scanner output|raw_payload)"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:soc ?2|iso ?27001|hipaa|security certified|compliance certified|"
    r"production[- ]ready|launch approved|pilot approved|procore (?:endorsed|"
    r"partner|certified|officially supported))\b"
)
FORBIDDEN_KEYS = {
    "raw_payload",
    "source_url",
    "signed_url",
    "database_url",
    "storage_key",
    "private_path",
    "report_contents",
    "authorization",
}


def sanitize_security_threat_model_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
        )
    ):
        return "[redacted]"
    return text[:400]


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_security_threat_model_report_safe(
    report: BaseModel | dict[str, Any] | str,
) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    text = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
    keys = set(_walk_keys(payload)) if not isinstance(payload, str) else set()
    if keys & FORBIDDEN_KEYS or any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
            PRIVATE_CONTENT,
        )
    ):
        raise SecurityThreatModelBlockedError("Unsafe threat-model content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise SecurityThreatModelBlockedError("Unsafe security claim was blocked.")


def build_security_trust_boundaries(settings: Settings) -> list[SecurityThreatBoundary]:
    return [
        SecurityThreatBoundary(
            name=name,
            description=f"Public-safe boundary model for {name.replace('_', ' ')}.",
            private_review_required=name
            in {
                "procore_api_boundary",
                "dmsa_credentials",
                "secret_provider_boundary",
                "storage_provider_boundary",
                "postgres_runtime_boundary",
                "hosted_deployment_boundary",
                "sandbox_evidence_boundary",
                "pilot_review_boundary",
            },
        )
        for name in BOUNDARY_NAMES
    ]


def build_security_threat_scenarios(settings: Settings) -> list[SecurityThreatScenario]:
    boundaries = list(BOUNDARY_NAMES)
    return [
        SecurityThreatScenario(
            category=category,
            boundary=boundaries[index % len(boundaries)],
            threat=f"{category.value.replace('_', ' ').title()} may cross a trust boundary.",
            consequence="Public or private safety assumptions could be weakened.",
        )
        for index, category in enumerate(SecurityThreatCategory)
    ]


def build_security_controls(settings: Settings) -> list[SecurityThreatControl]:
    return [
        SecurityThreatControl(
            name=name,
            boundary=boundary,
            description=description,
            evidence_path=evidence,
        )
        for name, boundary, description, evidence in (
            (
                "public audit",
                "public_repository",
                "Tracked public content is scanned offline.",
                "scripts/audit_public_safety.py",
            ),
            (
                "route audit",
                "admin_dashboard",
                "Unexpected mutation and file routes are rejected.",
                "scripts/audit_routes_read_only.py",
            ),
            (
                "secret references",
                "secret_provider_boundary",
                "Providers expose references rather than values.",
                "docs/secret-providers.md",
            ),
            (
                "metadata-only review",
                "attachment_metadata",
                "Attachment files and private locations remain unavailable.",
                "docs/attachment-review-manifest-ux.md",
            ),
            (
                "ignored outputs",
                "generated_output_boundary",
                "Generated outputs remain outside version control.",
                ".gitignore",
            ),
            (
                "manual live gates",
                "procore_api_boundary",
                "Live operations remain separate and fail closed.",
                "docs/safety-model.md",
            ),
            (
                "local lifecycle",
                "lifecycle_local_mutations",
                "Lifecycle changes remain local and bounded.",
                "docs/intake-lifecycle-status-flow.md",
            ),
            (
                "private pilot boundary",
                "pilot_review_boundary",
                "Pilot evidence and decisions stay private.",
                "docs/hosted-pilot-dry-run.md",
            ),
        )
    ]


def build_security_threat_model_report(settings: Settings) -> SecurityThreatModelReport:
    if not settings.security_threat_model_enabled:
        raise SecurityThreatModelError("Security threat model is disabled.")
    unsafe = any(
        (
            not settings.security_threat_model_require_placeholders,
            settings.security_threat_model_allow_real_identities,
            settings.security_threat_model_allow_real_domains,
            settings.security_threat_model_allow_real_urls,
            settings.security_threat_model_allow_report_contents,
            settings.security_threat_model_allow_private_paths,
        )
    )
    if settings.security_threat_model_fail_closed and unsafe:
        raise SecurityThreatModelBlockedError("Unsafe threat-model settings were blocked.")
    root = Path.cwd()
    requirements = [
        SecurityThreatRequirement(name=name, path=path, present=(root / path).is_file())
        for name, path in REQUIRED_FILES
    ]
    gitignore = (
        (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    )
    missing_ignores = [pattern for pattern in IGNORED_OUTPUTS if pattern not in gitignore]
    findings = [
        SecurityThreatFinding(
            code="missing_public_evidence",
            message=f"Missing public threat-model evidence: {item.name}.",
            severity="warning",
        )
        for item in requirements
        if not item.present
    ]
    findings.extend(
        SecurityThreatFinding(
            code="missing_ignore_rule",
            message=f"Missing generated-output ignore rule: {pattern}.",
            severity="warning",
        )
        for pattern in missing_ignores
    )
    findings = findings[: settings.security_threat_model_max_findings]
    boundaries = build_security_trust_boundaries(settings)
    scenarios = build_security_threat_scenarios(settings)
    controls = build_security_controls(settings)
    report = SecurityThreatModelReport(
        status=SecurityThreatModelStatus.READY
        if not findings
        else SecurityThreatModelStatus.NEEDS_REVIEW,
        decision=(
            SecurityThreatModelDecision.READY_FOR_SECURITY_REVIEW
            if not findings
            else SecurityThreatModelDecision.NEEDS_REVIEW
        ),
        boundaries=boundaries,
        scenarios=scenarios,
        controls=controls,
        requirements=requirements,
        boundaries_total=len(boundaries),
        scenarios_total=len(scenarios),
        controls_total=len(controls),
        findings=findings,
        warnings=[finding.message for finding in findings],
        recommended_next_steps=[
            "Review the public boundary map.",
            "Resolve warnings without adding private values.",
            "Perform any environment-specific security review privately.",
            "Treat this model as review input, not certification or production authorization.",
        ],
    )
    validate_security_threat_model_report_safe(report)
    return report


def render_security_threat_model_markdown(report: SecurityThreatModelReport) -> str:
    lines = [
        "# Security Threat Model",
        "",
        f"Status: `{report.status.value}`",
        f"Decision: `{report.decision.value}`",
        "",
        "Offline public-safe review aid only. No live scanner or external call was attempted.",
        "",
        "## Threat scenarios",
        "",
    ]
    lines.extend(
        f"- **{item.category.value}** at `{item.boundary}`: {item.threat}"
        for item in report.scenarios
    )
    lines.extend(
        [
            "",
            "This model is not production authorization, security certification, "
            "or compliance certification.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_security_threat_model_report_safe(rendered)
    return rendered


def render_security_boundary_map(report: SecurityThreatModelReport) -> str:
    lines = ["# Security Boundary Map", ""]
    lines.extend(
        f"- `{item.name}` — {item.description} Private review required: "
        f"`{str(item.private_review_required).lower()}`"
        for item in report.boundaries
    )
    lines.append("")
    rendered = "\n".join(lines)
    validate_security_threat_model_report_safe(rendered)
    return rendered


def render_security_review_checklist(report: SecurityThreatModelReport) -> str:
    lines = [
        "# Security Review Checklist",
        "",
        "- [ ] Review every public trust boundary.",
        "- [ ] Confirm live operations remain separately gated.",
        "- [ ] Confirm generated and private outputs remain ignored.",
        "- [ ] Complete environment-specific review privately.",
        "- [ ] Confirm no certification or production authorization is claimed.",
        "",
    ]
    rendered = "\n".join(lines)
    validate_security_threat_model_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-security-threat-model-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise SecurityThreatModelBlockedError("Unsafe threat-model output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_ROOTS}:
        raise SecurityThreatModelBlockedError("Unapproved threat-model output root.")
    return root


def write_security_threat_model_artifacts(
    report: SecurityThreatModelReport, output_root: Path
) -> SecurityThreatModelArtifactResult:
    root = _safe_output_root(Path(output_root))
    artifacts = {
        "security-threat-model-report.json": report.model_dump_json(indent=2),
        "security-threat-model-report.md": render_security_threat_model_markdown(report),
        "security-boundary-map.md": render_security_boundary_map(report),
        "security-review-checklist.md": render_security_review_checklist(report),
    }
    manifest = json.dumps(
        {"files": sorted(artifacts), "live_operations": False, "sanitized": True},
        indent=2,
    )
    artifacts["manifest.json"] = manifest
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_security_threat_model_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return SecurityThreatModelArtifactResult(
        status=SecurityThreatModelStatus.READY,
        output_directory=root.name,
        files=sorted(artifacts),
    )
