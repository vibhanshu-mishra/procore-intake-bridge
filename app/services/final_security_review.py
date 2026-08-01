import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.final_security_review import (
    FinalSecurityArtifactResult,
    FinalSecurityDecision,
    FinalSecurityDomain,
    FinalSecurityDomainSummary,
    FinalSecurityFinding,
    FinalSecurityGap,
    FinalSecurityGate,
    FinalSecurityGateStatus,
    FinalSecurityReport,
    FinalSecurityReviewDependency,
    FinalSecurityReviewStatus,
)


class FinalSecurityReviewError(ValueError):
    pass


class FinalSecurityReviewBlockedError(FinalSecurityReviewError):
    pass


IGNORED_OUTPUTS = (
    "final-security-review-output/",
    "security-readiness-output/",
    "final-security-output/",
    "private-security-review-output/",
    "security-gate-output/",
    "*.final-security-review-report.json",
    "*.final-security-review-report.md",
    "*.security-readiness-summary.md",
    "*.security-gap-register.md",
    "*.private-security-review-checklist.md",
    "*.security-domain-matrix.csv",
)
SAFE_ROOTS = {value.rstrip("/") for value in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "final-security-review-report.json",
    "final-security-review-report.md",
    "security-readiness-summary.md",
    "security-gap-register.md",
    "private-security-review-checklist.md",
    "security-domain-matrix.csv",
    "manifest.json",
)

DEPENDENCIES = (
    ("I1 threat model guide", "docs/security-threat-model.md", FinalSecurityDomain.THREAT_MODEL),
    (
        "I2 auth boundary guide",
        "docs/auth-permission-boundary-audit.md",
        FinalSecurityDomain.AUTH_PERMISSION_BOUNDARY,
    ),
    (
        "I3 webhook security guide",
        "docs/webhook-replay-signature-hardening.md",
        FinalSecurityDomain.WEBHOOK_SECURITY,
    ),
    (
        "I4 data policy guide",
        "docs/data-retention-redaction-policy.md",
        FinalSecurityDomain.DATA_RETENTION_REDACTION,
    ),
    (
        "I5 infrastructure security guide",
        "docs/secrets-storage-db-security-review.md",
        FinalSecurityDomain.SECRETS_STORAGE_DATABASE,
    ),
    (
        "I6 supply-chain guide",
        "docs/dependency-supply-chain-security.md",
        FinalSecurityDomain.DEPENDENCY_SUPPLY_CHAIN,
    ),
    (
        "I7 incident response guide",
        "docs/incident-response-forensics.md",
        FinalSecurityDomain.INCIDENT_RESPONSE_FORENSICS,
    ),
    ("I1 review script", "scripts/run_security_threat_model.py", FinalSecurityDomain.THREAT_MODEL),
    (
        "I2 review script",
        "scripts/run_auth_boundary_audit.py",
        FinalSecurityDomain.AUTH_PERMISSION_BOUNDARY,
    ),
    (
        "I3 review script",
        "scripts/run_webhook_security_review.py",
        FinalSecurityDomain.WEBHOOK_SECURITY,
    ),
    (
        "I4 review script",
        "scripts/run_data_policy_review.py",
        FinalSecurityDomain.DATA_RETENTION_REDACTION,
    ),
    (
        "I5 review script",
        "scripts/run_infra_security_review.py",
        FinalSecurityDomain.SECRETS_STORAGE_DATABASE,
    ),
    (
        "I6 review script",
        "scripts/run_supply_chain_review.py",
        FinalSecurityDomain.DEPENDENCY_SUPPLY_CHAIN,
    ),
    (
        "I7 review script",
        "scripts/run_incident_response_review.py",
        FinalSecurityDomain.INCIDENT_RESPONSE_FORENSICS,
    ),
    ("I1 tests", "tests/test_security_threat_model_i1.py", FinalSecurityDomain.THREAT_MODEL),
    (
        "I2 tests",
        "tests/test_auth_boundary_audit_i2.py",
        FinalSecurityDomain.AUTH_PERMISSION_BOUNDARY,
    ),
    ("I3 tests", "tests/test_webhook_security_review_i3.py", FinalSecurityDomain.WEBHOOK_SECURITY),
    (
        "I4 tests",
        "tests/test_data_policy_review_i4.py",
        FinalSecurityDomain.DATA_RETENTION_REDACTION,
    ),
    (
        "I5 tests",
        "tests/test_infra_security_review_i5.py",
        FinalSecurityDomain.SECRETS_STORAGE_DATABASE,
    ),
    (
        "I6 tests",
        "tests/test_supply_chain_review_i6.py",
        FinalSecurityDomain.DEPENDENCY_SUPPLY_CHAIN,
    ),
    (
        "I7 tests",
        "tests/test_incident_response_review_i7.py",
        FinalSecurityDomain.INCIDENT_RESPONSE_FORENSICS,
    ),
    (
        "public safety audit",
        "scripts/audit_public_safety.py",
        FinalSecurityDomain.PUBLIC_REPO_SAFETY,
    ),
    ("route audit", "scripts/audit_routes_read_only.py", FinalSecurityDomain.ROUTE_BOUNDARY),
    ("docs-site checker", "scripts/check_docs_site.py", FinalSecurityDomain.PUBLIC_REPO_SAFETY),
    (
        "final readiness",
        "scripts/run_final_public_readiness_audit.py",
        FinalSecurityDomain.RELEASE_READINESS_BOUNDARY,
    ),
    (
        "release readiness",
        "scripts/check_release_readiness.py",
        FinalSecurityDomain.RELEASE_READINESS_BOUNDARY,
    ),
    ("safety model", "docs/safety-model.md", FinalSecurityDomain.PUBLIC_REPO_SAFETY),
    (
        "project status",
        "docs/project-status.md",
        FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY,
    ),
    ("roadmap", "docs/roadmap.md", FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY),
)

