"""Offline, public-safe handoff preparation for the target 0.1.0 metadata.

This module only reads repository text and writes explicitly requested local
artifacts.  It never builds, tags, publishes, releases, deploys, or calls an
external service.
"""

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.versioned_release_handoff import (
    IncludedScopeCategory,
    KnownLimitationCategory,
    KnownLimitationItem,
    MaintainerDecisionChecklistItem,
    PostReleaseChecklistItem,
    ReleaseEvidenceMatrixItem,
    ReleaseNoteCategory,
    ReleaseNoteItem,
    ReleaseScopeItem,
    VersionedReleaseArtifactResult,
    VersionedReleaseDomain,
    VersionedReleaseDomainSummary,
    VersionedReleaseFinding,
    VersionedReleaseGate,
    VersionedReleaseGateStatus,
    VersionedReleaseHandoffDecision,
    VersionedReleaseHandoffReport,
    VersionedReleaseHandoffStatus,
)
from app.services.api_docs_review import sanitize_api_docs_value


class VersionedReleaseHandoffError(ValueError):
    pass


class VersionedReleaseHandoffBlockedError(VersionedReleaseHandoffError):
    pass


REQUIRED_CONTROLS = (
    "versioned_release_handoff_require_rc_review",
    "versioned_release_handoff_require_release_notes_draft",
    "versioned_release_handoff_require_included_scope",
    "versioned_release_handoff_require_known_limitations",
    "versioned_release_handoff_require_maintainer_decision",
    "versioned_release_handoff_require_no_build",
    "versioned_release_handoff_require_no_publish",
    "versioned_release_handoff_require_no_tag",
    "versioned_release_handoff_require_no_release",
    "versioned_release_handoff_require_no_deploy",
    "versioned_release_handoff_require_no_workflow_changes",
)
ALLOW_SETTINGS = (
    "versioned_release_handoff_allow_real_identities",
    "versioned_release_handoff_allow_real_domains",
    "versioned_release_handoff_allow_real_urls",
    "versioned_release_handoff_allow_report_contents",
    "versioned_release_handoff_allow_private_paths",
)
REQUIRED_IGNORES = (
    "versioned-release-handoff-output/",
    "versioned-release-output/",
    "release-handoff-output/",
    "release-notes-draft-output/",
    "post-release-checklist-output/",
    "*.versioned-release-handoff-report.json",
    "*.versioned-release-handoff-report.md",
    "*.release-notes-draft.md",
    "*.maintainer-release-decision-checklist.md",
    "*.post-release-checklist.md",
    "*.release-evidence-matrix.csv",
    "*.release-scope-summary.md",
)
ARTIFACT_FILES = (
    "versioned-release-handoff-report.json",
    "versioned-release-handoff-report.md",
    "release-notes-draft.md",
    "release-scope-summary.md",
    "maintainer-release-decision-checklist.md",
    "post-release-checklist.md",
    "release-evidence-matrix.csv",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "versioned-release-handoff-output",
    "versioned-release-output",
    "release-handoff-output",
    "release-notes-draft-output",
    "post-release-checklist-output",
}
REPOSITORY_FILES = (
    "app/version.py",
    "pyproject.toml",
    "CHANGELOG.md",
    "README.md",
    "QUICKSTART.md",
    "Makefile",
    ".gitignore",
    "mkdocs.yml",
    "docs/project-status.md",
    "docs/roadmap.md",
    "docs/release-readiness.md",
    "docs/final-public-readiness.md",
    "docs/version-prep-review.md",
    "docs/release-candidate-review.md",
    "docs/release-candidate-checklist.md",
    "docs/release-candidate-gap-register.md",
    "docs/package-metadata-summary.md",
    "docs/setup-experience-review.md",
    "docs/demo-data-seed-reset.md",
    "docs/api-docs-review.md",
    "docs/hosted-ui-preparation.md",
    "docs/docs-site-polish.md",
    "docs/final-security-readiness-review.md",
    "docs/security-gap-closeout.md",
    "scripts/audit_public_safety.py",
    "scripts/audit_routes_read_only.py",
    "scripts/audit_public_usability.py",
    "scripts/check_docs_site.py",
)
SEMANTIC_VERSION_PATTERN = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
UNSAFE_MAKE_TARGET_PATTERN = re.compile(
    r"(?m)^(?:build|docker-build|package-build|publish|tag|release|deploy)\s*:"
)
UNSAFE_COMMAND_PATTERN = re.compile(
    r"(?i)(?:python\s+-m\s+build|docker\s+(?:build|push)|git\s+tag|"
    r"(?:^|\s)make\s+(?:publish|deploy|tag|release)(?:\s|$)|twine\s+upload|"
    r"gh\s+release|pip\s+upload)"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:actual|this|the)\s+(?:package\s+)?release\s+(?:was|has been|is)\s+"
    r"(?:performed|complete|completed|published|created)|"
    r"\b(?:actual\s+)?release\s+(?:happened|occurred)\b|"
    r"\b(?:package|docker(?:\s+image)?)\s+build\s+(?:happened|occurred|was performed|completed)\b|"
    r"\b(?:production|launch|pilot|release|deployment)\s+approved\b|"
    r"\b(?:production|release|pilot|deployment)\s+approval\s+(?:granted|complete)\b|"
    r"\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:package|version)\s+(?:(?:is|was|has been)\s+)?published\b|"
    r"\b(?:publish|tag|git tag|deploy(?:ment)?)\s+(?:happened|occurred)\b|"
    r"\b(?:tag|git tag)\s+(?:was|has been|is)\s+(?:created|pushed)\b|"
    r"\b(?:procore\s+(?:endorsed|partner|certified|officially supported))\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance|privacy)\s+certified\b"
)
NEGATED_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:not|no|does not|do not|never|without|cannot|isn't|is not|"
    r"doesn't|out of scope|requires separate|prepared|unreleased|later|manual)\b"
)


