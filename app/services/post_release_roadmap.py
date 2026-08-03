# ruff: noqa: E501
"""Offline, public-safe post-release roadmap and known-limitations review.

J10 is a planning aid for work that may happen after a future, separately
authorised 0.1.0 release.  It reads only a small allow-list of local public
repository files and never performs a release, build, publish, tag, deploy,
network call, issue/ticket action, or approval.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.post_release_roadmap import (
    FutureWorkCategory,
    FutureWorkItem,
    HostedPilotBacklogItem,
    KnownLimitationCategory,
    KnownLimitationItem,
    PostReleaseFinding,
    PostReleaseRoadmapArtifactResult,
    PostReleaseRoadmapDecision,
    PostReleaseRoadmapMatrixItem,
    PostReleaseRoadmapReport,
    PostReleaseRoadmapStatus,
    PreTagReminderItem,
    PrivateReviewBacklogItem,
    ProductImprovementItem,
    ProductionizationBacklogItem,
    RoadmapDomain,
    RoadmapDomainSummary,
    RoadmapItemStatus,
    RoadmapPriority,
    RoadmapTimeframe,
    SecurityFutureWorkItem,
)
from app.services.api_docs_review import sanitize_api_docs_value


class PostReleaseRoadmapError(ValueError):
    """Base error raised for invalid public roadmap input."""


class PostReleaseRoadmapBlockedError(PostReleaseRoadmapError):
    """Raised whenever a fail-closed roadmap condition is not satisfied."""


REPOSITORY_FILES = (
    "README.md",
    "QUICKSTART.md",
    "CHANGELOG.md",
    "Makefile",
    ".gitignore",
    "mkdocs.yml",
    "app/version.py",
    "docs/versioned-release-handoff.md",
    "docs/release-notes-v0.1.0.md",
    "docs/release-scope-summary.md",
    "docs/maintainer-handoff.md",
    "docs/maintainer-review-checklist.md",
    "docs/release-candidate-review.md",
    "docs/version-prep-review.md",
    "docs/security-gap-closeout.md",
    "docs/final-security-readiness-review.md",
    "docs/hosted-ui-preparation.md",
    "docs/api-docs-review.md",
    "docs/demo-data-seed-reset.md",
    "docs/project-status.md",
    "docs/roadmap.md",
    "scripts/audit_public_safety.py",
    "scripts/audit_routes_read_only.py",
    "scripts/audit_public_usability.py",
    "scripts/check_docs_site.py",
)

REQUIRED_IGNORES = (
    "post-release-roadmap-output/",
    "post-release-output/",
    "known-limitations-output/",
    "future-work-output/",
    "roadmap-review-output/",
    "*.post-release-roadmap-report.json",
    "*.post-release-roadmap-report.md",
    "*.known-limitations-register.md",
    "*.future-work-backlog.md",
    "*.private-review-backlog.md",
    "*.pre-tag-reminder-checklist.md",
    "*.post-release-roadmap-matrix.csv",
)

ARTIFACT_FILES = (
    "post-release-roadmap-report.json",
    "post-release-roadmap-report.md",
    "known-limitations-register.md",
    "future-work-backlog.md",
    "private-review-backlog.md",
    "pre-tag-reminder-checklist.md",
    "post-release-roadmap-matrix.csv",
    "manifest.json",
)

SAFE_ROOT_NAMES = {
    "post-release-roadmap-output",
    "post-release-output",
    "known-limitations-output",
    "future-work-output",
    "roadmap-review-output",
}
TMP_PREFIXES = (
    "/tmp/procore-intake-bridge-post-release-roadmap-",
    "/private/tmp/procore-intake-bridge-post-release-roadmap-",
)
SEMVER = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
UNSAFE_COMMAND = re.compile(
    r"(?i)(?:python\s+-m\s+build|docker\s+(?:build|push)|git\s+tag|"
    r"(?:^|\s)make\s+(?:publish|deploy|tag|release)(?:\s|$)|twine\s+upload|"
    r"gh\s+(?:release|issue)|(?:create|open)\s+(?:issues?|tickets?))"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\bproduction[- ]ready\b|"
    r"\b(?:production|pilot|release|deployment)\s+(?:(?:is|was|has been)\s+)?approved\b|"
    r"\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance)\s+(?:(?:is|was|has been)\s+)?certified\b|"
    r"\b(?:gdpr|ccpa|hipaa|privacy|legally)\s+(?:(?:is|was|has been)\s+)?compliant\b|"
    r"\b(?:actual\s+)?release\s+(?:was|has been|is)\s+(?:performed|complete|completed|published|created)\b|"
    r"\b(?:package|version)\s+(?:was|has been|is)\s+(?:published|released)\b|"
    r"\b(?:tag|git tag)\s+(?:was|has been|is)\s+(?:created|pushed)\b|"
    r"\b(?:deployment|deploy)\s+(?:was|has been|is)\s+(?:performed|completed|deployed)\b|"
    r"\b(?:issue|ticket)s?\s+(?:were|was|have been|has been)\s+"
    r"(?:created|opened|filed|closed|resolved)\b|"
    r"\b(?:approval|authorization)\s+(?:(?:was|has been|is)\s+)?granted\b"
)
NEGATED_CLAIM = re.compile(
    r"(?i)\b(?:not|no|never|without|does not|do not|is not|isn't|out of scope|"
    r"requires separate|unreleased|later|manual|future)\b"
)


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def sanitize_post_release_roadmap_value(value: Any) -> str:
    """Bound and redact a scalar before it enters public roadmap material."""

    return sanitize_api_docs_value(value)


def _read(path: str | Path) -> str:
    candidate = Path(path)
    try:
        return candidate.read_text(encoding="utf-8") if candidate.is_file() else ""
    except (OSError, UnicodeError):
        return ""


def _validate_settings(settings: Settings) -> str:
    if not _setting(settings, "post_release_roadmap_enabled", True):
        raise PostReleaseRoadmapBlockedError("Post-release roadmap is disabled.")
    if not _setting(settings, "post_release_roadmap_fail_closed", True):
        raise PostReleaseRoadmapBlockedError("Post-release roadmap must remain fail closed.")
    required = (
        "post_release_roadmap_require_known_limitations",
        "post_release_roadmap_require_private_review_backlog",
        "post_release_roadmap_require_productionization_backlog",
        "post_release_roadmap_require_hosted_pilot_backlog",
        "post_release_roadmap_require_security_future_work",
        "post_release_roadmap_require_product_backlog",
        "post_release_roadmap_require_pre_tag_reminder",
        "post_release_roadmap_require_no_release_actions",
        "post_release_roadmap_require_no_build",
        "post_release_roadmap_require_no_publish",
        "post_release_roadmap_require_no_tag",
        "post_release_roadmap_require_no_deploy",
    )
    if not all(bool(_setting(settings, name, True)) for name in required):
        raise PostReleaseRoadmapBlockedError("A required J10 control is disabled.")
    unsafe = (
        "post_release_roadmap_allow_real_identities",
        "post_release_roadmap_allow_real_domains",
        "post_release_roadmap_allow_real_urls",
        "post_release_roadmap_allow_report_contents",
        "post_release_roadmap_allow_private_paths",
    )
    if any(bool(_setting(settings, name, False)) for name in unsafe):
        raise PostReleaseRoadmapBlockedError("Unsafe roadmap material is enabled.")
    target = str(_setting(settings, "post_release_roadmap_target_version", "0.1.0"))
    if target != "0.1.0" or not SEMVER.fullmatch(target):
        raise PostReleaseRoadmapBlockedError("The roadmap target must be 0.1.0.")
    return target


def build_post_release_dependencies(settings: Settings) -> dict[str, bool]:
    """Check only local public files and generated-output ignore coverage."""

    _validate_settings(settings)
    dependencies = {path: Path(path).is_file() for path in REPOSITORY_FILES}
    gitignore = _read(".gitignore")
    dependencies["generated_output_ignores"] = all(item in gitignore for item in REQUIRED_IGNORES)
    dependencies["workflows_unchanged"] = True
    return dependencies


def _summary(
    domain: RoadmapDomain,
    summary: str,
    *,
    private: bool = False,
    status: RoadmapItemStatus | None = None,
) -> RoadmapDomainSummary:
    return RoadmapDomainSummary(
        domain=domain,
        status=status
        or (
            RoadmapItemStatus.REQUIRES_PRIVATE_REVIEW if private else RoadmapItemStatus.FUTURE_WORK
        ),
        summary=summary,
        source="public repository planning inputs",
        private_review_required=private,
    )


def build_roadmap_domain_summaries(settings: Settings) -> list[RoadmapDomainSummary]:
    _validate_settings(settings)
    private_domains = {
        RoadmapDomain.PRIVATE_REVIEW,
        RoadmapDomain.HOSTED_PILOT,
        RoadmapDomain.PRODUCTIONIZATION,
        RoadmapDomain.LIVE_SANDBOX_VALIDATION,
        RoadmapDomain.CUSTOMER_ONBOARDING,
        RoadmapDomain.PRIVACY_LEGAL,
        RoadmapDomain.SECURITY_COMPLIANCE,
        RoadmapDomain.DATA_RETENTION,
        RoadmapDomain.ENCRYPTION_AT_REST,
        RoadmapDomain.OBSERVABILITY,
        RoadmapDomain.SUPPORT_OPERATIONS,
        RoadmapDomain.PRE_TAG_DECISION,
    }
    descriptions = {
        RoadmapDomain.PRIVATE_REVIEW: "Sandbox and Pilot evidence needs an authorised private review.",
        RoadmapDomain.HOSTED_PILOT: "Hosted pilot security and infrastructure review remains future work.",
        RoadmapDomain.PRODUCTIONIZATION: "Production-shaped controls are planning inputs, not approval.",
        RoadmapDomain.LIVE_SANDBOX_VALIDATION: "Live Procore sandbox validation is separately gated and not run.",
        RoadmapDomain.CUSTOMER_ONBOARDING: "Real customer onboarding decisions require private ownership review.",
        RoadmapDomain.NOTIFICATIONS_ALERTING: "Notifications and alerting are not implemented in this phase.",
        RoadmapDomain.AUDIT_LOGGING: "A complete durable audit-log system is future work.",
        RoadmapDomain.DATA_RETENTION: "Retention and deletion enforcement remain future work.",
        RoadmapDomain.ENCRYPTION_AT_REST: "Deployment-specific encryption and key custody need private design.",
        RoadmapDomain.PRIVACY_LEGAL: "Privacy and legal review remains outside this public planning layer.",
        RoadmapDomain.SECURITY_COMPLIANCE: "Security/compliance evidence and decisions require private review.",
        RoadmapDomain.API_HARDENING: "API hardening and versioning are possible future product work.",
        RoadmapDomain.HOSTED_UI: "Hosted UI implementation is not included in 0.1.0 planning.",
        RoadmapDomain.OPERATOR_EXPERIENCE: "Operator and support experience improvements are candidates only.",
        RoadmapDomain.DOCS_HOSTING: "Documentation hosting is optional future maintainer work.",
        RoadmapDomain.RELEASE_AUTOMATION: "Release automation is not added; a maintainer may revisit it later.",
        RoadmapDomain.OBSERVABILITY: "Operational monitoring and incident evidence need private review.",
        RoadmapDomain.SUPPORT_OPERATIONS: "Support ownership and response paths remain to be designed privately.",
        RoadmapDomain.PRODUCT_BACKLOG: "Product backlog candidates are uncommitted and unscheduled.",
        RoadmapDomain.KNOWN_LIMITATIONS: "Known limitations are recorded without claiming they are fixed.",
        RoadmapDomain.PRE_TAG_DECISION: "A human maintainer must decide any later tag or release action.",
    }
    return [
        _summary(domain, descriptions[domain], private=domain in private_domains)
        for domain in RoadmapDomain
    ]


def _limitation(
    category: KnownLimitationCategory,
    title: str,
    summary: str,
    next_step: str,
) -> KnownLimitationItem:
    return KnownLimitationItem(
        category=category,
        title=title,
        summary=summary,
        next_step=next_step,
    )


def build_known_limitations_register(settings: Settings) -> list[KnownLimitationItem]:
    _validate_settings(settings)
    return [
        _limitation(
            KnownLimitationCategory.PRODUCTION_APPROVAL,
            "No production approval",
            "Production use and production approval are outside this public repository review.",
            "Complete private security, privacy, infrastructure, and owner review.",
        ),
        _limitation(
            KnownLimitationCategory.HOSTED_DEPLOYMENT,
            "No hosted deployment",
            "Hosted deployment and hosted availability are not implemented or claimed.",
            "Prepare a separately scoped hosted pilot review if authorized.",
        ),
        _limitation(
            KnownLimitationCategory.NOTIFICATIONS,
            "No notification system",
            "Notification providers, alert delivery, and telemetry are intentionally absent.",
            "Design a private operations proposal before any implementation.",
        ),
        _limitation(
            KnownLimitationCategory.AUDIT_LOG,
            "No full audit log",
            "A complete durable audit-log and incident evidence system is future work.",
            "Define retention, access, and incident requirements privately.",
        ),
        _limitation(
            KnownLimitationCategory.RETENTION,
            "No retention enforcement",
            "Retention periods, deletion enforcement, and legal disposition are not implemented.",
            "Complete privacy/legal and data-owner review before scope is proposed.",
        ),
        _limitation(
            KnownLimitationCategory.ENCRYPTION,
            "No app-level encryption claim",
            "Application-level encryption behavior and deployment key custody are not provided.",
            "Specify infrastructure and security controls in a private review.",
        ),
        _limitation(
            KnownLimitationCategory.PRIVACY_LEGAL,
            "No privacy or legal compliance claim",
            "This public planning material does not claim privacy, legal, or compliance approval.",
            "Obtain separate qualified privacy/legal review for any later use.",
        ),
    ]


def _future(
    category: FutureWorkCategory,
    title: str,
    summary: str,
    next_step: str,
    *,
    domain: RoadmapDomain | None = None,
    priority: RoadmapPriority = RoadmapPriority.MEDIUM,
    timeframe: RoadmapTimeframe = RoadmapTimeframe.AFTER_0_1_0_RELEASE,
    private: bool = False,
) -> FutureWorkItem:
    return FutureWorkItem(
        category=category,
        domain=domain,
        title=title,
        summary=summary,
        next_step=next_step,
        priority=priority,
        timeframe=timeframe,
        private_review_required=private,
    )


def build_future_work_backlog(settings: Settings) -> list[FutureWorkItem]:
    _validate_settings(settings)
    return [
        _future(
            FutureWorkCategory.PRIVATE_REVIEW,
            "Private Sandbox/Pilot review",
            "Validate private evidence and boundaries.",
            "Record an opaque private review reference.",
            domain=RoadmapDomain.PRIVATE_REVIEW,
            priority=RoadmapPriority.HIGH,
            timeframe=RoadmapTimeframe.BEFORE_PRIVATE_PILOT,
            private=True,
        ),
        _future(
            FutureWorkCategory.HOSTED_PILOT,
            "Hosted pilot review",
            "Assess hosted security and infrastructure controls.",
            "Complete a private hosted-pilot design review.",
            domain=RoadmapDomain.HOSTED_PILOT,
            priority=RoadmapPriority.HIGH,
            timeframe=RoadmapTimeframe.BEFORE_HOSTED_PILOT,
            private=True,
        ),
        _future(
            FutureWorkCategory.LIVE_SANDBOX_VALIDATION,
            "Live sandbox validation",
            "A future authorized live read may be evaluated separately.",
            "Use a separately gated private runbook; this service performs no live call.",
            domain=RoadmapDomain.LIVE_SANDBOX_VALIDATION,
            timeframe=RoadmapTimeframe.BEFORE_PRIVATE_PILOT,
            private=True,
        ),
        _future(
            FutureWorkCategory.CUSTOMER_ONBOARDING,
            "Customer onboarding decision",
            "Real customer onboarding needs ownership and privacy decisions.",
            "Define onboarding scope privately before implementation.",
            domain=RoadmapDomain.CUSTOMER_ONBOARDING,
            private=True,
        ),
        _future(
            FutureWorkCategory.NOTIFICATIONS_ALERTING,
            "Notifications and alerting",
            "Notification and alerting capabilities are not in 0.1.0.",
            "Design a provider-neutral private proposal.",
            domain=RoadmapDomain.NOTIFICATIONS_ALERTING,
        ),
        _future(
            FutureWorkCategory.AUDIT_LOGGING,
            "Full audit logging",
            "Durable audit history is a future requirement.",
            "Define evidence and access requirements.",
            domain=RoadmapDomain.AUDIT_LOGGING,
            private=True,
        ),
        _future(
            FutureWorkCategory.DATA_RETENTION,
            "Retention enforcement",
            "Retention and deletion policy enforcement may be scoped later.",
            "Complete privacy/legal review.",
            domain=RoadmapDomain.DATA_RETENTION,
            private=True,
        ),
        _future(
            FutureWorkCategory.ENCRYPTION_AT_REST,
            "Encryption at rest",
            "Deployment-specific encryption and key custody may need design.",
            "Complete private infrastructure review.",
            domain=RoadmapDomain.ENCRYPTION_AT_REST,
            private=True,
        ),
        _future(
            FutureWorkCategory.PRIVACY_LEGAL,
            "Privacy and legal review",
            "Privacy/legal requirements remain a future decision.",
            "Obtain qualified private review.",
            domain=RoadmapDomain.PRIVACY_LEGAL,
            private=True,
        ),
        _future(
            FutureWorkCategory.API_HARDENING,
            "API hardening and versioning",
            "Hardening and version policy are uncommitted candidates.",
            "Write a separate scoped proposal.",
            domain=RoadmapDomain.API_HARDENING,
        ),
        _future(
            FutureWorkCategory.HOSTED_UI,
            "Hosted UI implementation",
            "Hosted UI work is not included in this planning phase.",
            "Review product and infrastructure scope later.",
            domain=RoadmapDomain.HOSTED_UI,
        ),
        _future(
            FutureWorkCategory.RELEASE_AUTOMATION,
            "Installer and release automation",
            "Automation is optional future maintainer work.",
            "Revisit only after a separate design review.",
            domain=RoadmapDomain.RELEASE_AUTOMATION,
            timeframe=RoadmapTimeframe.LATER,
        ),
        _future(
            FutureWorkCategory.DOCUMENTATION_HOSTING,
            "Documentation hosting",
            "Hosted docs are not published by J10.",
            "Evaluate hosting privately if maintainers choose it.",
            domain=RoadmapDomain.DOCS_HOSTING,
            timeframe=RoadmapTimeframe.LATER,
        ),
        _future(
            FutureWorkCategory.OBSERVABILITY,
            "Observability and support",
            "Operational monitoring and support evidence are future work.",
            "Define ownership and data boundaries privately.",
            domain=RoadmapDomain.OBSERVABILITY,
            private=True,
        ),
    ]


def build_private_review_backlog(settings: Settings) -> list[PrivateReviewBacklogItem]:
    _validate_settings(settings)
    rows = (
        (
            "Security and identity review",
            "Review tenant, role, session, and access boundaries.",
            "Security and owner review.",
        ),
        (
            "Privacy and legal review",
            "Review retention, deletion, redaction, and data-use obligations.",
            "Qualified privacy/legal review.",
        ),
        (
            "Infrastructure review",
            "Review database, storage, encryption, backup, recovery, and monitoring controls.",
            "Private infrastructure evidence.",
        ),
        (
            "Hosted pilot review",
            "Review hosted pilot threat model, isolation, and rollback boundaries.",
            "Private hosted-pilot decision.",
        ),
        (
            "Maintainer release decision",
            "Review scope, limitations, notes, and pre-tag reminders.",
            "Human maintainer decision outside this service.",
        ),
    )
    return [
        PrivateReviewBacklogItem(
            title=title,
            summary=summary,
            next_step=next_step,
            priority=RoadmapPriority.HIGH if index < 3 else RoadmapPriority.MAINTAINER_DECISION,
            timeframe=RoadmapTimeframe.BEFORE_PRIVATE_PILOT,
        )
        for index, (title, summary, next_step) in enumerate(rows)
    ]


def build_productionization_backlog(settings: Settings) -> list[ProductionizationBacklogItem]:
    _validate_settings(settings)
    rows = (
        (
            "Production identity and tenant isolation",
            "Define production access boundaries.",
            "Private security and owner review.",
        ),
        (
            "Recovery and operations evidence",
            "Define backups, rollback, monitoring, and incident ownership.",
            "Private infrastructure runbook.",
        ),
        (
            "Encryption and key custody",
            "Choose deployment-specific controls without implementing them here.",
            "Private security design.",
        ),
    )
    return [
        ProductionizationBacklogItem(
            title=title,
            summary=summary,
            next_step=next_step,
            priority=RoadmapPriority.HIGH,
            private_review_required=True,
        )
        for title, summary, next_step in rows
    ]


def build_hosted_pilot_backlog(settings: Settings) -> list[HostedPilotBacklogItem]:
    _validate_settings(settings)
    rows = (
        (
            "Hosted isolation review",
            "Assess tenant and operator isolation for a future hosted pilot.",
            "Private hosted infrastructure review.",
        ),
        (
            "Hosted ingress and TLS review",
            "Assess ingress, domain, and certificate ownership privately.",
            "Private security and infrastructure review.",
        ),
        (
            "Pilot support and rollback review",
            "Define support, stop, and rollback expectations.",
            "Private operations decision.",
        ),
    )
    return [
        HostedPilotBacklogItem(
            title=title,
            summary=summary,
            next_step=next_step,
            priority=RoadmapPriority.HIGH,
            private_review_required=True,
        )
        for title, summary, next_step in rows
    ]


def build_security_future_work_register(settings: Settings) -> list[SecurityFutureWorkItem]:
    _validate_settings(settings)
    rows = (
        (
            "Durable audit log",
            "Define tamper-aware audit evidence and access policy.",
            "Private security review.",
        ),
        (
            "Retention and deletion",
            "Define lifecycle controls and legal disposition.",
            "Private privacy/legal review.",
        ),
        (
            "Encryption at rest",
            "Define encryption and key custody for any later deployment.",
            "Private infrastructure review.",
        ),
        (
            "Incident and observability evidence",
            "Define monitoring, alerts, and incident evidence boundaries.",
            "Private operations review.",
        ),
    )
    return [
        SecurityFutureWorkItem(
            title=title,
            summary=summary,
            next_step=next_step,
            priority=RoadmapPriority.HIGH,
            private_review_required=True,
        )
        for title, summary, next_step in rows
    ]


def build_product_improvement_backlog(settings: Settings) -> list[ProductImprovementItem]:
    _validate_settings(settings)
    rows = (
        (
            "API hardening and versioning",
            "Consider durable API compatibility guidance.",
            "Separate product and security review.",
        ),
        (
            "Hosted UI experience",
            "Consider hosted UI implementation only if separately approved.",
            "Product and infrastructure review.",
        ),
        (
            "Operator workflow improvements",
            "Consider triage, onboarding, and support improvements.",
            "Maintainer and operator review.",
        ),
        (
            "Read-only boundary decisions",
            "Evaluate any future write-back or communication scope explicitly.",
            "Product, Procore owner, and security review.",
        ),
    )
    return [
        ProductImprovementItem(
            title=title, summary=summary, next_step=next_step, priority=RoadmapPriority.MEDIUM
        )
        for title, summary, next_step in rows
    ]


def build_pre_tag_reminder_checklist(settings: Settings) -> list[PreTagReminderItem]:
    _validate_settings(settings)
    rows = (
        (
            "version_scope",
            "Confirm the intended 0.1.0 version and source map agree.",
        ),
        (
            "review_limitations",
            "Read known limitations, future work, and private-review boundaries.",
        ),
        (
            "run_local_checks",
            "Run local quality, safety, route, and docs checks with disposable output.",
        ),
        (
            "inspect_staged_files",
            "Inspect staged files for secrets, private paths, IDs, reports, and generated output.",
        ),
        (
            "confirm_private_review",
            "Confirm private security, privacy/legal, infrastructure, operations, and ownership review references.",
        ),
        (
            "record_decision",
            "Record DEFER, REJECT, or AUTHORIZE_LATER as a human decision outside this repository.",
        ),
    )
    return [PreTagReminderItem(code=code, description=description) for code, description in rows]


def build_post_release_roadmap_matrix(settings: Settings) -> list[PostReleaseRoadmapMatrixItem]:
    _validate_settings(settings)
    summaries = build_roadmap_domain_summaries(settings)
    limitations = build_known_limitations_register(settings)
    limitation_text = {item.category.value: item.title for item in limitations}
    return [
        PostReleaseRoadmapMatrixItem(
            domain=item.domain,
            status=item.status,
            priority=RoadmapPriority.HIGH
            if item.private_review_required
            else RoadmapPriority.MEDIUM,
            timeframe=RoadmapTimeframe.BEFORE_PRIVATE_PILOT
            if item.private_review_required
            else RoadmapTimeframe.AFTER_0_1_0_RELEASE,
            summary=item.summary,
            known_limitation=limitation_text.get(
                item.domain.value, "No limitation register entry; candidate future work only."
            ),
            next_step="Complete the documented maintainer or private review before any later decision.",
        )
        for item in summaries
    ]


def build_post_release_roadmap_report(settings: Settings) -> PostReleaseRoadmapReport:
    target = _validate_settings(settings)
    dependencies = build_post_release_dependencies(settings)
    summaries = build_roadmap_domain_summaries(settings)
    limitations = build_known_limitations_register(settings)
    future = build_future_work_backlog(settings)
    private = build_private_review_backlog(settings)
    production = build_productionization_backlog(settings)
    hosted = build_hosted_pilot_backlog(settings)
    security = build_security_future_work_register(settings)
    product = build_product_improvement_backlog(settings)
    pre_tag = build_pre_tag_reminder_checklist(settings)
    matrix = build_post_release_roadmap_matrix(settings)
    findings = [
        PostReleaseFinding(
            code=f"{summary.domain.value}_{summary.status.value}",
            message=summary.summary,
            severity="warning",
            domain=summary.domain,
            source=summary.source,
        )
        for summary in summaries
    ]
    missing = [name for name, present in dependencies.items() if not present]
    findings.extend(
        PostReleaseFinding(
            code=f"missing_{Path(name).stem}",
            message="A required local public planning input is missing.",
            severity="blocker",
            source=name,
        )
        for name in missing
    )
    maximum = int(_setting(settings, "post_release_roadmap_max_findings", 400))
    if len(findings) > maximum:
        raise PostReleaseRoadmapBlockedError("Roadmap findings exceed the configured limit.")
    blockers = [item.message for item in findings if item.severity == "blocker"]
    warnings = [item.message for item in findings if item.severity != "blocker"]
    report = PostReleaseRoadmapReport(
        status=PostReleaseRoadmapStatus.BLOCKED
        if blockers
        else PostReleaseRoadmapStatus.NEEDS_REVIEW,
        decision=PostReleaseRoadmapDecision.BLOCKED
        if blockers
        else PostReleaseRoadmapDecision.READY_FOR_MAINTAINER_REVIEW,
        target_version=target,
        dependencies=dependencies,
        domain_summaries=summaries,
        roadmap_items=findings.copy(),
        known_limitations=limitations,
        future_work_backlog=future,
        private_review_backlog=private,
        productionization_backlog=production,
        hosted_pilot_backlog=hosted,
        security_future_work=security,
        product_improvement_backlog=product,
        pre_tag_reminders=pre_tag,
        roadmap_matrix=matrix,
        findings=findings,
        blockers=blockers,
        warnings=warnings,
        roadmap_items_total=len(findings),
        known_limitations_total=len(limitations),
        private_review_items_total=len(private),
        productionization_items_total=len(production),
        hosted_pilot_items_total=len(hosted),
        security_future_work_items_total=len(security),
        product_improvement_items_total=len(product),
        pre_tag_reminders_total=len(pre_tag),
        public_repo_safe_for_roadmap_review=not blockers,
        maintainer_decision_required=True,
        private_review_required=True,
        recommended_next_steps=[
            "Review this planning-only roadmap with a human maintainer.",
            "Keep private security, privacy/legal, infrastructure, and ownership evidence outside Git.",
            "Use the pre-tag reminders before any separately authorized future decision.",
            "Do not perform release, build, publish, tag, deploy, issue, or ticket actions from J10.",
        ],
    )
    validate_post_release_roadmap_report_safe(report)
    return report


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)
    elif isinstance(value, str):
        yield value


def validate_post_release_roadmap_report_safe(report: PostReleaseRoadmapReport) -> None:
    unsafe_flags = (
        report.actual_release_performed,
        report.package_build_attempted,
        report.docker_build_attempted,
        report.publish_attempted,
        report.tag_attempted,
        report.release_attempted,
        report.deploy_attempted,
        report.docs_deploy_attempted,
        report.workflow_changed,
        report.github_api_attempted,
        report.issue_creation_attempted,
        report.ticket_creation_attempted,
        report.package_registry_call_attempted,
        report.external_call_attempted,
        report.procore_call_attempted,
        report.cloud_call_attempted,
        report.notification_attempted,
        report.telemetry_added,
        report.production_approval_granted,
        report.release_approval_granted,
        report.pilot_approval_granted,
        report.deployment_approval_granted,
        report.compliance_claimed,
        report.certification_claimed,
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
    )
    if any(unsafe_flags) or report.blockers or not report.public_repo_safe_for_roadmap_review:
        raise PostReleaseRoadmapBlockedError("The post-release roadmap failed closed.")
    if not report.maintainer_decision_required or not report.private_review_required:
        raise PostReleaseRoadmapBlockedError("Maintainer and private review must remain required.")
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_post_release_roadmap_value(value) == "[redacted]":
            raise PostReleaseRoadmapBlockedError("The roadmap contains unsafe public material.")
        if UNSAFE_COMMAND.search(value):
            raise PostReleaseRoadmapBlockedError("The roadmap contains an unsafe command.")
        match = UNSAFE_CLAIM.search(value)
        if match and not NEGATED_CLAIM.search(
            value[max(0, match.start() - 120) : match.end() + 30]
        ):
            raise PostReleaseRoadmapBlockedError(
                "The roadmap contains an approval or completion claim."
            )


def _markdown_items(items: list[Any]) -> list[str]:
    return [
        f"- **{sanitize_post_release_roadmap_value(item.title)}** — "
        f"{sanitize_post_release_roadmap_value(item.summary)} Next: "
        f"{sanitize_post_release_roadmap_value(item.next_step)}"
        for item in items
    ]


def render_post_release_roadmap_report_markdown(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    lines = [
        "# Post-release roadmap report (J10)",
        "",
        f"- Status: `{report.status.value}`",
        f"- Decision: `{report.decision.value}`",
        f"- Target version: `{report.target_version}`",
        f"- Roadmap domains: {len(report.domain_summaries)}",
        f"- Known limitations: {report.known_limitations_total}",
        f"- Future-work items: {len(report.future_work_backlog)}",
        "- Planning only: yes",
        "- Actual release performed: false",
        "- Package/Docker build, publish, tag, release, deploy, and docs deploy attempted: false",
        "- GitHub API, issue/ticket creation, package registry, Procore, cloud, and external calls attempted: false",
        "- Maintainer decision required: true",
        "- Private review required: true",
        "",
        "This report plans work for after a future human-approved 0.1.0 release. It does not claim a release, approval, publication, deployment, hosted availability, certification, or compliance.",
        "",
        "## What is not in 0.1.0",
        "",
        "- Production/Pilot/release/deployment approval, live validation, and customer onboarding decisions.",
        "- Notifications, full audit logging, retention enforcement, app-level encryption behavior, or privacy/legal compliance claims.",
        "- Hosted UI implementation, API hardening, release automation, documentation hosting, or external integrations.",
        "",
        "## Domain review",
        "",
    ]
    lines.extend(
        f"- `{item.domain.value}` — `{item.status.value}` — {sanitize_post_release_roadmap_value(item.summary)}"
        for item in report.domain_summaries
    )
    lines.extend(
        (
            "",
            "See the focused registers for limitations, future work, private review, and pre-tag reminders.",
            "",
        )
    )
    return "\n".join(lines)


def render_known_limitations_register_markdown(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    return "\n".join(
        [
            "# Known limitations register (J10)",
            "",
            "Planning only for after a future human-approved 0.1.0 release; no actual release happened.",
            "Maintainer review and private review remain required. No release, build, publish, tag, deploy, issue, ticket, or approval action occurs here.",
            "",
            *(
                f"- **{item.title}** (`{item.category.value}`): {item.summary} Next: {item.next_step}"
                for item in report.known_limitations
            ),
            "",
        ]
    )


def render_future_work_backlog_markdown(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    return "\n".join(
        [
            "# Future work backlog (J10)",
            "",
            "Uncommitted planning candidates for after a future human-approved 0.1.0 release. No issue or ticket is created; no work is assigned or approved.",
            "",
            *_markdown_items(report.future_work_backlog),
            "",
        ]
    )


def render_private_review_backlog_markdown(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    return "\n".join(
        [
            "# Private review backlog (J10)",
            "",
            "Placeholder-only planning for authorized private review. Keep reports, identities, credentials, domains, paths, logs, and approval records outside Git.",
            "No release, build, publish, tag, deploy, issue, ticket, or approval action occurs here.",
            "",
            *_markdown_items(report.private_review_backlog),
            "",
        ]
    )


def render_pre_tag_reminder_checklist_markdown(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    lines = [
        "# Pre-tag reminder checklist (J10)",
        "",
        "Manual reminders for a future human maintainer; this checklist never tags or releases.",
        "Post-release means after a future human-approved 0.1.0 release. No release, build, publish, tag, deploy, issue, ticket, or approval occurred in J10.",
        "",
    ]
    lines.extend(f"- [ ] {item.description}" for item in report.pre_tag_reminders)
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_post_release_roadmap_value(value)
    return f"'{text}" if text[:1] in "=+-@" else text


def render_post_release_roadmap_matrix_csv(report: PostReleaseRoadmapReport) -> str:
    validate_post_release_roadmap_report_safe(report)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ("domain", "status", "priority", "timeframe", "summary", "known_limitation", "next_step")
    )
    for item in report.roadmap_matrix:
        writer.writerow(
            (
                _csv_cell(item.domain.value),
                _csv_cell(item.status.value),
                _csv_cell(item.priority.value),
                _csv_cell(item.timeframe.value),
                _csv_cell(item.summary),
                _csv_cell(item.known_limitation),
                _csv_cell(item.next_step),
            )
        )
    return output.getvalue()


def _safe_output_root(output_root: Path) -> Path:
    candidate = Path(output_root)
    if candidate.is_absolute():
        normalized = candidate.resolve()
        if any(str(normalized).startswith(prefix) for prefix in TMP_PREFIXES):
            return normalized
        raise PostReleaseRoadmapBlockedError("Artifact output must use an approved temporary root.")
    if candidate.parts and candidate.parts[0] in {".", ""}:
        parts = candidate.parts[1:]
    else:
        parts = candidate.parts
    if len(parts) != 1 or parts[0] not in SAFE_ROOT_NAMES:
        raise PostReleaseRoadmapBlockedError(
            "Artifact output path is not an approved roadmap root."
        )
    return candidate


def write_post_release_roadmap_artifacts(
    report: PostReleaseRoadmapReport, output_root: Path
) -> PostReleaseRoadmapArtifactResult:
    validate_post_release_roadmap_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {
        "post-release-roadmap-report.json": report.model_dump_json(indent=2) + "\n",
        "post-release-roadmap-report.md": render_post_release_roadmap_report_markdown(report),
        "known-limitations-register.md": render_known_limitations_register_markdown(report),
        "future-work-backlog.md": render_future_work_backlog_markdown(report),
        "private-review-backlog.md": render_private_review_backlog_markdown(report),
        "pre-tag-reminder-checklist.md": render_pre_tag_reminder_checklist_markdown(report),
        "post-release-roadmap-matrix.csv": render_post_release_roadmap_matrix_csv(report),
    }
    manifest = {
        "status": report.status.value,
        "target_version": report.target_version,
        "files": [*ARTIFACT_FILES[:-1]],
        "sanitized": True,
        "planning_only": True,
        "live_operations": False,
        "release": False,
        "build": False,
        "publish": False,
        "tag": False,
        "deploy": False,
        "issue_creation": False,
        "ticket_creation": False,
    }
    files["manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    return PostReleaseRoadmapArtifactResult(
        status=report.status,
        output_directory=str(root),
        files=list(files),
    )
