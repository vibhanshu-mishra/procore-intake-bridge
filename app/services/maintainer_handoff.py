# ruff: noqa: E501
"""Offline, public-safe maintainer handoff pack for Phase J9.

The service reads a small allow-list of repository files and creates review
material only.  It never performs release, build, publish, tag, deploy, or
network operations.  Generated output is explicitly sanitized and disposable.
"""

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.maintainer_handoff import (
    MaintainerCommandPlanItem,
    MaintainerDecisionLogItem,
    MaintainerHandoffArtifactResult,
    MaintainerHandoffDecision,
    MaintainerHandoffDomain,
    MaintainerHandoffDomainSummary,
    MaintainerHandoffFinding,
    MaintainerHandoffGate,
    MaintainerHandoffGateStatus,
    MaintainerHandoffMatrixItem,
    MaintainerHandoffReport,
    MaintainerHandoffStatus,
    MaintainerReviewChecklistItem,
)
from app.services.api_docs_review import sanitize_api_docs_value


class MaintainerHandoffError(ValueError):
    """Base error for unsafe or invalid handoff input."""


class MaintainerHandoffBlockedError(MaintainerHandoffError):
    """Raised whenever a fail-closed handoff condition is not satisfied."""


REQUIRED_CONTROLS = (
    "maintainer_handoff_require_release_handoff",
    "maintainer_handoff_require_safe_command_plan",
    "maintainer_handoff_require_private_review_boundary",
    "maintainer_handoff_require_no_release_actions",
    "maintainer_handoff_require_no_build",
    "maintainer_handoff_require_no_publish",
    "maintainer_handoff_require_no_tag",
    "maintainer_handoff_require_no_deploy",
)
ALLOW_SETTINGS = (
    "maintainer_handoff_allow_real_identities",
    "maintainer_handoff_allow_real_domains",
    "maintainer_handoff_allow_real_urls",
    "maintainer_handoff_allow_report_contents",
    "maintainer_handoff_allow_private_paths",
)

REPOSITORY_FILES = (
    "README.md",
    "QUICKSTART.md",
    "CHANGELOG.md",
    "Makefile",
    ".gitignore",
    "mkdocs.yml",
    "app/version.py",
    "docs/versioned-release-handoff.md",
    "docs/release-notes-draft.md",
    "docs/release-candidate-review.md",
    "docs/version-prep-review.md",
    "docs/docs-site-polish.md",
    "docs/hosted-ui-preparation.md",
    "docs/api-docs-review.md",
    "docs/demo-data-seed-reset.md",
    "docs/setup-experience-review.md",
    "docs/security-gap-closeout.md",
    "docs/final-security-readiness-review.md",
    "docs/project-status.md",
    "docs/roadmap.md",
    "scripts/audit_public_safety.py",
    "scripts/audit_routes_read_only.py",
    "scripts/audit_public_usability.py",
    "scripts/check_docs_site.py",
)

REQUIRED_IGNORES = (
    "maintainer-handoff-output/",
    "handoff-output/",
    "maintainer-review-output/",
    "release-handoff-review-output/",
    "*.maintainer-handoff-report.json",
    "*.maintainer-handoff-report.md",
    "*.maintainer-quickstart.md",
    "*.maintainer-review-checklist.md",
    "*.maintainer-command-plan.md",
    "*.maintainer-decision-log-template.md",
    "*.maintainer-handoff-matrix.csv",
)