def sanitize_versioned_release_value(value: Any) -> str:
    """Return a bounded, public-safe scalar for reports and CSV cells."""

    return sanitize_api_docs_value(value)


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _read(path: str | Path) -> str:
    candidate = Path(path)
    try:
        return candidate.read_text(encoding="utf-8") if candidate.is_file() else ""
    except (OSError, UnicodeError):
        return ""


def _validate_settings(settings: Settings) -> str:
    if not _setting(settings, "versioned_release_handoff_enabled", True):
        raise VersionedReleaseHandoffBlockedError("Versioned release handoff is disabled.")
    if not _setting(settings, "versioned_release_handoff_fail_closed", True):
        raise VersionedReleaseHandoffBlockedError(
            "Versioned release handoff must remain fail closed."
        )
    if not all(bool(_setting(settings, name, True)) for name in REQUIRED_CONTROLS):
        raise VersionedReleaseHandoffBlockedError("A required release handoff control is disabled.")
    if any(bool(_setting(settings, name, False)) for name in ALLOW_SETTINGS):
        raise VersionedReleaseHandoffBlockedError("Unsafe release handoff material is enabled.")
    target = str(_setting(settings, "versioned_release_handoff_target_version", "0.1.0"))
    if not SEMANTIC_VERSION_PATTERN.fullmatch(target) or target != "0.1.0":
        raise VersionedReleaseHandoffBlockedError("The versioned release target must be 0.1.0.")
    return target


def build_versioned_release_dependencies(settings: Settings) -> dict[str, bool]:
    _validate_settings(settings)
    dependencies = {path: Path(path).is_file() for path in REPOSITORY_FILES}
    dependencies["release_candidate_review"] = all(
        Path(path).is_file()
        for path in (
            "docs/release-candidate-review.md",
            "docs/release-candidate-checklist.md",
            "docs/release-candidate-gap-register.md",
        )
    )
    workflow_root = Path(".github/workflows")
    dependencies["workflows_unchanged"] = (
        not any(
            path.is_file() and UNSAFE_COMMAND_PATTERN.search(_read(path))
            for path in workflow_root.glob("*")
        )
        if workflow_root.is_dir()
        else True
    )
    dependencies["makefile_safe"] = not UNSAFE_MAKE_TARGET_PATTERN.search(_read("Makefile"))
    dependencies["generated_ignores"] = all(
        item in _read(".gitignore") for item in REQUIRED_IGNORES
    )
    return dependencies


