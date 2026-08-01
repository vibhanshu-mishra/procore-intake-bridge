import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.security_gap_closeout import (
    EncryptionGuidanceItem,
    ImplementationLevel,
    KnownLimitationItem,
    PolicyImplementationMatrixItem,
    PrivacyTemplateSection,
    PrivateSecurityActionItem,
    SecurityGapCloseoutArtifactResult,
    SecurityGapCloseoutDecision,
    SecurityGapCloseoutReport,
    SecurityGapCloseoutStatus,
    SecurityGapControl,
    SecurityGapDomain,
    SecurityGapFinding,
    SecurityGapItem,
)


class SecurityGapCloseoutError(ValueError):
    pass


class SecurityGapCloseoutBlockedError(SecurityGapCloseoutError):
    pass


IGNORED_OUTPUTS = (
    "security-gap-closeout-output/",
    "security-closeout-output/",
    "privacy-review-output/",
    "encryption-guidance-output/",
    "private-security-action-output/",
    "*.security-gap-closeout-report.json",
    "*.security-gap-closeout-report.md",
    "*.privacy-review-template.md",
    "*.encryption-at-rest-guidance.md",
    "*.policy-implementation-matrix.csv",
    "*.private-security-action-register.md",
    "*.known-limitations-closeout.md",
)
SAFE_ROOTS = {value.rstrip("/") for value in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "security-gap-closeout-report.json",
    "security-gap-closeout-report.md",
    "privacy-review-template.md",
    "encryption-at-rest-guidance.md",
    "private-security-action-register.md",
    "known-limitations-closeout.md",
    "policy-implementation-matrix.csv",
    "manifest.json",
)