ARTIFACT_FILES = (
    "maintainer-handoff-report.json",
    "maintainer-handoff-report.md",
    "maintainer-quickstart.md",
    "maintainer-review-checklist.md",
    "maintainer-command-plan.md",
    "maintainer-decision-log-template.md",
    "maintainer-handoff-matrix.csv",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "maintainer-handoff-output",
    "handoff-output",
    "maintainer-review-output",
    "release-handoff-review-output",
}
TMP_PREFIXES = (
    "/tmp/procore-intake-bridge-maintainer-handoff-",
    "/private/tmp/procore-intake-bridge-maintainer-handoff-",
)
SEMVER = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
UNSAFE_COMMAND = re.compile(
    r"(?i)(?:python\s+-m\s+build|docker\s+(?:build|push)|git\s+tag|"
    r"(?:^|\s)make\s+(?:publish|deploy|tag|release)(?:\s|$)|twine\s+upload|gh\s+release|pip\s+upload)"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:production|launch|pilot|release|deployment)\s+approved\b|"
    r"\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:package|version)\s+(?:is|was|has been)\s+published\b|"
    r"\b(?:tag|git tag)\s+(?:was|has been|is)\s+(?:created|pushed)\b|"
    r"\b(?:actual\s+)?release\s+(?:was|has been|is)\s+(?:performed|complete|completed|published|created)\b"
)
NEGATED_CLAIM = re.compile(
    r"(?i)\b(?:not|no|never|without|does not|do not|is not|isn't|out of scope|requires separate|unreleased|later|manual)\b"
)


def sanitize_maintainer_handoff_value(value: Any) -> str:
    """Return a bounded scalar with URLs, IDs, paths, and secrets redacted."""

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
    if not _setting(settings, "maintainer_handoff_enabled", True):
        raise MaintainerHandoffBlockedError("Maintainer handoff is disabled.")
    if not _setting(settings, "maintainer_handoff_fail_closed", True):
        raise MaintainerHandoffBlockedError("Maintainer handoff must remain fail closed.")
    if not all(bool(_setting(settings, key, True)) for key in REQUIRED_CONTROLS):
        raise MaintainerHandoffBlockedError("A required maintainer handoff control is disabled.")
    if any(bool(_setting(settings, key, False)) for key in ALLOW_SETTINGS):
        raise MaintainerHandoffBlockedError("Unsafe maintainer handoff material is enabled.")
    target = str(_setting(settings, "maintainer_handoff_target_version", "0.1.0"))
    if target != "0.1.0" or not SEMVER.fullmatch(target):
        raise MaintainerHandoffBlockedError("The maintainer handoff target must be 0.1.0.")
    return target


def build_maintainer_handoff_dependencies(settings: Settings) -> dict[str, bool]:
    _validate_settings(settings)
    dependencies = {path: Path(path).is_file() for path in REPOSITORY_FILES}
    dependencies["versioned_release_handoff"] = all(
        Path(path).is_file()
        for path in (
            "docs/versioned-release-handoff.md",
            "app/services/versioned_release_handoff.py",
            "app/schemas/versioned_release_handoff.py",
        )
    )
    dependencies["release_handoff"] = dependencies["versioned_release_handoff"]
    dependencies["release_handoff_dependency"] = dependencies["versioned_release_handoff"]
    dependencies["generated_output_ignores"] = all(
        item in _read(".gitignore") for item in REQUIRED_IGNORES
    )
    workflow_root = Path(".github/workflows")
    dependencies["workflows_unchanged"] = (
        not any(
            path.is_file() and UNSAFE_COMMAND.search(_read(path))
            for path in workflow_root.glob("*")
        )
        if workflow_root.is_dir()
        else True
    )
    return dependencies


def _status(passed: bool, private_review: bool = False) -> MaintainerHandoffGateStatus:
    if not passed:
        return MaintainerHandoffGateStatus.BLOCKED
    return (
        MaintainerHandoffGateStatus.NEEDS_REVIEW
        if private_review
        else MaintainerHandoffGateStatus.PASS
    )