URL_PATTERN = re.compile(r"(?i)\b(?:https?|s3|gs|postgres|postgresql)://\S+")
EMAIL_PATTERN = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{8,}\d)(?!\w)")
DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|dev|cloud|app|co)\b"
)
LONG_ID_PATTERN = re.compile(r"(?<![\w.-])[A-Za-z0-9]{20,}(?![\w.-])")
PRIVATE_PATH_PATTERN = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET_PATTERN = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:github_token|registry_token|"
    r"publish_token|ci_secret|release_signing_key|admin_token|webhook_secret|"
    r"dmsa_(?:client_id|client_secret)|database_url|signed_url|presigned_url|"
    r"storage_key|object_key|cloud_(?:account_)?id)\s*[:=]\s*(?!false|none|placeholder)\S+)"
)
PRIVATE_MATERIAL_PATTERN = re.compile(
    r"(?i)(?:raw_log|raw_payload|live_webhook_(?:headers|payload)|packet_capture|"
    r"memory_dump|core_dump|forensic_image|legal_notice|regulator_notice|"
    r"law_enforcement_report|breach_notification_content|db_dump_content|"
    r"backup_archive_content|migration_log)\s*[:=]\s*(?!false|none|placeholder)\S+|"
    r"\b\S+\.(?:pcap|pcapng|har|dmp|core|img|raw)\b"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:production|pilot|release|deployment) approval (?:granted|complete)\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance|breach readiness) certified\b|"
    r"\b(?:gdpr|ccpa|hipaa|slsa|sbom) compliant\b|\bbreach notification completed\b|"
    r"\bprocore (?:endorsed|partner|certified)\b"
)
NEGATION_PATTERN = re.compile(
    r"(?i)\b(?:no|not|never|does not|is not|without|false|remain(?:s)? required|"
    r"remain(?:s)? outside|out of scope)\b"
)
FORBIDDEN_KEYS = {
    "authorization",
    "admin_token",
    "webhook_secret",
    "github_token",
    "registry_token",
    "publish_token",
    "ci_secret",
    "release_signing_key",
    "database_url",
    "source_url",
    "signed_url",
    "presigned_url",
    "storage_key",
    "object_key",
    "cloud_id",
    "private_path",
    "report_contents",
    "raw_log",
    "raw_payload",
    "live_webhook_headers",
    "live_webhook_payload",
    "packet_capture",
    "memory_dump",
    "core_dump",
    "forensic_image",
    "legal_notice",
    "legal_notice_content",
    "regulator_notice",
    "law_enforcement_report",
    "breach_notification_content",
    "db_dump_content",
    "backup_archive_content",
    "migration_log",
    "reviewer_name",
    "approver_name",
    "operator_name",
    "customer_name",
    "company_name",
    "real_domain",
    "cloud_account_id",
}