LOCAL_CONTROLS = (
    ("I1 threat model", "docs/security-threat-model.md", SecurityGapDomain.PRODUCT_LIMITATIONS),
    (
        "I2 auth boundary audit",
        "docs/auth-permission-boundary-audit.md",
        SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY,
    ),
    (
        "I3 webhook security review",
        "docs/webhook-replay-signature-hardening.md",
        SecurityGapDomain.PRODUCT_LIMITATIONS,
    ),
    (
        "I4 retention and redaction policy",
        "docs/data-retention-redaction-policy.md",
        SecurityGapDomain.RETENTION_POLICY_VS_ENFORCEMENT,
    ),
    (
        "I5 secrets storage and database review",
        "docs/secrets-storage-db-security-review.md",
        SecurityGapDomain.ENCRYPTION_AT_REST_GUIDANCE,
    ),
    (
        "I6 supply chain review",
        "docs/dependency-supply-chain-security.md",
        SecurityGapDomain.RELEASE_SECURITY_PRIVATE_REVIEW,
    ),
    (
        "I7 incident response review",
        "docs/incident-response-forensics.md",
        SecurityGapDomain.INCIDENT_RESPONSE_PRIVATE_GAPS,
    ),
    (
        "I8 final security readiness review",
        "docs/final-security-readiness-review.md",
        SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY,
    ),
    (
        "I8 final security readiness script",
        "scripts/run_final_security_review.py",
        SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY,
    ),
    (
        "H4 lifecycle local event history",
        "docs/intake-lifecycle-status-flow.md",
        SecurityGapDomain.AUDIT_LOGGING_POLICY_VS_IMPLEMENTATION,
    ),
    (
        "H7 export pack guidance",
        "docs/operator-export-pack.md",
        SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW,
    ),
    (
        "B8 operator diagnostics guide",
        "docs/operator-diagnostics.md",
        SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW,
    ),
    (
        "B8 operator diagnostics script",
        "scripts/print_operator_diagnostics.py",
        SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW,
    ),
    (
        "B8 operator diagnostics tests",
        "tests/test_operator_diagnostics_b8.py",
        SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW,
    ),
    (
        "public safety audit",
        "scripts/audit_public_safety.py",
        SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY,
    ),
    (
        "final readiness review",
        "scripts/run_final_public_readiness_audit.py",
        SecurityGapDomain.RELEASE_SECURITY_PRIVATE_REVIEW,
    ),
    (
        "release readiness review",
        "scripts/check_release_readiness.py",
        SecurityGapDomain.RELEASE_SECURITY_PRIVATE_REVIEW,
    ),
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
    r"storage_key|object_key|cloud_(?:account_)?id)\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+)"
)
PRIVATE_MATERIAL_PATTERN = re.compile(
    r"(?i)(?:raw_log|raw_payload|live_webhook_(?:headers|payload)|packet_capture|"
    r"memory_dump|core_dump|forensic_image|legal_notice(?:_content)?|"
    r"regulator_notice(?:_content)?|law_enforcement_report(?:_content)?|"
    r"breach_notification_content|db_dump_content|"
    r"backup_archive_content|migration_log|private_report_contents)\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+|\b\S+\.(?:pcap|pcapng|har|dmp|core|img|raw)\b"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:production|pilot|release|deployment) approval (?:granted|complete)\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance|breach readiness) certified\b|"
    r"\b(?:gdpr|ccpa|hipaa|slsa|sbom|privacy|legally) compliant\b|"
    r"\b(?:privacy|legal) compliance (?:achieved|complete|confirmed)\b|"
    r"\bbreach notification completed\b|\bprocore (?:endorsed|partner|certified)\b|"
    r"\bencryption at rest (?:is )?implemented(?: by (?:the )?app)?\b|"
    r"\bretention enforcement (?:is )?implemented\b"
)
NEGATION_PATTERN = re.compile(
    r"(?i)\b(?:no|not|never|does not|is not|without|false|remain(?:s)? required|"
    r"remain(?:s)? outside|out of scope|guidance only|future work|private infrastructure)\b"
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
    "regulator_notice_content",
    "law_enforcement_report",
    "law_enforcement_report_content",
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


def sanitize_security_gap_closeout_value(value: Any) -> str:
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


def _build_controls() -> list[SecurityGapControl]:
    return [
        SecurityGapControl(
            name=name,
            evidence_path=path,
            domain=domain,
            description="Local public-repository review input.",
            present=Path(path).is_file(),
        )
        for name, path, domain in LOCAL_CONTROLS
    ]


def build_security_gap_domains(settings: Settings) -> list[SecurityGapItem]:
    del settings
    levels = {
        SecurityGapDomain.PRIVACY_REVIEW_TEMPLATE: ImplementationLevel.GUIDANCE_ONLY,
        SecurityGapDomain.ENCRYPTION_AT_REST_GUIDANCE: ImplementationLevel.GUIDANCE_ONLY,
        SecurityGapDomain.RETENTION_POLICY_VS_ENFORCEMENT: ImplementationLevel.POLICY_ONLY,
        SecurityGapDomain.AUDIT_LOGGING_POLICY_VS_IMPLEMENTATION: (
            ImplementationLevel.PARTIALLY_IMPLEMENTED
        ),
        SecurityGapDomain.NOTIFICATION_BOUNDARY: ImplementationLevel.INTENTIONALLY_NOT_IMPLEMENTED,
        SecurityGapDomain.INCIDENT_RESPONSE_PRIVATE_GAPS: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.PROVIDER_PERMISSIONS_PRIVATE_REVIEW: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.DATABASE_ROLES_PRIVATE_REVIEW: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.RELEASE_SECURITY_PRIVATE_REVIEW: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.LEGAL_COMPLIANCE_PRIVATE_REVIEW: (
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED
        ),
        SecurityGapDomain.OPERATIONAL_MONITORING_FUTURE_WORK: ImplementationLevel.FUTURE_WORK,
        SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY: ImplementationLevel.IMPLEMENTED,
        SecurityGapDomain.PRODUCT_LIMITATIONS: ImplementationLevel.IMPLEMENTED,
    }
    return [
        SecurityGapItem(
            code=domain.value,
            domain=domain,
            title=domain.value.replace("_", " ").title(),
            implementation_level=levels[domain],
            summary="Public-safe closeout position recorded for maintainer review.",
            private_review_required=(levels[domain] == ImplementationLevel.PRIVATE_REVIEW_REQUIRED),
        )
        for domain in SecurityGapDomain
    ]


def build_policy_implementation_matrix(settings: Settings) -> list[PolicyImplementationMatrixItem]:
    del settings
    rows = (
        (
            "Better intake UI/API",
            SecurityGapDomain.PRODUCT_LIMITATIONS,
            ImplementationLevel.IMPLEMENTED,
        ),
        (
            "Better sync controls",
            SecurityGapDomain.PRODUCT_LIMITATIONS,
            ImplementationLevel.PARTIALLY_IMPLEMENTED,
        ),
        (
            "Attachment processing improvements",
            SecurityGapDomain.PRODUCT_LIMITATIONS,
            ImplementationLevel.PARTIALLY_IMPLEMENTED,
        ),
        (
            "Notifications",
            SecurityGapDomain.NOTIFICATION_BOUNDARY,
            ImplementationLevel.INTENTIONALLY_NOT_IMPLEMENTED,
        ),
        (
            "Audit logging",
            SecurityGapDomain.AUDIT_LOGGING_POLICY_VS_IMPLEMENTATION,
            ImplementationLevel.PARTIALLY_IMPLEMENTED,
        ),
        (
            "Data retention",
            SecurityGapDomain.RETENTION_POLICY_VS_ENFORCEMENT,
            ImplementationLevel.POLICY_ONLY,
        ),
        (
            "Encryption at rest",
            SecurityGapDomain.ENCRYPTION_AT_REST_GUIDANCE,
            ImplementationLevel.GUIDANCE_ONLY,
        ),
        (
            "Privacy compliance template",
            SecurityGapDomain.PRIVACY_REVIEW_TEMPLATE,
            ImplementationLevel.GUIDANCE_ONLY,
        ),
        ("Threat model", SecurityGapDomain.PRODUCT_LIMITATIONS, ImplementationLevel.IMPLEMENTED),
        (
            "Final security readiness",
            SecurityGapDomain.PUBLIC_PRIVATE_BOUNDARY,
            ImplementationLevel.PRIVATE_REVIEW_REQUIRED,
        ),
        (
            "Operational monitoring",
            SecurityGapDomain.OPERATIONAL_MONITORING_FUTURE_WORK,
            ImplementationLevel.FUTURE_WORK,
        ),
        (
            "Legal compliance workflow",
            SecurityGapDomain.LEGAL_COMPLIANCE_PRIVATE_REVIEW,
            ImplementationLevel.OUT_OF_SCOPE,
        ),
    )
    return [
        PolicyImplementationMatrixItem(
            capability=capability,
            domain=domain,
            implementation_level=level,
            public_repo_position=(
                "Metadata and manifest handling only; private review remains required."
                if capability == "Attachment processing improvements"
                else "The implementation level is bounded to the public repository."
            ),
            private_review_required=level
            in {ImplementationLevel.PRIVATE_REVIEW_REQUIRED, ImplementationLevel.OUT_OF_SCOPE},
        )
        for capability, domain, level in rows
    ]


def build_private_security_action_register(settings: Settings) -> list[PrivateSecurityActionItem]:
    del settings
    actions = (
        (
            "provider_permissions",
            SecurityGapDomain.PROVIDER_PERMISSIONS_PRIVATE_REVIEW,
            "Review live provider permissions in an authorized private workspace.",
        ),
        (
            "database_roles",
            SecurityGapDomain.DATABASE_ROLES_PRIVATE_REVIEW,
            "Review actual database roles and access boundaries privately.",
        ),
        (
            "customer_data",
            SecurityGapDomain.CUSTOMER_DATA_HANDLING_PRIVATE_REVIEW,
            "Review actual customer-data handling and contractual obligations privately.",
        ),
        (
            "release_security",
            SecurityGapDomain.RELEASE_SECURITY_PRIVATE_REVIEW,
            "Complete private infrastructure and release-security review.",
        ),
        (
            "legal_obligations",
            SecurityGapDomain.LEGAL_COMPLIANCE_PRIVATE_REVIEW,
            "Have qualified reviewers assess applicable legal and privacy obligations.",
        ),
        (
            "incident_operations",
            SecurityGapDomain.INCIDENT_RESPONSE_PRIVATE_GAPS,
            "Define private incident contacts, authority, custody, and notification decisions.",
        ),
    )
    return [
        PrivateSecurityActionItem(code=code, domain=domain, action=action)
        for code, domain, action in actions
    ]


def build_privacy_review_template(settings: Settings) -> list[PrivacyTemplateSection]:
    del settings
    sections = (
        (
            "scope",
            "Processing scope",
            "Document intended processing scope using placeholders only.",
        ),
        (
            "data_inventory",
            "Data inventory",
            "Review categories, sources, destinations, and sensitivity privately.",
        ),
        (
            "purpose_and_access",
            "Purpose and access",
            "Record purpose, access roles, and minimization decisions privately.",
        ),
        (
            "retention",
            "Retention",
            (
                "Record policy decisions and note that public-repository enforcement is not "
                "implemented."
            ),
        ),
        (
            "rights_and_requests",
            "Rights and requests",
            "Define any required request process outside this public repository.",
        ),
        (
            "incident_and_notice",
            "Incident and notice",
            "Determine applicable notification duties through qualified private review.",
        ),
    )
    return [
        PrivacyTemplateSection(code=code, title=title, guidance=guidance)
        for code, title, guidance in sections
    ]


def build_encryption_at_rest_guidance(settings: Settings) -> list[EncryptionGuidanceItem]:
    del settings
    items = (
        (
            "database",
            "Database",
            (
                "Evaluate provider-managed encryption, key ownership, backup coverage, and "
                "access controls privately."
            ),
        ),
        (
            "object_storage",
            "Object storage",
            "Evaluate provider encryption settings, key policy, and object access privately.",
        ),
        (
            "backups",
            "Backups",
            "Confirm private backup encryption, restoration controls, and key-recovery ownership.",
        ),
        (
            "local_outputs",
            "Generated outputs",
            (
                "Keep generated private outputs outside the public repository and apply private "
                "storage controls."
            ),
        ),
        (
            "key_management",
            "Key management",
            "Define private key ownership, rotation, recovery, and separation of duties.",
        ),
    )
    return [
        EncryptionGuidanceItem(code=code, component=component, guidance=guidance)
        for code, component, guidance in items
    ]


def build_known_limitations_closeout(settings: Settings) -> list[KnownLimitationItem]:
    del settings
    rows = (
        (
            "retention_enforcement",
            SecurityGapDomain.RETENTION_POLICY_VS_ENFORCEMENT,
            "Retention guidance exists; persistent-data enforcement is not implemented.",
            ImplementationLevel.POLICY_ONLY,
        ),
        (
            "full_audit_log",
            SecurityGapDomain.AUDIT_LOGGING_POLICY_VS_IMPLEMENTATION,
            "Local lifecycle, sync, and event history is not a full immutable audit log.",
            ImplementationLevel.PARTIALLY_IMPLEMENTED,
        ),
        (
            "notifications",
            SecurityGapDomain.NOTIFICATION_BOUNDARY,
            "Notifications and alerting are intentionally not implemented.",
            ImplementationLevel.INTENTIONALLY_NOT_IMPLEMENTED,
        ),
        (
            "app_encryption",
            SecurityGapDomain.ENCRYPTION_AT_REST_GUIDANCE,
            (
                "Encryption-at-rest material is guidance only; app-level encryption is not "
                "implemented."
            ),
            ImplementationLevel.GUIDANCE_ONLY,
        ),
        (
            "privacy_workflows",
            SecurityGapDomain.PRIVACY_REVIEW_TEMPLATE,
            "The privacy template is a review aid; legal workflows are outside scope.",
            ImplementationLevel.GUIDANCE_ONLY,
        ),
        (
            "monitoring",
            SecurityGapDomain.OPERATIONAL_MONITORING_FUTURE_WORK,
            "Operational monitoring requires future private product and infrastructure work.",
            ImplementationLevel.FUTURE_WORK,
        ),
    )
    return [
        KnownLimitationItem(
            code=code, domain=domain, limitation=limitation, implementation_level=level
        )
        for code, domain, limitation, level in rows
    ]


def _validate_policy(settings: Settings) -> None:
    required = (
        settings.security_gap_closeout_require_placeholders,
        settings.security_gap_closeout_require_privacy_template,
        settings.security_gap_closeout_require_encryption_guidance,
        settings.security_gap_closeout_require_policy_implementation_matrix,
        settings.security_gap_closeout_require_private_action_register,
        settings.security_gap_closeout_require_no_compliance_claims,
        settings.security_gap_closeout_require_no_approval_claims,
    )
    allowed = (
        settings.security_gap_closeout_allow_real_identities,
        settings.security_gap_closeout_allow_real_domains,
        settings.security_gap_closeout_allow_real_urls,
        settings.security_gap_closeout_allow_report_contents,
        settings.security_gap_closeout_allow_private_paths,
    )
    if settings.security_gap_closeout_fail_closed and (not all(required) or any(allowed)):
        raise SecurityGapCloseoutBlockedError("Unsafe security-gap closeout policy blocked.")


def build_security_gap_closeout_report(settings: Settings) -> SecurityGapCloseoutReport:
    if not settings.security_gap_closeout_enabled:
        raise SecurityGapCloseoutError("Security-gap closeout disabled.")
    _validate_policy(settings)
    controls = _build_controls()
    domain_items = build_security_gap_domains(settings)
    matrix = build_policy_implementation_matrix(settings)
    actions = build_private_security_action_register(settings)
    privacy = build_privacy_review_template(settings)
    encryption = build_encryption_at_rest_guidance(settings)
    limitations = build_known_limitations_closeout(settings)
    missing = [control for control in controls if not control.present]
    gitignore = Path(".gitignore")
    ignores_ready = gitignore.is_file() and all(
        pattern in gitignore.read_text() for pattern in IGNORED_OUTPUTS
    )
    blockers = [f"Missing required local review input: {item.evidence_path}." for item in missing]
    if not ignores_ready:
        blockers.append("One or more generated security-gap output patterns are not ignored.")
    findings = [
        SecurityGapFinding(code="missing_local_control", message=message, severity="blocker")
        for message in blockers
    ]
    levels = [item.implementation_level for item in matrix]
    report = SecurityGapCloseoutReport(
        status=(
            SecurityGapCloseoutStatus.BLOCKED
            if blockers
            else SecurityGapCloseoutStatus.NEEDS_PRIVATE_REVIEW
        ),
        decision=(
            SecurityGapCloseoutDecision.BLOCKED
            if blockers
            else SecurityGapCloseoutDecision.NEEDS_PRIVATE_REVIEW
        ),
        domains_total=len(domain_items),
        implemented_items_total=levels.count(ImplementationLevel.IMPLEMENTED),
        partial_items_total=levels.count(ImplementationLevel.PARTIALLY_IMPLEMENTED),
        policy_only_items_total=levels.count(ImplementationLevel.POLICY_ONLY),
        guidance_only_items_total=levels.count(ImplementationLevel.GUIDANCE_ONLY),
        intentionally_not_implemented_items_total=levels.count(
            ImplementationLevel.INTENTIONALLY_NOT_IMPLEMENTED
        ),
        private_review_items_total=levels.count(ImplementationLevel.PRIVATE_REVIEW_REQUIRED),
        future_work_items_total=levels.count(ImplementationLevel.FUTURE_WORK),
        encryption_at_rest_guidance_provided=bool(encryption),
        findings=findings[: settings.security_gap_closeout_max_findings],
        blockers=blockers,
        warnings=[
            "Private infrastructure, security, privacy, and legal review remains required.",
            (
                "This offline closeout grants no production, pilot, release, deployment, "
                "compliance, or certification approval."
            ),
        ],
        controls=controls,
        domain_items=domain_items,
        policy_implementation_matrix=matrix,
        private_security_actions=actions,
        privacy_template_sections=privacy,
        encryption_guidance_items=encryption,
        known_limitations=limitations,
        recommended_next_steps=[
            "Complete the private security action register in an authorized workspace.",
            (
                "Obtain qualified privacy, legal, infrastructure, and operational review before "
                "live use."
            ),
            (
                "Keep all real evidence, identities, endpoints, credentials, and decisions "
                "outside the public repository."
            ),
        ],
    )
    validate_security_gap_closeout_report_safe(report)
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


def validate_security_gap_closeout_report_safe(report: Any) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    if not isinstance(payload, str) and set(_walk_keys(payload)) & FORBIDDEN_KEYS:
        raise SecurityGapCloseoutBlockedError("Unsafe security-gap closeout content blocked.")
    strings = [payload] if isinstance(payload, str) else list(_walk_strings(payload))
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
    for value in strings:
        if any(pattern.search(value) for pattern in patterns):
            raise SecurityGapCloseoutBlockedError("Unsafe security-gap closeout content blocked.")
        if UNSAFE_CLAIM_PATTERN.search(value) and not NEGATION_PATTERN.search(value):
            raise SecurityGapCloseoutBlockedError("Unsafe security-gap closeout claim blocked.")


def render_security_gap_closeout_markdown(report: SecurityGapCloseoutReport) -> str:
    text = "\n".join(
        [
            "# Security Gap Closeout",
            "",
            f"Status: `{report.status.value}`",
            f"Decision: `{report.decision.value}`",
            "",
            "This offline closeout uses local public-repository files only.",
            "",
            *(
                f"- `{item.capability}`: `{item.implementation_level.value}`"
                for item in report.policy_implementation_matrix
            ),
            "",
            (
                "Private security and legal review remains required. No production, pilot, "
                "release, deployment, compliance, or certification approval is granted."
            ),
            (
                "No live operation, external call, encryption, deletion, retention enforcement, "
                "notification, scanner, or database connection was attempted."
            ),
            "",
        ]
    )
    validate_security_gap_closeout_report_safe(text)
    return text


def render_privacy_review_template_markdown(report: SecurityGapCloseoutReport) -> str:
    text = "\n".join(
        [
            "# Privacy Review Template",
            "",
            (
                "Maintainer and qualified legal-review aid only; no privacy or legal compliance "
                "is claimed."
            ),
            "",
            *(
                f"## {item.title}\n\n{item.guidance}\n\nReference: `{item.legal_review_reference}`"
                for item in report.privacy_template_sections
            ),
            "",
        ]
    )
    validate_security_gap_closeout_report_safe(text)
    return text


def render_encryption_at_rest_guidance_markdown(report: SecurityGapCloseoutReport) -> str:
    text = "\n".join(
        [
            "# Encryption-at-Rest Guidance",
            "",
            "Guidance only. App-level encryption at rest is not implemented by this pack.",
            "",
            *(
                f"- **{item.component}:** {item.guidance}"
                for item in report.encryption_guidance_items
            ),
            "",
        ]
    )
    validate_security_gap_closeout_report_safe(text)
    return text


def render_private_security_action_register_markdown(report: SecurityGapCloseoutReport) -> str:
    text = "\n".join(
        [
            "# Private Security Action Register",
            "",
            "Complete only in an authorized private workspace; do not add private evidence here.",
            "",
            *(
                f"- [ ] `{item.code}` — {item.action} Reference: `{item.private_review_reference}`"
                for item in report.private_security_actions
            ),
            "",
        ]
    )
    validate_security_gap_closeout_report_safe(text)
    return text


def render_known_limitations_closeout_markdown(report: SecurityGapCloseoutReport) -> str:
    text = "\n".join(
        [
            "# Known Limitations Closeout",
            "",
            *(
                f"- `{item.code}` (`{item.implementation_level.value}`) — {item.limitation}"
                for item in report.known_limitations
            ),
            "",
        ]
    )
    validate_security_gap_closeout_report_safe(text)
    return text


def _csv_cell(value: Any) -> str:
    text = sanitize_security_gap_closeout_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_policy_implementation_matrix_csv(report: SecurityGapCloseoutReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "capability",
            "domain",
            "implementation_level",
            "public_repo_position",
            "private_review_required",
        )
    )
    for item in report.policy_implementation_matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.capability,
                    item.domain.value,
                    item.implementation_level.value,
                    item.public_repo_position,
                    str(item.private_review_required).lower(),
                )
            )
        )
    text = output.getvalue()
    validate_security_gap_closeout_report_safe(text)
    return text