def build_maintainer_handoff_domain_summaries(
    settings: Settings,
) -> list[MaintainerHandoffDomainSummary]:
    target = _validate_settings(settings)
    deps = build_maintainer_handoff_dependencies(settings)
    rows: tuple[tuple[MaintainerHandoffDomain, bool, str, str, bool], ...] = (
        (
            MaintainerHandoffDomain.REPOSITORY_OVERVIEW,
            deps["README.md"] and deps["CHANGELOG.md"] and deps["app/version.py"],
            "Repository purpose and the prepared 0.1.0 scope are summarized locally.",
            "README.md, CHANGELOG.md, app/version.py",
            False,
        ),
        (
            MaintainerHandoffDomain.LOCAL_SETUP,
            deps["QUICKSTART.md"] and deps["Makefile"],
            "Local setup and safe review commands are documented.",
            "QUICKSTART.md and Makefile",
            False,
        ),
        (
            MaintainerHandoffDomain.DEMO_MODE,
            deps["docs/demo-data-seed-reset.md"],
            "Demo Mode uses deterministic local fake data and reset guidance.",
            "docs/demo-data-seed-reset.md",
            False,
        ),
        (
            MaintainerHandoffDomain.API_DOCUMENTATION,
            deps["docs/api-docs-review.md"] and deps["scripts/audit_routes_read_only.py"],
            "API and route review remains a local, read-only reference.",
            "docs/api-docs-review.md and route audit",
            False,
        ),
        (
            MaintainerHandoffDomain.PRODUCT_UI,
            deps["docs/project-status.md"],
            "Product UI surfaces are documented for local review only.",
            "docs/project-status.md",
            False,
        ),
        (
            MaintainerHandoffDomain.HOSTED_PREPARATION,
            deps["docs/hosted-ui-preparation.md"],
            "Hosted UI preparation contains no deployment or hosted availability claim.",
            "docs/hosted-ui-preparation.md",
            True,
        ),
        (
            MaintainerHandoffDomain.SECURITY_READINESS,
            deps["docs/final-security-readiness-review.md"]
            and deps["scripts/audit_public_safety.py"],
            "Public security readiness inputs are documented; approval is separate.",
            "security review and safety audit",
            True,
        ),
        (
            MaintainerHandoffDomain.PRIVACY_SECURITY_GAPS,
            deps["docs/security-gap-closeout.md"],
            "Privacy, retention, encryption, and security gaps remain review inputs.",
            "docs/security-gap-closeout.md",
            True,
        ),
        (
            MaintainerHandoffDomain.RELEASE_HANDOFF,
            deps["versioned_release_handoff"],
            f"J8 release handoff for {target} is detected; no release action occurred.",
            "docs/versioned-release-handoff.md",
            True,
        ),
        (
            MaintainerHandoffDomain.KNOWN_LIMITATIONS,
            deps["docs/roadmap.md"] and deps["docs/project-status.md"],
            "Known limitations and later work remain explicit.",
            "docs/roadmap.md and project status",
            True,
        ),
        (
            MaintainerHandoffDomain.PRIVATE_REVIEW_BOUNDARY,
            deps["docs/security-gap-closeout.md"]
            and deps["docs/final-security-readiness-review.md"],
            "Private infrastructure, legal, privacy, and security review remains required.",
            "security readiness docs",
            True,
        ),
        (
            MaintainerHandoffDomain.MAINTAINER_DECISION,
            deps["Makefile"] and deps["docs/release-candidate-review.md"],
            "A human maintainer must decide what to do next.",
            "Makefile and J7 review",
            True,
        ),
        (
            MaintainerHandoffDomain.GENERATED_OUTPUT_BOUNDARY,
            deps[".gitignore"] and deps["generated_output_ignores"],
            "Generated handoff output is ignored and disposable.",
            ".gitignore",
            False,
        ),
        (
            MaintainerHandoffDomain.PUBLIC_SAFETY,
            deps["scripts/audit_public_safety.py"]
            and deps["scripts/audit_public_usability.py"]
            and deps["scripts/check_docs_site.py"],
            "Public-safety checks remain offline and do not claim approval.",
            "public audits and docs checker",
            False,
        ),
    )
    return [
        MaintainerHandoffDomainSummary(
            domain=domain,
            status=_status(passed, private_review),
            summary=summary,
            source=source,
            private_review_required=private_review,
        )
        for domain, passed, summary, source, private_review in rows
    ]


def build_maintainer_handoff_gates(settings: Settings) -> list[MaintainerHandoffGate]:
    return [
        MaintainerHandoffGate(
            code=f"{item.domain.value}_gate",
            domain=item.domain,
            status=item.status,
            description=item.summary,
            evidence=[item.source],
        )
        for item in build_maintainer_handoff_domain_summaries(settings)
    ]