def _gate_status(passed: bool, *, private_review: bool = False) -> VersionedReleaseGateStatus:
    if not passed:
        return VersionedReleaseGateStatus.BLOCKED
    return (
        VersionedReleaseGateStatus.NEEDS_REVIEW
        if private_review
        else VersionedReleaseGateStatus.PASS
    )


def build_versioned_release_domain_summaries(
    settings: Settings,
) -> list[VersionedReleaseDomainSummary]:
    target = _validate_settings(settings)
    docs = {path: _read(path) for path in REPOSITORY_FILES}
    all_text = "\n".join(docs.values()).casefold()
    dependencies = build_versioned_release_dependencies(settings)
    changelog = docs["CHANGELOG.md"]
    version_source = docs["app/version.py"]
    pyproject = docs["pyproject.toml"]
    makefile = docs["Makefile"]
    gitignore = docs[".gitignore"]
    workflow_root = Path(".github/workflows")
    workflow_changed = (
        any(
            p.is_file() and UNSAFE_COMMAND_PATTERN.search(_read(p)) for p in workflow_root.glob("*")
        )
        if workflow_root.is_dir()
        else False
    )
    no_release_language = all(
        phrase in all_text
        for phrase in ("no package", "no publish", "no tag", "no release", "no deploy")
    )
    expected_targets = (
        "versioned-release-handoff",
        "release-notes-draft",
        "release-scope-summary",
        "maintainer-release-decision-checklist",
        "post-release-checklist",
        "versioned-release-artifact-check",
    )
    make_targets_present = all(f"{target_name}:" in makefile for target_name in expected_targets)
    rows = (
        (
            VersionedReleaseDomain.RELEASE_CANDIDATE_REVIEW,
            dependencies["release_candidate_review"],
            "J7 release-candidate review exists.",
            "docs/release-candidate-review.md",
            False,
        ),
        (
            VersionedReleaseDomain.VERSION_METADATA,
            target in version_source and target in pyproject,
            "0.1.0 appears in the local version sources.",
            "app/version.py and pyproject.toml",
            False,
        ),
        (
            VersionedReleaseDomain.PACKAGE_METADATA,
            dependencies["pyproject.toml"] and dependencies["docs/package-metadata-summary.md"],
            "Package metadata is documented without a build.",
            "pyproject.toml and package metadata summary",
            False,
        ),
        (
            VersionedReleaseDomain.LOCAL_SETUP,
            dependencies["docs/setup-experience-review.md"] and dependencies["QUICKSTART.md"],
            "Local setup and quickstart guidance are present.",
            "J1 setup docs",
            False,
        ),
        (
            VersionedReleaseDomain.DEMO_EXPERIENCE,
            dependencies["docs/demo-data-seed-reset.md"],
            "Deterministic local Demo guidance is present.",
            "J2 Demo docs",
            False,
        ),
        (
            VersionedReleaseDomain.API_DOCUMENTATION,
            dependencies["docs/api-docs-review.md"]
            and dependencies["scripts/audit_routes_read_only.py"],
            "Offline API and route-boundary documentation is present.",
            "J3 API docs and route audit",
            False,
        ),
        (
            VersionedReleaseDomain.HOSTED_UI_PREPARATION,
            dependencies["docs/hosted-ui-preparation.md"],
            "Hosted UI preparation remains documentation only.",
            "J4 hosted UI docs",
            True,
        ),
        (
            VersionedReleaseDomain.DOCS_SITE,
            dependencies["docs/docs-site-polish.md"] and dependencies["mkdocs.yml"],
            "Local docs-site navigation guidance is present.",
            "J5 docs-site docs",
            False,
        ),
        (
            VersionedReleaseDomain.SECURITY_READINESS,
            dependencies["docs/final-security-readiness-review.md"]
            and dependencies["docs/security-gap-closeout.md"],
            "Public security readiness is documented; private review remains separate.",
            "I8/I9 security docs",
            True,
        ),
        (
            VersionedReleaseDomain.PUBLIC_SAFETY,
            dependencies["scripts/audit_public_safety.py"]
            and dependencies["scripts/audit_public_usability.py"],
            "Public-safety and usability audits are local-only.",
            "H1/H2 audit scripts",
            False,
        ),
        (
            VersionedReleaseDomain.ROUTE_BOUNDARY,
            dependencies["scripts/audit_routes_read_only.py"],
            "Route audit remains read-only and local.",
            "scripts/audit_routes_read_only.py",
            False,
        ),
        (
            VersionedReleaseDomain.GENERATED_OUTPUT_BOUNDARY,
            all(item in gitignore for item in REQUIRED_IGNORES),
            "Handoff output patterns are ignored.",
            ".gitignore",
            False,
        ),
        (
            VersionedReleaseDomain.CHANGELOG,
            target in changelog and "not" in changelog.casefold(),
            "Changelog records prepared metadata and no actual release.",
            "CHANGELOG.md",
            False,
        ),
        (
            VersionedReleaseDomain.KNOWN_LIMITATIONS,
            all(
                phrase in all_text
                for phrase in (
                    "private",
                    "production",
                    "notification",
                    "audit log",
                    "retention",
                    "encryption",
                    "privacy",
                )
            ),
            "Known limitations are retained for maintainer and private review.",
            "security and readiness docs",
            True,
        ),
        (
            VersionedReleaseDomain.MAINTAINER_DECISION,
            make_targets_present
            and no_release_language
            and not UNSAFE_MAKE_TARGET_PATTERN.search(makefile)
            and not workflow_changed,
            "Maintainer decision and safe command review remain manual.",
            "Makefile and local workflow inspection",
            True,
        ),
    )
    return [
        VersionedReleaseDomainSummary(
            domain=domain,
            status=_gate_status(passed, private_review=private_review),
            summary=summary,
            source=source,
            private_review_required=private_review,
        )
        for domain, passed, summary, source, private_review in rows
    ]