def sanitize_final_security_value(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        LONG_ID_PATTERN,
        PRIVATE_PATH_PATTERN,
        SECRET_PATTERN,
        PRIVATE_MATERIAL_PATTERN,
    )
    return "[redacted]" if any(pattern.search(text) for pattern in patterns) else text[:400]


def build_final_security_dependencies(settings: Settings) -> list[FinalSecurityReviewDependency]:
    del settings
    return [
        FinalSecurityReviewDependency(
            name=name,
            path=path,
            domain=domain,
            present=Path(path).is_file(),
        )
        for name, path, domain in DEPENDENCIES
    ]


def _generated_output_boundary_ready() -> bool:
    gitignore = Path(".gitignore")
    return gitignore.is_file() and all(
        pattern in gitignore.read_text() for pattern in IGNORED_OUTPUTS
    )


def build_final_security_domain_summaries(
    settings: Settings,
) -> list[FinalSecurityDomainSummary]:
    dependencies = build_final_security_dependencies(settings)
    by_domain = {
        domain: [dependency for dependency in dependencies if dependency.domain == domain]
        for domain in FinalSecurityDomain
    }
    summaries = []
    for domain in FinalSecurityDomain:
        domain_dependencies = by_domain[domain]
        present = bool(domain_dependencies) and all(item.present for item in domain_dependencies)
        if domain == FinalSecurityDomain.GENERATED_OUTPUT_BOUNDARY:
            present = _generated_output_boundary_ready()
        if domain == FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY:
            status = FinalSecurityGateStatus.NEEDS_REVIEW
            summary = "Authorized private security review remains required."
        elif not domain_dependencies and domain not in {
            FinalSecurityDomain.GENERATED_OUTPUT_BOUNDARY,
            FinalSecurityDomain.DEMO_MODE_BOUNDARY,
            FinalSecurityDomain.SANDBOX_PILOT_BOUNDARY,
        }:
            status = FinalSecurityGateStatus.MISSING
            summary = "Required local review evidence is missing."
        elif domain in {
            FinalSecurityDomain.DEMO_MODE_BOUNDARY,
            FinalSecurityDomain.SANDBOX_PILOT_BOUNDARY,
        }:
            status = FinalSecurityGateStatus.PASS
            summary = "Public documentation preserves this offline/private boundary."
        else:
            status = FinalSecurityGateStatus.PASS if present else FinalSecurityGateStatus.MISSING
            summary = (
                "Required local review evidence is present."
                if present
                else "Required local review evidence is missing."
            )
        summaries.append(
            FinalSecurityDomainSummary(
                domain=domain,
                status=status,
                summary=summary,
                private_review_required=(
                    domain == FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY
                ),
            )
        )
    return summaries


def build_final_security_gates(settings: Settings) -> list[FinalSecurityGate]:
    dependencies = build_final_security_dependencies(settings)
    summaries = build_final_security_domain_summaries(settings)
    return [
        FinalSecurityGate(
            name=f"{summary.domain.value}_gate",
            domain=summary.domain,
            status=summary.status,
            description=summary.summary,
            evidence_paths=[item.path for item in dependencies if item.domain == summary.domain],
        )
        for summary in summaries
    ]


def build_final_security_gap_register(settings: Settings) -> list[FinalSecurityGap]:
    gaps = [
        FinalSecurityGap(
            code="private_live_infrastructure_review",
            domain=FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY,
            description=(
                "Live infrastructure and provider permissions require authorized private review."
            ),
        ),
        FinalSecurityGap(
            code="private_credentials_and_customer_data_review",
            domain=FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY,
            description="Real credentials and customer data require authorized private review.",
        ),
        FinalSecurityGap(
            code="private_operational_and_legal_review",
            domain=FinalSecurityDomain.PRIVATE_SECURITY_REVIEW_BOUNDARY,
            description=(
                "Actual legal obligations, release process, incident contacts, evidence custody, "
                "and operational controls require authorized private review."
            ),
        ),
    ]
    for dependency in build_final_security_dependencies(settings):
        if not dependency.present:
            gaps.append(
                FinalSecurityGap(
                    code="missing_local_dependency",
                    domain=dependency.domain,
                    description=f"Missing required local review file: {dependency.path}.",
                    blocking=True,
                )
            )
    if not _generated_output_boundary_ready():
        gaps.append(
            FinalSecurityGap(
                code="missing_generated_output_ignore",
                domain=FinalSecurityDomain.GENERATED_OUTPUT_BOUNDARY,
                description="One or more generated final-security output patterns are not ignored.",
                blocking=True,
            )
        )
    return gaps