def build_maintainer_quickstart(settings: Settings) -> list[str]:
    _validate_settings(settings)
    return [
        "Read README.md and QUICKSTART.md to understand the repository and local setup.",
        "Try Demo Mode with fixture-only data; do not add credentials or customer data.",
        "Run the safe read-only review commands in the maintainer command plan.",
        "Read the J8 versioned release handoff and confirm 0.1.0 is prepared, not released.",
        "Keep private reports, URLs, identities, IDs, paths, logs, and approval records outside the public repository.",
        "Record the maintainer decision separately; private review remains required before Sandbox, Pilot, Hosted, or live use.",
    ]


def build_maintainer_review_checklist(settings: Settings) -> list[MaintainerReviewChecklistItem]:
    _validate_settings(settings)
    rows = (
        (
            "understand_repository",
            "Confirm what this repository is and what 0.1.0 includes.",
            MaintainerHandoffDomain.REPOSITORY_OVERVIEW,
            False,
        ),
        (
            "try_demo_safely",
            "Try Demo Mode with fake local data only and confirm reset guidance.",
            MaintainerHandoffDomain.DEMO_MODE,
            False,
        ),
        (
            "review_setup_api_ui",
            "Review local setup, API documentation, product UI, and hosted preparation boundaries.",
            MaintainerHandoffDomain.LOCAL_SETUP,
            False,
        ),
        (
            "review_security_privacy",
            "Complete or reference private security, privacy, legal, and infrastructure review.",
            MaintainerHandoffDomain.PRIVACY_SECURITY_GAPS,
            True,
        ),
        (
            "confirm_release_boundary",
            "Confirm no build, publish, tag, release, deploy, docs deploy, or workflow change occurred.",
            MaintainerHandoffDomain.RELEASE_HANDOFF,
            True,
        ),
        (
            "confirm_public_safety",
            "Confirm generated output is ignored and no private values or report contents are committed.",
            MaintainerHandoffDomain.PUBLIC_SAFETY,
            False,
        ),
        (
            "make_decision",
            "Record whether the handoff needs review, is blocked, or is ready for a later authorized decision.",
            MaintainerHandoffDomain.MAINTAINER_DECISION,
            True,
        ),
    )
    return [
        MaintainerReviewChecklistItem(
            code=code,
            description=description,
            domain=domain,
            evidence="Local public-safe handoff material",
            private_review_required=private_review,
        )
        for code, description, domain, private_review in rows
    ]


SAFE_COMMANDS: tuple[tuple[str, str, MaintainerHandoffDomain, bool], ...] = (
    (
        "make quality",
        "Run the repository's local quality checks.",
        MaintainerHandoffDomain.PUBLIC_SAFETY,
        False,
    ),
    (
        "make safety-check",
        "Run the public-safety audit without external calls.",
        MaintainerHandoffDomain.PUBLIC_SAFETY,
        False,
    ),
    (
        "make docs-site-check",
        "Check local documentation navigation and links.",
        MaintainerHandoffDomain.API_DOCUMENTATION,
        False,
    ),
    (
        "make versioned-release-handoff",
        "Review the J8 0.1.0 handoff without releasing anything.",
        MaintainerHandoffDomain.RELEASE_HANDOFF,
        False,
    ),
    (
        "python scripts/run_maintainer_handoff.py",
        "Generate or print this J9 offline handoff review.",
        MaintainerHandoffDomain.MAINTAINER_DECISION,
        False,
    ),
    (
        "git diff --check",
        "Check working-tree whitespace before any maintainer decision.",
        MaintainerHandoffDomain.PUBLIC_SAFETY,
        False,
    ),
)

INCLUDED_SCOPE = [
    "Repository overview and prepared 0.1.0 metadata.",
    "Local setup guidance and safe review commands.",
    "Fixture-only Demo Mode and reset guidance.",
    "Offline API documentation, product UI review, and hosted preparation.",
    "Public security/readiness inputs and a concise maintainer decision aid.",
]
NOT_INCLUDED_SCOPE = [
    "No customer data, credentials, secrets, private reports, private paths, IDs, or live URLs.",
    "No package or container-image construction, publish, tag, release, docs hosting, or deployment.",
    "No production, Pilot, hosted, release, deployment, Procore, legal, privacy, or compliance approval.",
    "No network, GitHub API, package registry, cloud, database, scanner, or external service call.",
]