def build_versioned_release_gates(settings: Settings) -> list[VersionedReleaseGate]:
    return [
        VersionedReleaseGate(
            code=f"{item.domain.value}_gate",
            domain=item.domain,
            status=item.status,
            description=item.summary,
            evidence=[item.source],
        )
        for item in build_versioned_release_domain_summaries(settings)
    ]


def build_release_notes_draft(settings: Settings) -> list[ReleaseNoteItem]:
    target = _validate_settings(settings)
    return [
        ReleaseNoteItem(
            category=ReleaseNoteCategory.HIGHLIGHT,
            title=f"Prepared {target} handoff",
            summary=(
                "Versioned release metadata and an offline maintainer handoff are prepared; "
                "0.1.0 is not released."
            ),
        ),
        ReleaseNoteItem(
            category=ReleaseNoteCategory.SETUP,
            title="Local setup and Demo path",
            summary=(
                "J1/J2 local setup, fake Demo data, and reset guidance remain available "
                "without external calls."
            ),
        ),
        ReleaseNoteItem(
            category=ReleaseNoteCategory.DOCUMENTATION,
            title="Documentation and route reference",
            summary="J3-J5 add local API, hosted UI preparation, and docs-site review guidance.",
        ),
        ReleaseNoteItem(
            category=ReleaseNoteCategory.SECURITY,
            title="Public security boundaries",
            summary=(
                "I-series security and privacy guidance is documented for separate private review."
            ),
        ),
        ReleaseNoteItem(
            category=ReleaseNoteCategory.BOUNDARY,
            title="Manual release boundary",
            summary=(
                "J6/J7/J8 perform no build, publish, tag, release, deploy, workflow change, "
                "or external call."
            ),
        ),
        ReleaseNoteItem(
            category=ReleaseNoteCategory.LIMITATION,
            title="Known limitations remain",
            summary=(
                "Production, Pilot, hosted, legal, privacy, encryption, and security approvals "
                "are not granted."
            ),
        ),
    ]