def _validate_policy(settings: Settings) -> None:
    required = (
        settings.final_security_review_require_placeholders,
        settings.final_security_review_require_i1_threat_model,
        settings.final_security_review_require_i2_auth_boundary,
        settings.final_security_review_require_i3_webhook_security,
        settings.final_security_review_require_i4_data_policy,
        settings.final_security_review_require_i5_infra_security,
        settings.final_security_review_require_i6_supply_chain,
        settings.final_security_review_require_i7_incident_response,
        settings.final_security_review_require_public_safety_audit,
        settings.final_security_review_require_route_audit,
        settings.final_security_review_require_private_review_gaps,
    )
    allowed = (
        settings.final_security_review_allow_real_identities,
        settings.final_security_review_allow_real_domains,
        settings.final_security_review_allow_real_urls,
        settings.final_security_review_allow_report_contents,
        settings.final_security_review_allow_private_paths,
    )
    if settings.final_security_review_fail_closed and (not all(required) or any(allowed)):
        raise FinalSecurityReviewBlockedError("Unsafe final-security review policy blocked.")


def build_final_security_review_report(settings: Settings) -> FinalSecurityReport:
    if not settings.final_security_review_enabled:
        raise FinalSecurityReviewError("Final-security review disabled.")
    _validate_policy(settings)
    summaries = build_final_security_domain_summaries(settings)
    dependencies = build_final_security_dependencies(settings)
    gates = build_final_security_gates(settings)
    gaps = build_final_security_gap_register(settings)
    blocking_gaps = [gap for gap in gaps if gap.blocking]
    findings = [
        FinalSecurityFinding(
            code=gap.code,
            domain=gap.domain,
            message=gap.description,
            severity="blocker" if gap.blocking else "warning",
        )
        for gap in gaps
    ]
    blocked = bool(blocking_gaps)
    status = (
        FinalSecurityReviewStatus.BLOCKED
        if blocked
        else FinalSecurityReviewStatus.NEEDS_PRIVATE_SECURITY_REVIEW
    )
    report = FinalSecurityReport(
        status=status,
        decision=(
            FinalSecurityDecision.BLOCKED if blocked else FinalSecurityDecision.NEEDS_PRIVATE_REVIEW
        ),
        domains_total=len(summaries),
        domains_passed=sum(item.status == FinalSecurityGateStatus.PASS for item in summaries),
        domains_needing_review=sum(
            item.status == FinalSecurityGateStatus.NEEDS_REVIEW for item in summaries
        ),
        domains_blocked=sum(
            item.status in {FinalSecurityGateStatus.BLOCKED, FinalSecurityGateStatus.MISSING}
            for item in summaries
        ),
        gates_total=len(gates),
        gates_passed=sum(item.status == FinalSecurityGateStatus.PASS for item in gates),
        gates_needing_review=sum(
            item.status == FinalSecurityGateStatus.NEEDS_REVIEW for item in gates
        ),
        gaps_total=len(gaps),
        public_repo_safe_for_maintainer_review=not blocked,
        findings=findings[: settings.final_security_review_max_findings],
        blockers=[gap.description for gap in blocking_gaps],
        warnings=[gap.description for gap in gaps if not gap.blocking],
        dependencies=dependencies,
        domain_summaries=summaries,
        gates=gates,
        gaps=gaps,
        recommended_next_steps=[
            (
                "Complete an authorized private review of live infrastructure, permissions, "
                "credentials, customer data, and operational controls."
            ),
            "Keep private security evidence and decisions outside the public repository.",
            (
                "Treat I8 as maintainer review input; it grants no production, pilot, release, "
                "legal, compliance, or certification approval."
            ),
        ],
    )
    validate_final_security_review_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)
    elif isinstance(value, str):
        yield value


def validate_final_security_review_report_safe(report: Any) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    if not isinstance(payload, str) and set(_walk_keys(payload)) & FORBIDDEN_KEYS:
        raise FinalSecurityReviewBlockedError("Unsafe final-security content blocked.")
    strings = [payload] if isinstance(payload, str) else list(_walk_strings(payload))
    unsafe_patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        LONG_ID_PATTERN,
        PRIVATE_PATH_PATTERN,
        SECRET_PATTERN,
        PRIVATE_MATERIAL_PATTERN,
    )
    for value in strings:
        if any(pattern.search(value) for pattern in unsafe_patterns):
            raise FinalSecurityReviewBlockedError("Unsafe final-security content blocked.")
        if UNSAFE_CLAIM_PATTERN.search(value) and not NEGATION_PATTERN.search(value):
            raise FinalSecurityReviewBlockedError("Unsafe final-security claim blocked.")