def build_maintainer_command_plan(settings: Settings) -> list[MaintainerCommandPlanItem]:
    _validate_settings(settings)
    items = [
        MaintainerCommandPlanItem(
            command=command,
            purpose=purpose,
            domain=domain,
            writes_generated_output=writes_output,
        )
        for command, purpose, domain, writes_output in SAFE_COMMANDS
    ]
    if any(UNSAFE_COMMAND.search(item.command) for item in items):
        raise MaintainerHandoffBlockedError("An unsafe command entered the maintainer plan.")
    return items


def build_maintainer_decision_log_template(settings: Settings) -> list[MaintainerDecisionLogItem]:
    _validate_settings(settings)
    rows = (
        ("scope_confirmed", "Does the public repository summary accurately describe 0.1.0?", False),
        (
            "safe_commands_confirmed",
            "Did the safe command plan remain offline and non-mutating?",
            False,
        ),
        (
            "private_review_confirmed",
            "Has authorized private review been completed or explicitly deferred?",
            True,
        ),
        ("next_action", "What should the maintainer do next, if anything?", False),
        (
            "release_authorization",
            "If a later release is considered, what separate authorization is required?",
            True,
        ),
    )
    return [
        MaintainerDecisionLogItem(
            code=code,
            question=question,
            domain=(
                MaintainerHandoffDomain.PRIVATE_REVIEW_BOUNDARY
                if private
                else MaintainerHandoffDomain.MAINTAINER_DECISION
            ),
            private_review_required=private,
        )
        for code, question, private in rows
    ]


def build_maintainer_handoff_matrix(settings: Settings) -> list[MaintainerHandoffMatrixItem]:
    summaries = build_maintainer_handoff_domain_summaries(settings)
    return [
        MaintainerHandoffMatrixItem(
            domain=item.domain,
            gate_status=item.status,
            evidence=item.source,
            included_scope="Public repository review material only.",
            not_included=(
                "Private review or live approval remains required."
                if item.private_review_required
                else "No release, build, publish, tag, or deploy action."
            ),
            next_step="Complete the documented maintainer review gate.",
        )
        for item in summaries
    ]