def build_release_scope_summary(settings: Settings) -> list[ReleaseScopeItem]:
    _validate_settings(settings)
    return [
        ReleaseScopeItem(
            category=IncludedScopeCategory.SETUP,
            phase="J1",
            title="Installer and setup review",
            summary="Local setup, first-run, troubleshooting, and command guidance.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.DEMO,
            phase="J2",
            title="Demo seed and reset",
            summary="Deterministic fake-data Demo planning and reset experience.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.API,
            phase="J3",
            title="API route reference",
            summary="Offline route and method documentation with read-only boundary review.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.HOSTED_UI,
            phase="J4",
            title="Hosted UI preparation",
            summary="Protected hosted-evaluation preparation without deployment or frontend build.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.DOCS,
            phase="J5",
            title="Docs site polish",
            summary="Local handbook navigation and reader paths without docs hosting.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.VERSION_METADATA,
            phase="J6",
            title="Version metadata and security inputs",
            summary="Prepared 0.1.0 metadata and public security/readiness inputs.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.RELEASE_REVIEW,
            phase="J7",
            title="Release-candidate checklist",
            summary="Offline candidate checklist, gaps, and safe command review.",
        ),
        ReleaseScopeItem(
            category=IncludedScopeCategory.SECURITY,
            phase="H/I",
            title="Public and security readiness inputs",
            summary=(
                "H-series public product polish and I-series security boundaries remain review "
                "inputs."
            ),
        ),
    ]


def build_known_limitations_summary(settings: Settings) -> list[KnownLimitationItem]:
    _validate_settings(settings)
    return [
        KnownLimitationItem(
            category=KnownLimitationCategory.PRIVATE_REVIEW,
            title="Private review remains required",
            summary=(
                "Authorized private security, infrastructure, legal, privacy, and maintainer "
                "review is outside this public handoff."
            ),
            next_step="Complete authorized private review separately.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.PRODUCTION_APPROVAL,
            title="No production approval",
            summary="This phase grants no production, Pilot, release, or deployment approval.",
            next_step="Obtain explicit maintainer and operational authorization.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.HOSTED_DEPLOYMENT,
            title="No hosted deployment",
            summary=(
                "No application, docs, package, image, or hosted service was deployed or published."
            ),
            next_step="Perform any later deployment through separately authorized procedures.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.NOTIFICATIONS,
            title="No notification system",
            summary="Notification delivery and customer communications are not included.",
            next_step="Design and authorize a notification workflow separately.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.AUDIT_LOG,
            title="No full audit log",
            summary=(
                "A complete production audit-log implementation is not included in this handoff."
            ),
            next_step="Review audit-log requirements privately before live use.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.RETENTION,
            title="No retention enforcement",
            summary=(
                "Retention policy guidance does not enforce production retention or purge behavior."
            ),
            next_step="Complete data-retention implementation and review separately.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.ENCRYPTION,
            title="No app-level encryption",
            summary="Application-level encryption is not claimed or granted by this phase.",
            next_step="Complete authorized encryption and key-management review separately.",
        ),
        KnownLimitationItem(
            category=KnownLimitationCategory.PRIVACY_LEGAL,
            title="No privacy/legal compliance claim",
            summary=(
                "This public handoff is not legal advice and makes no privacy, regulatory, or "
                "compliance claim."
            ),
            next_step="Obtain independent legal and privacy review.",
        ),
    ]


def build_maintainer_release_decision_checklist(
    settings: Settings,
) -> list[MaintainerDecisionChecklistItem]:
    _validate_settings(settings)
    rows = (
        (
            "review_rc",
            "Review the J7 release-candidate checklist and resolve any open findings.",
            VersionedReleaseDomain.RELEASE_CANDIDATE_REVIEW,
        ),
        (
            "confirm_version",
            "Confirm 0.1.0 metadata and changelog wording are intentional.",
            VersionedReleaseDomain.VERSION_METADATA,
        ),
        (
            "review_notes",
            "Review and edit the release notes draft for the public repository.",
            VersionedReleaseDomain.CHANGELOG,
        ),
        (
            "review_scope",
            "Confirm the included-scope summary accurately describes J1-J7/H/I inputs.",
            VersionedReleaseDomain.MAINTAINER_DECISION,
        ),
        (
            "review_limitations",
            "Confirm known limitations and private-review requirements are explicit.",
            VersionedReleaseDomain.KNOWN_LIMITATIONS,
        ),
        (
            "check_boundaries",
            (
                "Confirm no build, publish, tag, release, deploy, workflow, or external "
                "operation occurred."
            ),
            VersionedReleaseDomain.PUBLIC_SAFETY,
        ),
        (
            "authorize_release",
            "Make an explicit maintainer decision before any later release action.",
            VersionedReleaseDomain.MAINTAINER_DECISION,
        ),
    )
    return [
        MaintainerDecisionChecklistItem(
            code=code, description=description, domain=domain, evidence="Local-only J8 handoff"
        )
        for code, description, domain in rows
    ]