def render_final_security_review_markdown(report: FinalSecurityReport) -> str:
    text = "\n".join(
        [
            "# Final Security Readiness Review",
            "",
            f"Status: `{report.status.value}`",
            f"Decision: `{report.decision.value}`",
            "",
            (
                "This offline review aggregates I1 through I7 using local public-repository "
                "files only."
            ),
            "",
            *(f"- `{item.code}` — {item.message}" for item in report.findings),
            "",
            (
                "Private security review remains required. No production, pilot, release, "
                "deployment, legal, compliance, or certification approval is granted."
            ),
            (
                "No live operation, scanner, external call, Procore call, cloud call, database "
                "connection, notification, build, or package operation was attempted."
            ),
            "",
        ]
    )
    validate_final_security_review_report_safe(text)
    return text


def render_security_readiness_summary_markdown(report: FinalSecurityReport) -> str:
    text = "\n".join(
        [
            "# Security Readiness Summary",
            "",
            f"- Domains: {report.domains_total}",
            f"- Domains passed: {report.domains_passed}",
            f"- Domains needing review: {report.domains_needing_review}",
            f"- Gates passed: {report.gates_passed} of {report.gates_total}",
            "- Private security review remains required.",
            (
                "- No production, pilot, release, legal, compliance, or certification approval "
                "is granted."
            ),
            "",
        ]
    )
    validate_final_security_review_report_safe(text)
    return text


def render_security_gap_register_markdown(report: FinalSecurityReport) -> str:
    text = "\n".join(
        [
            "# Security Gap Register",
            "",
            "Public-safe descriptions only; private evidence remains outside this repository.",
            "",
            *(f"- `{gap.code}` (`{gap.domain.value}`) — {gap.description}" for gap in report.gaps),
            "",
        ]
    )
    validate_final_security_review_report_safe(text)
    return text


def render_private_security_review_checklist_markdown(report: FinalSecurityReport) -> str:
    del report
    text = "\n".join(
        [
            "# Private Security Review Checklist",
            "",
            "Complete these items only in an authorized private workspace:",
            "",
            "- Review live infrastructure and provider permissions.",
            "- Review real credentials and customer-data handling.",
            "- Review actual legal obligations and release process.",
            "- Review incident contacts, evidence custody, and operational controls.",
            "",
            "No approval or certification is granted by this checklist.",
            "",
        ]
    )
    validate_final_security_review_report_safe(text)
    return text


def _csv_cell(value: Any) -> str:
    text = sanitize_final_security_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_security_domain_matrix_csv(report: FinalSecurityReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("domain", "status", "summary", "private_review_required"))
    for summary in report.domain_summaries:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    summary.domain.value,
                    summary.status.value,
                    summary.summary,
                    str(summary.private_review_required).lower(),
                )
            )
        )
    text = output.getvalue()
    validate_final_security_review_report_safe(text)
    return text


def _safe_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-final-security-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if (
        ".." in root.parts
        or (root.is_absolute() and not temporary)
        or (not temporary and root.parts[:1] not in {(value,) for value in SAFE_ROOTS})
    ):
        raise FinalSecurityReviewBlockedError("Unsafe output root.")
    return root


def write_final_security_review_artifacts(
    report: FinalSecurityReport, output_root: str | Path
) -> FinalSecurityArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "final-security-review-report.json": report.model_dump_json(indent=2),
        "final-security-review-report.md": render_final_security_review_markdown(report),
        "security-readiness-summary.md": render_security_readiness_summary_markdown(report),
        "security-gap-register.md": render_security_gap_register_markdown(report),
        "private-security-review-checklist.md": render_private_security_review_checklist_markdown(
            report
        ),
        "security-domain-matrix.csv": render_security_domain_matrix_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {
            "files": sorted(artifacts),
            "sanitized": True,
            "live_operations": False,
            "external_operations": False,
            "approval_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in artifacts.items():
        validate_final_security_review_report_safe(content)
        (root / filename).write_text(content)
    return FinalSecurityArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=sorted(artifacts),
    )