def build_maintainer_handoff_report(settings: Settings) -> MaintainerHandoffReport:
    target = _validate_settings(settings)
    dependencies = build_maintainer_handoff_dependencies(settings)
    summaries = build_maintainer_handoff_domain_summaries(settings)
    gates = build_maintainer_handoff_gates(settings)
    quickstart = build_maintainer_quickstart(settings)
    checklist = build_maintainer_review_checklist(settings)
    command_plan = build_maintainer_command_plan(settings)
    decision_log = build_maintainer_decision_log_template(settings)
    matrix = build_maintainer_handoff_matrix(settings)
    findings: list[MaintainerHandoffFinding] = [
        MaintainerHandoffFinding(
            code=f"missing_{Path(name).stem}",
            message="A required local maintainer-handoff dependency is missing.",
            severity="blocker",
            source=name,
        )
        for name, present in dependencies.items()
        if not present
    ]
    findings.extend(
        MaintainerHandoffFinding(
            code=f"{item.domain.value}_{item.status.value}",
            message=item.summary,
            severity="blocker"
            if item.status
            in {MaintainerHandoffGateStatus.BLOCKED, MaintainerHandoffGateStatus.MISSING}
            else "warning",
            domain=item.domain,
            source=item.source,
        )
        for item in summaries
        if item.status is not MaintainerHandoffGateStatus.PASS
    )
    maximum = int(_setting(settings, "maintainer_handoff_max_findings", 400))
    if len(findings) > maximum:
        raise MaintainerHandoffBlockedError(
            "Maintainer handoff findings exceed the configured limit."
        )
    blockers = [item.message for item in findings if item.severity == "blocker"]
    warnings = [item.message for item in findings if item.severity != "blocker"]
    status = (
        MaintainerHandoffStatus.BLOCKED
        if blockers
        else MaintainerHandoffStatus.NEEDS_REVIEW
        if warnings
        else MaintainerHandoffStatus.READY
    )
    decision = (
        MaintainerHandoffDecision.BLOCKED
        if blockers
        else MaintainerHandoffDecision.NEEDS_REVIEW
        if warnings
        else MaintainerHandoffDecision.READY_FOR_REVIEW
    )
    report = MaintainerHandoffReport(
        status=status,
        decision=decision,
        target_version=target,
        dependencies=dependencies,
        domain_summaries=summaries,
        gates=gates,
        quickstart=quickstart,
        included_scope=INCLUDED_SCOPE,
        not_included_scope=NOT_INCLUDED_SCOPE,
        review_checklist=checklist,
        command_plan=command_plan,
        decision_log_template=decision_log,
        handoff_matrix=matrix,
        findings=findings,
        blockers=blockers,
        warnings=warnings,
        domains_total=len(summaries),
        domains_passed=sum(item.status is MaintainerHandoffGateStatus.PASS for item in summaries),
        domains_needing_review=sum(
            item.status is MaintainerHandoffGateStatus.NEEDS_REVIEW for item in summaries
        ),
        domains_blocked=sum(
            item.status
            in {MaintainerHandoffGateStatus.BLOCKED, MaintainerHandoffGateStatus.MISSING}
            for item in summaries
        ),
        gates_total=len(gates),
        gates_passed=sum(item.status is MaintainerHandoffGateStatus.PASS for item in gates),
        gates_needing_review=sum(
            item.status is MaintainerHandoffGateStatus.NEEDS_REVIEW for item in gates
        ),
        checklist_items_total=len(checklist),
        command_plan_items_total=len(command_plan),
        decision_log_items_total=len(decision_log),
        matrix_items_total=len(matrix),
        public_repo_safe_for_handoff=not blockers,
        maintainer_decision_required=True,
        private_review_required=True,
        recommended_next_steps=[
            "Review this concise handoff with a human maintainer.",
            "Try Demo Mode safely with fake local data only.",
            "Complete private security, privacy, legal, infrastructure, and operational review separately.",
            "Do not perform any release, build, publish, tag, or deploy action from this handoff.",
        ],
    )
    validate_maintainer_handoff_report_safe(report)
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


def validate_maintainer_handoff_report_safe(report: MaintainerHandoffReport) -> None:
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
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
        report.package_publication_claimed,
        report.docs_hosting_claimed,
        report.private_report_contents_exposed,
    )
    if any(unsafe_flags) or not report.public_repo_safe_for_handoff or report.blockers:
        raise MaintainerHandoffBlockedError("The maintainer handoff failed closed.")
    if not report.maintainer_decision_required or not report.private_review_required:
        raise MaintainerHandoffBlockedError(
            "Maintainer decision and private review must remain required."
        )
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_maintainer_handoff_value(value) == "[redacted]":
            raise MaintainerHandoffBlockedError("The handoff contains unsafe material.")
        if UNSAFE_COMMAND.search(value):
            raise MaintainerHandoffBlockedError("The handoff contains an unsafe command.")
        match = UNSAFE_CLAIM.search(value)
        if match and not NEGATED_CLAIM.search(
            value[max(0, match.start() - 120) : match.end() + 30]
        ):
            raise MaintainerHandoffBlockedError(
                "The handoff contains an approval or release claim."
            )