def build_post_release_checklist(settings: Settings) -> list[PostReleaseChecklistItem]:
    _validate_settings(settings)
    rows = (
        (
            "record_decision",
            (
                "Record the maintainer release decision and authorization outside this generated "
                "report."
            ),
        ),
        (
            "review_artifacts",
            "Review any later artifacts in an authorized, private release environment.",
        ),
        (
            "verify_publishing",
            (
                "If separately authorized, verify package, tag, release, and deployment results "
                "through their own controls."
            ),
        ),
        (
            "verify_docs",
            (
                "If separately authorized, verify docs hosting and links without adding "
                "credentials or private values here."
            ),
        ),
        (
            "monitor_boundaries",
            (
                "Retain security, privacy, retention, audit-log, rollback, and incident-response "
                "follow-up."
            ),
        ),
    )
    return [
        PostReleaseChecklistItem(code=code, description=description) for code, description in rows
    ]


def build_release_evidence_matrix(settings: Settings) -> list[ReleaseEvidenceMatrixItem]:
    summaries = build_versioned_release_domain_summaries(settings)
    return [
        ReleaseEvidenceMatrixItem(
            domain=item.domain,
            gate_status=item.status,
            evidence=item.source,
            included_scope="Included in this offline handoff input.",
            limitation="Private or maintainer review remains required."
            if item.private_review_required
            else "No live operation is represented.",
            next_step="Complete the documented review gate before any later decision.",
        )
        for item in summaries
    ]


def build_versioned_release_handoff_report(settings: Settings) -> VersionedReleaseHandoffReport:
    target = _validate_settings(settings)
    dependencies = build_versioned_release_dependencies(settings)
    summaries = build_versioned_release_domain_summaries(settings)
    gates = build_versioned_release_gates(settings)
    notes = build_release_notes_draft(settings)
    scope = build_release_scope_summary(settings)
    limitations = build_known_limitations_summary(settings)
    maintainer = build_maintainer_release_decision_checklist(settings)
    post_release = build_post_release_checklist(settings)
    matrix = build_release_evidence_matrix(settings)
    findings: list[VersionedReleaseFinding] = []
    findings.extend(
        VersionedReleaseFinding(
            code=f"missing_{Path(name).stem}",
            message="A required local release-handoff dependency is missing.",
            severity="blocker",
            source=name,
        )
        for name, present in dependencies.items()
        if not present
    )
    findings.extend(
        VersionedReleaseFinding(
            code=f"{item.domain.value}_{item.status.value}",
            message=item.summary,
            severity="blocker"
            if item.status
            in {VersionedReleaseGateStatus.BLOCKED, VersionedReleaseGateStatus.MISSING}
            else "warning",
            domain=item.domain,
            source=item.source,
        )
        for item in summaries
        if item.status is not VersionedReleaseGateStatus.PASS
    )
    maximum = int(_setting(settings, "versioned_release_handoff_max_findings", 400))
    if len(findings) > maximum:
        raise VersionedReleaseHandoffBlockedError(
            "Release handoff findings exceed the configured limit."
        )
    blockers = [item.message for item in findings if item.severity == "blocker"]
    warnings = [item.message for item in findings if item.severity == "warning"]
    status = (
        VersionedReleaseHandoffStatus.BLOCKED
        if blockers
        else VersionedReleaseHandoffStatus.NEEDS_REVIEW
        if warnings
        else VersionedReleaseHandoffStatus.READY
    )
    decision = (
        VersionedReleaseHandoffDecision.BLOCKED
        if blockers
        else VersionedReleaseHandoffDecision.NEEDS_REVIEW
        if warnings
        else VersionedReleaseHandoffDecision.READY_FOR_MAINTAINER_DECISION
    )
    report = VersionedReleaseHandoffReport(
        status=status,
        decision=decision,
        target_version=target,
        dependencies=dependencies,
        domain_summaries=summaries,
        gates=gates,
        release_notes=notes,
        included_scope=scope,
        known_limitations=limitations,
        maintainer_decision_checklist=maintainer,
        post_release_checklist=post_release,
        release_evidence_matrix=matrix,
        domains_total=len(summaries),
        domains_passed=sum(item.status is VersionedReleaseGateStatus.PASS for item in summaries),
        domains_needing_review=sum(
            item.status is VersionedReleaseGateStatus.NEEDS_REVIEW for item in summaries
        ),
        domains_blocked=sum(
            item.status in {VersionedReleaseGateStatus.BLOCKED, VersionedReleaseGateStatus.MISSING}
            for item in summaries
        ),
        gates_total=len(gates),
        gates_passed=sum(item.status is VersionedReleaseGateStatus.PASS for item in gates),
        gates_needing_review=sum(
            item.status is VersionedReleaseGateStatus.NEEDS_REVIEW for item in gates
        ),
        findings=findings,
        blockers=blockers,
        warnings=warnings,
        release_notes_items_total=len(notes),
        included_scope_items_total=len(scope),
        known_limitations_total=len(limitations),
        maintainer_decision_items_total=len(maintainer),
        post_release_items_total=len(post_release),
        public_repo_safe_for_release_handoff=not blockers,
        recommended_next_steps=[
            "Review this offline handoff with the maintainer.",
            (
                "Complete private security, privacy, legal, infrastructure, and operational "
                "review separately."
            ),
            "Do not build, publish, tag, release, deploy, or change workflows from J8.",
        ],
    )
    validate_versioned_release_handoff_report_safe(report)
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