def _safe_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-security-gap-closeout-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if (
        ".." in root.parts
        or (root.is_absolute() and not temporary)
        or (not temporary and root.parts[:1] not in {(value,) for value in SAFE_ROOTS})
    ):
        raise SecurityGapCloseoutBlockedError("Unsafe output root.")
    return root


def write_security_gap_closeout_artifacts(
    report: SecurityGapCloseoutReport, output_root: str | Path
) -> SecurityGapCloseoutArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "security-gap-closeout-report.json": report.model_dump_json(indent=2),
        "security-gap-closeout-report.md": render_security_gap_closeout_markdown(report),
        "privacy-review-template.md": render_privacy_review_template_markdown(report),
        "encryption-at-rest-guidance.md": render_encryption_at_rest_guidance_markdown(report),
        "private-security-action-register.md": render_private_security_action_register_markdown(
            report
        ),
        "known-limitations-closeout.md": render_known_limitations_closeout_markdown(report),
        "policy-implementation-matrix.csv": render_policy_implementation_matrix_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {
            "files": sorted(artifacts),
            "sanitized": True,
            "live_operations": False,
            "external_operations": False,
            "approval_operations": False,
            "encryption_operations": False,
            "deletion_operations": False,
            "notification_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in artifacts.items():
        validate_security_gap_closeout_report_safe(content)
        (root / filename).write_text(content)
    return SecurityGapCloseoutArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=sorted(artifacts),
    )