def render_maintainer_handoff_report_markdown(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    return "\n".join(
        (
            "# Public maintainer handoff pack",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Target version: `{report.target_version}`",
            f"- Domains reviewed: {report.domains_passed}/{report.domains_total} passed; {report.domains_needing_review} need review",
            "- Maintainer decision required: true",
            "- Private review required: true",
            "- Actual release performed: false",
            "- Package/Docker build, publish, tag, release, deploy, and docs deploy attempted: false",
            "- GitHub, package registry, Procore, cloud, and external calls attempted: false",
            "",
            "This is a concise public-repository handoff for human review. It does not claim release, publication, deployment, approval, certification, or hosted availability.",
            "",
            "## What 0.1.0 includes",
            "",
            *[f"- {item}" for item in report.included_scope],
            "",
            "## What is intentionally not included",
            "",
            *[f"- {item}" for item in report.not_included_scope],
            "",
        )
    )


def render_maintainer_quickstart_markdown(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    lines = [
        "# Maintainer quickstart",
        "",
        "Offline review only; no release, build, publish, tag, or deploy action occurs here.",
        "",
        "## Included in 0.1.0",
        "",
        *[f"- {item}" for item in report.included_scope],
        "",
        "## Intentionally not included",
        "",
        *[f"- {item}" for item in report.not_included_scope],
        "",
    ]
    lines.extend(f"{index}. {item}" for index, item in enumerate(report.quickstart, 1))
    return "\n".join(lines) + "\n"


def render_maintainer_review_checklist_markdown(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    lines = [
        "# Maintainer review checklist",
        "",
        "Maintainer decision and private review remain required.",
        "",
    ]
    lines.extend(f"- [ ] {item.description}" for item in report.review_checklist)
    return "\n".join(lines) + "\n"


def render_maintainer_command_plan_markdown(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    lines = [
        "# Maintainer command plan",
        "",
        "Run locally in order. Commands are read-only or create ignored temporary review output; none releases, builds, publishes, tags, or deploys.",
        "",
        "| Command | Purpose |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| `{item.command}` | {item.purpose.replace('|', '\\|')} |" for item in report.command_plan
    )
    return "\n".join(lines) + "\n"


def render_maintainer_decision_log_template_markdown(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    lines = [
        "# Maintainer decision log template",
        "",
        "Record decisions outside generated output. Replace placeholders only in a private review record.",
        "",
        "| Question | Decision | Owner |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {item.question.replace('|', '\\|')} | `{item.placeholder}` | {item.owner} |"
        for item in report.decision_log_template
    )
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_maintainer_handoff_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_maintainer_handoff_matrix_csv(report: MaintainerHandoffReport) -> str:
    validate_maintainer_handoff_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        ("domain", "gate_status", "evidence", "included_scope", "not_included", "next_step")
    )
    for item in report.handoff_matrix:
        writer.writerow(
            _csv_cell(value)
            for value in (
                item.domain.value,
                item.gate_status.value,
                item.evidence,
                item.included_scope,
                item.not_included,
                item.next_step,
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if raw.is_absolute() or ".." in raw.parts:
        resolved = raw.resolve()
        if not str(resolved).startswith(TMP_PREFIXES):
            raise MaintainerHandoffBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    if not str(resolved).startswith(TMP_PREFIXES) and raw.name not in SAFE_ROOT_NAMES:
        raise MaintainerHandoffBlockedError(
            "Output root is outside the maintainer-handoff boundary."
        )
    return resolved


def write_maintainer_handoff_artifacts(
    report: MaintainerHandoffReport, output_root: str | Path
) -> MaintainerHandoffArtifactResult:
    validate_maintainer_handoff_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "maintainer-handoff-report.json": json.dumps(report.model_dump(mode="json"), indent=2)
        + "\n",
        "maintainer-handoff-report.md": render_maintainer_handoff_report_markdown(report),
        "maintainer-quickstart.md": render_maintainer_quickstart_markdown(report),
        "maintainer-review-checklist.md": render_maintainer_review_checklist_markdown(report),
        "maintainer-command-plan.md": render_maintainer_command_plan_markdown(report),
        "maintainer-decision-log-template.md": render_maintainer_decision_log_template_markdown(
            report
        ),
        "maintainer-handoff-matrix.csv": render_maintainer_handoff_matrix_csv(report),
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
            raise MaintainerHandoffBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return MaintainerHandoffArtifactResult(
        status=report.status, output_directory=root.name, files=list(ARTIFACT_FILES)
    )