def validate_versioned_release_handoff_report_safe(report: VersionedReleaseHandoffReport) -> None:
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
        report.package_registry_call_attempted,
        report.external_call_attempted,
        report.procore_call_attempted,
        report.cloud_call_attempted,
        report.db_external_connection_attempted,
        report.scanner_attempted,
        report.production_approval_granted,
        report.release_approval_granted,
        report.pilot_approval_granted,
        report.deployment_approval_granted,
        report.package_publication_claimed,
        report.docs_hosting_claimed,
        report.private_report_contents_exposed,
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
    )
    if any(unsafe_flags) or not report.public_repo_safe_for_release_handoff or report.blockers:
        raise VersionedReleaseHandoffBlockedError("The versioned release handoff failed closed.")
    if not report.maintainer_authorization_required or not report.private_review_required:
        raise VersionedReleaseHandoffBlockedError(
            "Maintainer authorization and private review must remain required."
        )
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_versioned_release_value(value) == "[redacted]":
            raise VersionedReleaseHandoffBlockedError("The handoff contains unsafe material.")
        for match in UNSAFE_COMMAND_PATTERN.finditer(value):
            raise VersionedReleaseHandoffBlockedError("The handoff contains an unsafe command.")
        for match in UNSAFE_CLAIM_PATTERN.finditer(value):
            window = value[max(0, match.start() - 120) : match.end() + 30]
            if not NEGATED_CLAIM_PATTERN.search(window):
                raise VersionedReleaseHandoffBlockedError(
                    "The handoff contains an approval or release claim."
                )


def render_versioned_release_handoff_report_markdown(report: VersionedReleaseHandoffReport) -> str:
    validate_versioned_release_handoff_report_safe(report)
    return "\n".join(
        (
            "# Versioned 0.1.0 release handoff",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Prepared target version: `{report.target_version}`",
            f"- Domains passed: {report.domains_passed}/{report.domains_total}",
            f"- Domains needing review: {report.domains_needing_review}",
            "- Maintainer authorization required: true",
            "- Private review required: true",
            "- Actual release performed: false",
            "- Package/Docker build, publish, tag, release, deploy, and docs deploy attempted: "
            "false",
            "",
            (
                "0.1.0 is prepared as release metadata, not released by this phase. Actual tag, "
                "release, publish, and deploy steps are outside J8 and require maintainer "
                "authorization."
            ),
            "Maintainer authorization is still required.",
            (
                "Production, Pilot, hosted, legal, privacy, security, and deployment approvals "
                "are not granted."
            ),
            "",
        )
    )


def render_release_notes_draft_markdown(report: VersionedReleaseHandoffReport) -> str:
    validate_versioned_release_handoff_report_safe(report)
    lines = [
        f"# Release notes draft — {report.target_version}",
        "",
        "Prepared metadata only; this draft does not claim an actual release.",
        "",
    ]
    for item in report.release_notes:
        lines.extend((f"## {item.title}", "", item.summary, ""))
    return "\n".join(lines)


def render_release_scope_summary_markdown(report: VersionedReleaseHandoffReport) -> str:
    validate_versioned_release_handoff_report_safe(report)
    lines = [
        f"# What is included in {report.target_version}",
        "",
        "This is a public-safe scope summary for maintainer review; it is not release approval.",
        "",
        "| Phase | Area | Summary |",
        "| --- | --- | --- |",
    ]
    for item in report.included_scope:
        lines.append(
            "| " + " | ".join((item.phase, item.title, item.summary.replace("|", "\\|"))) + " |"
        )
    return "\n".join(lines) + "\n"


def render_maintainer_release_decision_checklist_markdown(
    report: VersionedReleaseHandoffReport,
) -> str:
    validate_versioned_release_handoff_report_safe(report)
    lines = [
        "# Maintainer release decision checklist",
        "",
        "A maintainer must decide separately; no release is performed here.",
        "",
    ]
    lines.extend(f"- [ ] {item.description}" for item in report.maintainer_decision_checklist)
    return "\n".join(lines) + "\n"


def render_post_release_checklist_markdown(report: VersionedReleaseHandoffReport) -> str:
    validate_versioned_release_handoff_report_safe(report)
    lines = [
        "# Safe post-release checklist",
        "",
        "Use only after separate authorization. J8 performs no post-release operation.",
        "",
    ]
    lines.extend(f"- [ ] {item.description}" for item in report.post_release_checklist)
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_versioned_release_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_release_evidence_matrix_csv(report: VersionedReleaseHandoffReport) -> str:
    validate_versioned_release_handoff_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        ("domain", "gate_status", "evidence", "included_scope", "limitation", "next_step")
    )
    for item in report.release_evidence_matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.domain.value,
                    item.gate_status.value,
                    item.evidence,
                    item.included_scope,
                    item.limitation,
                    item.next_step,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if raw.is_absolute() or ".." in raw.parts:
        allowed_tmp = str(raw.resolve()).startswith(
            (
                "/tmp/procore-intake-bridge-versioned-release-",
                "/private/tmp/procore-intake-bridge-versioned-release-",
            )
        )
        if not allowed_tmp:
            raise VersionedReleaseHandoffBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        (
            "/tmp/procore-intake-bridge-versioned-release-",
            "/private/tmp/procore-intake-bridge-versioned-release-",
        )
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise VersionedReleaseHandoffBlockedError(
            "Output root is outside the release-handoff boundary."
        )
    return resolved


def write_versioned_release_handoff_artifacts(
    report: VersionedReleaseHandoffReport, output_root: str | Path
) -> VersionedReleaseArtifactResult:
    validate_versioned_release_handoff_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "versioned-release-handoff-report.json": json.dumps(
            report.model_dump(mode="json"), indent=2
        )
        + "\n",
        "versioned-release-handoff-report.md": render_versioned_release_handoff_report_markdown(
            report
        ),
        "release-notes-draft.md": render_release_notes_draft_markdown(report),
        "release-scope-summary.md": render_release_scope_summary_markdown(report),
        "maintainer-release-decision-checklist.md": (
            render_maintainer_release_decision_checklist_markdown(report)
        ),
        "post-release-checklist.md": render_post_release_checklist_markdown(report),
        "release-evidence-matrix.csv": render_release_evidence_matrix_csv(report),
        "manifest.json": json.dumps(
            {
                "status": report.status.value,
                "files": list(ARTIFACT_FILES[:-1]),
                "sanitized": True,
                "live_operations": False,
                "package_build": False,
                "docker_build": False,
                "publish": False,
                "tag": False,
                "release": False,
                "deploy": False,
            },
            indent=2,
        )
        + "\n",
    }
    for filename, contents in rendered.items():
        target = (root / filename).resolve()
        if target.parent != root:
            raise VersionedReleaseHandoffBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return VersionedReleaseArtifactResult(
        status=report.status, output_directory=root.name, files=list(ARTIFACT_FILES)
    )
