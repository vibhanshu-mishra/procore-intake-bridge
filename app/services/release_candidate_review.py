import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.release_candidate_review import (
    ReleaseCandidateArtifactResult,
    ReleaseCandidateCommandPlanItem,
    ReleaseCandidateDecision,
    ReleaseCandidateDomain,
    ReleaseCandidateDomainSummary,
    ReleaseCandidateFinding,
    ReleaseCandidateGap,
    ReleaseCandidateGate,
    ReleaseCandidateGateStatus,
    ReleaseCandidateMatrixItem,
    ReleaseCandidateReport,
    ReleaseCandidateStatus,
)
from app.services.api_docs_review import build_api_docs_report
from app.services.demo_data_experience import build_demo_data_experience_report
from app.services.docs_site_polish import build_docs_site_polish_report
from app.services.final_public_readiness import build_final_public_readiness_report
from app.services.final_security_review import build_final_security_review_report
from app.services.hosted_ui_review import build_hosted_ui_review_report
from app.services.release_readiness import build_release_readiness_report
from app.services.security_gap_closeout import build_security_gap_closeout_report
from app.services.setup_experience import build_setup_experience_report
from app.services.version_prep import build_version_prep_report, sanitize_version_prep_value


class ReleaseCandidateReviewError(ValueError):
    pass


class ReleaseCandidateReviewBlockedError(ReleaseCandidateReviewError):
    pass


REQUIRED_CONTROLS = (
    "release_candidate_require_version_prep",
    "release_candidate_require_setup_experience",
    "release_candidate_require_demo_data",
    "release_candidate_require_api_docs",
    "release_candidate_require_hosted_ui_review",
    "release_candidate_require_docs_site_polish",
    "release_candidate_require_security_closeout",
    "release_candidate_require_final_readiness",
    "release_candidate_require_release_boundary",
    "release_candidate_require_no_build",
    "release_candidate_require_no_publish",
    "release_candidate_require_no_tag",
    "release_candidate_require_no_deploy",
    "release_candidate_require_no_workflow_changes",
)
REQUIRED_IGNORES = (
    "release-candidate-output/",
    "release-candidate-review-output/",
    "rc-checklist-output/",
    "rc-readiness-output/",
    "candidate-release-output/",
    "*.release-candidate-report.json",
    "*.release-candidate-report.md",
    "*.release-candidate-checklist.md",
    "*.release-candidate-gap-register.md",
    "*.release-candidate-command-plan.md",
    "*.release-candidate-matrix.csv",
)
ARTIFACT_FILES = (
    "release-candidate-report.json",
    "release-candidate-report.md",
    "release-candidate-checklist.md",
    "release-candidate-gap-register.md",
    "release-candidate-command-plan.md",
    "release-candidate-matrix.csv",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "release-candidate-output",
    "release-candidate-review-output",
    "rc-checklist-output",
    "rc-readiness-output",
    "candidate-release-output",
}
DEPENDENCY_PATHS = {
    "version_prep": "app/services/version_prep.py",
    "setup_experience": "app/services/setup_experience.py",
    "demo_data": "app/services/demo_data_experience.py",
    "api_docs": "app/services/api_docs_review.py",
    "hosted_ui_review": "app/services/hosted_ui_review.py",
    "docs_site_polish": "app/services/docs_site_polish.py",
    "final_security_readiness": "app/services/final_security_review.py",
    "security_gap_closeout": "app/services/security_gap_closeout.py",
    "final_public_readiness": "app/services/final_public_readiness.py",
    "release_readiness": "app/services/release_readiness.py",
    "public_safety_audit": "scripts/audit_public_safety.py",
    "route_audit": "scripts/audit_routes_read_only.py",
    "public_usability_audit": "scripts/audit_public_usability.py",
    "docs_site_audit": "scripts/check_docs_site.py",
    "changelog": "CHANGELOG.md",
    "roadmap": "docs/roadmap.md",
}
SAFE_COMMANDS = (
    (
        "make version-prep-review",
        "Review version and package metadata.",
        ReleaseCandidateDomain.VERSION_METADATA,
    ),
    (
        "make setup-experience-review",
        "Review local setup guidance.",
        ReleaseCandidateDomain.SETUP_EXPERIENCE,
    ),
    (
        "make demo-seed-plan",
        "Print the non-writing Demo seed plan.",
        ReleaseCandidateDomain.DEMO_SEED_RESET,
    ),
    (
        "make api-docs-review",
        "Review the offline API inventory.",
        ReleaseCandidateDomain.API_DOCUMENTATION,
    ),
    (
        "make hosted-ui-review",
        "Review hosted UI preparation.",
        ReleaseCandidateDomain.HOSTED_UI_PREPARATION,
    ),
    (
        "make docs-site-polish-review",
        "Review local docs navigation.",
        ReleaseCandidateDomain.DOCS_SITE_POLISH,
    ),
    (
        "make security-gap-closeout",
        "Review public security gaps.",
        ReleaseCandidateDomain.SECURITY_GAP_CLOSEOUT,
    ),
    (
        "make final-readiness",
        "Review final public readiness.",
        ReleaseCandidateDomain.PUBLIC_REPO_SAFETY,
    ),
    (
        "make release-readiness",
        "Review the existing release boundary.",
        ReleaseCandidateDomain.RELEASE_BOUNDARY,
    ),
    (
        "make safety-audit",
        "Run the local public-safety audit.",
        ReleaseCandidateDomain.PUBLIC_REPO_SAFETY,
    ),
    (
        "make route-audit",
        "Run the local route-boundary audit.",
        ReleaseCandidateDomain.ROUTE_BOUNDARY,
    ),
    (
        "make public-usability-audit",
        "Run local usability checks.",
        ReleaseCandidateDomain.PUBLIC_REPO_SAFETY,
    ),
    (
        "make docs-site-check",
        "Run the local docs-site checker.",
        ReleaseCandidateDomain.DOCS_SITE_POLISH,
    ),
)
SEMANTIC_VERSION_PATTERN = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
UNSAFE_COMMAND_PATTERN = re.compile(
    r"(?i)(?:python\s+-m\s+build|docker\s+(?:build|push)|git\s+tag|"
    r"make\s+(?:publish|deploy|tag|release)(?:\s|$)|twine\s+upload|"
    r"sandbox-read-validation|postgres-connectivity|migration-status-check)"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\bpackage (?:is )?published\b|\brelease (?:is )?complete\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance) certified\b|"
    r"\bprocore (?:endorsed|partner|certified|officially supported)\b"
)
NEGATED_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:not|no|does not|do not|never|without|cannot|isn't|is not|"
    r"doesn't|out of scope|requires separate|candidate|maintainer review)\b"
)


def sanitize_release_candidate_value(value: Any) -> str:
    return sanitize_version_prep_value(value)


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _validate_settings(settings: Settings) -> str:
    if not _setting(settings, "release_candidate_review_enabled", True):
        raise ReleaseCandidateReviewBlockedError("Release-candidate review is disabled.")
    if not _setting(settings, "release_candidate_fail_closed", True):
        raise ReleaseCandidateReviewBlockedError(
            "Release-candidate review must remain fail closed."
        )
    if not all(bool(_setting(settings, name, True)) for name in REQUIRED_CONTROLS):
        raise ReleaseCandidateReviewBlockedError(
            "A required release-candidate review control is disabled."
        )
    allow_settings = (
        "release_candidate_allow_real_identities",
        "release_candidate_allow_real_domains",
        "release_candidate_allow_real_urls",
        "release_candidate_allow_report_contents",
        "release_candidate_allow_private_paths",
    )
    if any(bool(_setting(settings, name, False)) for name in allow_settings):
        raise ReleaseCandidateReviewBlockedError("Unsafe release-candidate material is enabled.")
    target = str(_setting(settings, "release_candidate_target_version", "0.1.0"))
    if not SEMANTIC_VERSION_PATTERN.fullmatch(target):
        raise ReleaseCandidateReviewBlockedError("The release-candidate target is invalid.")
    return target


def build_release_candidate_dependencies(settings: Settings) -> dict[str, bool]:
    _validate_settings(settings)
    return {name: Path(path).is_file() for name, path in DEPENDENCY_PATHS.items()}


def _status(value: Any) -> str:
    return str(getattr(value, "value", value)).casefold()


def _gate_status(status: Any, *, private_review: bool = False) -> ReleaseCandidateGateStatus:
    normalized = _status(status)
    if normalized in {"blocked", "missing", "not_run"}:
        return ReleaseCandidateGateStatus.BLOCKED
    if private_review or "needs" in normalized:
        return ReleaseCandidateGateStatus.NEEDS_REVIEW
    return ReleaseCandidateGateStatus.PASS


def build_release_candidate_domain_summaries(
    settings: Settings,
) -> list[ReleaseCandidateDomainSummary]:
    target = _validate_settings(settings)
    version = build_version_prep_report(settings)
    setup = build_setup_experience_report(settings)
    demo = build_demo_data_experience_report(settings)
    api_docs = build_api_docs_report(settings)
    hosted_ui = build_hosted_ui_review_report(settings)
    docs_site = build_docs_site_polish_report(settings)
    final_security = build_final_security_review_report(settings)
    security_gap = build_security_gap_closeout_report(settings)
    final_public = build_final_public_readiness_report(settings)
    release = build_release_readiness_report()
    dependencies = build_release_candidate_dependencies(settings)
    ignores = all(
        item in Path(".gitignore").read_text(encoding="utf-8") for item in REQUIRED_IGNORES
    )
    changelog_roadmap = all(
        "J7" in Path(path).read_text(encoding="utf-8")
        for path in ("CHANGELOG.md", "docs/roadmap.md")
        if Path(path).is_file()
    )
    package_status = (
        ReleaseCandidateGateStatus.NEEDS_REVIEW
        if version.warnings
        else ReleaseCandidateGateStatus.PASS
    )
    rows = (
        (
            ReleaseCandidateDomain.VERSION_METADATA,
            ReleaseCandidateGateStatus.PASS
            if version.target_version == target
            else ReleaseCandidateGateStatus.BLOCKED,
            "Prepared target version is consistent with J6.",
            "J6 version prep",
            False,
        ),
        (
            ReleaseCandidateDomain.PACKAGE_METADATA,
            package_status,
            "Required package metadata is present; optional fields retain review status.",
            "J6 package metadata",
            bool(version.warnings),
        ),
        (
            ReleaseCandidateDomain.SETUP_EXPERIENCE,
            _gate_status(setup.status),
            "Local setup experience is documented and offline.",
            "J1 setup review",
            False,
        ),
        (
            ReleaseCandidateDomain.DEMO_SEED_RESET,
            _gate_status(demo.status),
            "Deterministic local Demo planning is available.",
            "J2 Demo review",
            False,
        ),
        (
            ReleaseCandidateDomain.API_DOCUMENTATION,
            _gate_status(api_docs.status),
            "All local application routes are documented.",
            "J3 API docs",
            False,
        ),
        (
            ReleaseCandidateDomain.HOSTED_UI_PREPARATION,
            _gate_status(hosted_ui.status, private_review=True),
            "Hosted UI preparation is public-safe and retains private gates.",
            "J4 hosted UI review",
            True,
        ),
        (
            ReleaseCandidateDomain.DOCS_SITE_POLISH,
            _gate_status(docs_site.status),
            "Local handbook navigation and reader paths are complete.",
            "J5 docs polish",
            False,
        ),
        (
            ReleaseCandidateDomain.SECURITY_READINESS,
            _gate_status(final_security.status, private_review=True),
            "Public security review is complete; private security review remains required.",
            "I8 final security review",
            True,
        ),
        (
            ReleaseCandidateDomain.SECURITY_GAP_CLOSEOUT,
            _gate_status(security_gap.status, private_review=True),
            "Public gap closeout is documented with private actions outstanding.",
            "I9 security closeout",
            True,
        ),
        (
            ReleaseCandidateDomain.PUBLIC_REPO_SAFETY,
            _gate_status(final_public.status),
            "Final public readiness and safety boundaries are present.",
            "H1/H2 final readiness",
            False,
        ),
        (
            ReleaseCandidateDomain.ROUTE_BOUNDARY,
            ReleaseCandidateGateStatus.PASS
            if dependencies["route_audit"] and api_docs.unsafe_routes_total == 0
            else ReleaseCandidateGateStatus.BLOCKED,
            "Route audit exists and the API inventory has no unsafe route.",
            "Route audit and J3",
            False,
        ),
        (
            ReleaseCandidateDomain.GENERATED_OUTPUT_BOUNDARY,
            ReleaseCandidateGateStatus.PASS if ignores else ReleaseCandidateGateStatus.BLOCKED,
            "Release-candidate generated outputs are ignored.",
            ".gitignore",
            False,
        ),
        (
            ReleaseCandidateDomain.CHANGELOG_AND_ROADMAP,
            ReleaseCandidateGateStatus.PASS
            if changelog_roadmap
            else ReleaseCandidateGateStatus.MISSING,
            "Changelog and roadmap describe J7 as preparation only.",
            "CHANGELOG.md and roadmap",
            False,
        ),
        (
            ReleaseCandidateDomain.RELEASE_BOUNDARY,
            _gate_status(release.status),
            "Existing release readiness keeps publication and deployment manual.",
            "E4 and J6 release boundaries",
            False,
        ),
        (
            ReleaseCandidateDomain.PRIVATE_REVIEW_BOUNDARY,
            ReleaseCandidateGateStatus.NEEDS_REVIEW,
            "Maintainer and authorized private reviews remain required before any live use.",
            "Private review boundary",
            True,
        ),
    )
    return [
        ReleaseCandidateDomainSummary(
            domain=domain,
            status=status,
            summary=summary,
            source=source,
            private_review_required=private_review,
        )
        for domain, status, summary, source, private_review in rows
    ]


def build_release_candidate_gates(settings: Settings) -> list[ReleaseCandidateGate]:
    return [
        ReleaseCandidateGate(
            code=f"{item.domain.value}_gate",
            domain=item.domain,
            status=item.status,
            description=item.summary,
            evidence=[item.source],
        )
        for item in build_release_candidate_domain_summaries(settings)
    ]


def build_release_candidate_gap_register(settings: Settings) -> list[ReleaseCandidateGap]:
    gaps = []
    for item in build_release_candidate_domain_summaries(settings):
        if item.status is ReleaseCandidateGateStatus.PASS:
            continue
        gaps.append(
            ReleaseCandidateGap(
                code=f"{item.domain.value}_gap",
                domain=item.domain,
                description=(
                    "Private or maintainer review remains required."
                    if item.status is ReleaseCandidateGateStatus.NEEDS_REVIEW
                    else "A required public repository condition is blocked or missing."
                ),
                private_review_required=item.private_review_required,
                blocking=item.status
                in {ReleaseCandidateGateStatus.BLOCKED, ReleaseCandidateGateStatus.MISSING},
            )
        )
    return gaps


def build_release_candidate_command_plan(
    settings: Settings,
) -> list[ReleaseCandidateCommandPlanItem]:
    _validate_settings(settings)
    items = [
        ReleaseCandidateCommandPlanItem(command=command, purpose=purpose, domain=domain)
        for command, purpose, domain in SAFE_COMMANDS
    ]
    if any(UNSAFE_COMMAND_PATTERN.search(item.command) for item in items):
        raise ReleaseCandidateReviewBlockedError("An unsafe release-candidate command was blocked.")
    return items


def build_release_candidate_matrix(settings: Settings) -> list[ReleaseCandidateMatrixItem]:
    gaps = {item.domain: item for item in build_release_candidate_gap_register(settings)}
    return [
        ReleaseCandidateMatrixItem(
            domain=item.domain,
            gate_status=item.status,
            evidence=item.source,
            gap=gaps[item.domain].description if item.domain in gaps else "No public gap.",
            next_step=(
                "Complete the documented review gate."
                if item.domain in gaps
                else "Retain the current public-safe boundary."
            ),
        )
        for item in build_release_candidate_domain_summaries(settings)
    ]


def build_release_candidate_report(settings: Settings) -> ReleaseCandidateReport:
    target = _validate_settings(settings)
    dependencies = build_release_candidate_dependencies(settings)
    summaries = build_release_candidate_domain_summaries(settings)
    gates = [
        ReleaseCandidateGate(
            code=f"{item.domain.value}_gate",
            domain=item.domain,
            status=item.status,
            description=item.summary,
            evidence=[item.source],
        )
        for item in summaries
    ]
    gaps = []
    for item in summaries:
        if item.status is ReleaseCandidateGateStatus.PASS:
            continue
        gaps.append(
            ReleaseCandidateGap(
                code=f"{item.domain.value}_gap",
                domain=item.domain,
                description=(
                    "Private or maintainer review remains required."
                    if item.status is ReleaseCandidateGateStatus.NEEDS_REVIEW
                    else "A required public repository condition is blocked or missing."
                ),
                private_review_required=item.private_review_required,
                blocking=item.status
                in {ReleaseCandidateGateStatus.BLOCKED, ReleaseCandidateGateStatus.MISSING},
            )
        )
    command_plan = build_release_candidate_command_plan(settings)
    gap_by_domain = {item.domain: item for item in gaps}
    matrix = [
        ReleaseCandidateMatrixItem(
            domain=item.domain,
            gate_status=item.status,
            evidence=item.source,
            gap=(
                gap_by_domain[item.domain].description
                if item.domain in gap_by_domain
                else "No public gap."
            ),
            next_step=(
                "Complete the documented review gate."
                if item.domain in gap_by_domain
                else "Retain the current public-safe boundary."
            ),
        )
        for item in summaries
    ]
    findings = [
        ReleaseCandidateFinding(
            code=gap.code,
            message=gap.description,
            severity="blocker" if gap.blocking else "warning",
            domain=gap.domain,
        )
        for gap in gaps
    ]
    findings.extend(
        ReleaseCandidateFinding(
            code=f"missing_{name}",
            message="A required release-candidate dependency is missing.",
            severity="blocker",
        )
        for name, present in dependencies.items()
        if not present
    )
    maximum = int(_setting(settings, "release_candidate_max_findings", 400))
    if len(findings) > maximum:
        raise ReleaseCandidateReviewBlockedError(
            "Release-candidate findings exceed the configured limit."
        )
    blockers = [finding.message for finding in findings if finding.severity == "blocker"]
    warnings = [finding.message for finding in findings if finding.severity == "warning"]
    report = ReleaseCandidateReport(
        status=(
            ReleaseCandidateStatus.BLOCKED
            if blockers
            else ReleaseCandidateStatus.NEEDS_REVIEW
            if warnings
            else ReleaseCandidateStatus.READY
        ),
        decision=(
            ReleaseCandidateDecision.BLOCKED
            if blockers
            else ReleaseCandidateDecision.NEEDS_REVIEW
            if warnings
            else ReleaseCandidateDecision.READY_FOR_MAINTAINER_REVIEW
        ),
        target_version=target,
        dependencies=dependencies,
        domain_summaries=summaries,
        gates=gates,
        gaps=gaps,
        command_plan=command_plan,
        matrix=matrix,
        domains_total=len(summaries),
        domains_passed=sum(item.status is ReleaseCandidateGateStatus.PASS for item in summaries),
        domains_needing_review=sum(
            item.status is ReleaseCandidateGateStatus.NEEDS_REVIEW for item in summaries
        ),
        domains_blocked=sum(
            item.status in {ReleaseCandidateGateStatus.BLOCKED, ReleaseCandidateGateStatus.MISSING}
            for item in summaries
        ),
        gates_total=len(gates),
        gates_passed=sum(item.status is ReleaseCandidateGateStatus.PASS for item in gates),
        gates_needing_review=sum(
            item.status is ReleaseCandidateGateStatus.NEEDS_REVIEW for item in gates
        ),
        gaps_total=len(gaps),
        findings=findings,
        blockers=blockers,
        warnings=warnings,
        public_repo_safe_for_rc_review=not blockers,
        recommended_next_steps=[
            "Review non-blocking public and private gaps with the maintainer.",
            "Complete authorized private security and infrastructure review separately.",
            "Do not build, publish, tag, release, or deploy from this checklist.",
        ],
    )
    validate_release_candidate_report_safe(report)
    return report


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value


def validate_release_candidate_report_safe(report: ReleaseCandidateReport) -> None:
    unsafe_flags = (
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
        report.private_report_contents_exposed,
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
    )
    if any(unsafe_flags) or not report.public_repo_safe_for_rc_review or report.blockers:
        raise ReleaseCandidateReviewBlockedError("The release-candidate report failed closed.")
    if not report.private_review_required:
        raise ReleaseCandidateReviewBlockedError("Private review must remain required.")
    for item in report.command_plan:
        if (
            not item.safe_read_only
            or item.writes_generated_output
            or item.database_access
            or item.live_operation
            or item.external_operation
            or UNSAFE_COMMAND_PATTERN.search(item.command)
        ):
            raise ReleaseCandidateReviewBlockedError("The command plan contains an unsafe action.")
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_release_candidate_value(value) == "[redacted]":
            raise ReleaseCandidateReviewBlockedError("The report contains unsafe material.")
        for match in UNSAFE_CLAIM_PATTERN.finditer(value):
            window = value[max(0, match.start() - 100) : match.end() + 20]
            if not NEGATED_CLAIM_PATTERN.search(window):
                raise ReleaseCandidateReviewBlockedError(
                    "The report contains an approval or release claim."
                )


def render_release_candidate_report_markdown(report: ReleaseCandidateReport) -> str:
    validate_release_candidate_report_safe(report)
    return "\n".join(
        (
            "# Release-candidate review",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Prepared target version: `{report.target_version}`",
            f"- Domains passed: {report.domains_passed}/{report.domains_total}",
            f"- Domains needing review: {report.domains_needing_review}",
            "- Private review required: true",
            "- Build, publish, tag, release, or deployment attempted: false",
            "",
            "This checklist grants no production, pilot, release, or deployment approval.",
            "",
        )
    )


def render_release_candidate_checklist_markdown(report: ReleaseCandidateReport) -> str:
    validate_release_candidate_report_safe(report)
    lines = ["# Release-candidate checklist", ""]
    for gate in report.gates:
        marker = "x" if gate.status is ReleaseCandidateGateStatus.PASS else " "
        lines.append(f"- [{marker}] {gate.description} Status: `{gate.status.value}`.")
    return "\n".join(lines) + "\n"


def render_release_candidate_gap_register_markdown(report: ReleaseCandidateReport) -> str:
    validate_release_candidate_report_safe(report)
    lines = ["# Release-candidate gap register", ""]
    for gap in report.gaps:
        lines.extend(
            (
                f"## {gap.domain.value}",
                "",
                gap.description,
                f"Private review required: `{str(gap.private_review_required).lower()}`.",
                "",
            )
        )
    return "\n".join(lines)


def render_release_candidate_command_plan_markdown(report: ReleaseCandidateReport) -> str:
    validate_release_candidate_report_safe(report)
    lines = [
        "# Release-candidate command plan",
        "",
        "Every command is local, non-writing, and makes no external call.",
        "",
    ]
    for item in report.command_plan:
        lines.append(f"- `{item.command}` — {item.purpose}")
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_release_candidate_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_release_candidate_matrix_csv(report: ReleaseCandidateReport) -> str:
    validate_release_candidate_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("domain", "gate_status", "evidence", "gap", "next_step"))
    for item in report.matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.domain.value,
                    item.gate_status.value,
                    item.evidence,
                    item.gap,
                    item.next_step,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if ".." in raw.parts:
        raise ReleaseCandidateReviewBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        (
            "/tmp/procore-intake-bridge-release-candidate-",
            "/private/tmp/procore-intake-bridge-release-candidate-",
        )
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise ReleaseCandidateReviewBlockedError(
            "Output root is outside the release-candidate boundary."
        )
    return resolved


def write_release_candidate_artifacts(
    report: ReleaseCandidateReport, output_root: str | Path
) -> ReleaseCandidateArtifactResult:
    validate_release_candidate_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "release-candidate-report.json": json.dumps(report.model_dump(mode="json"), indent=2)
        + "\n",
        "release-candidate-report.md": render_release_candidate_report_markdown(report),
        "release-candidate-checklist.md": render_release_candidate_checklist_markdown(report),
        "release-candidate-gap-register.md": render_release_candidate_gap_register_markdown(report),
        "release-candidate-command-plan.md": render_release_candidate_command_plan_markdown(report),
        "release-candidate-matrix.csv": render_release_candidate_matrix_csv(report),
    }
    rendered["manifest.json"] = (
        json.dumps(
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
        + "\n"
    )
    for filename, contents in rendered.items():
        target = (root / filename).resolve()
        if target.parent != root:
            raise ReleaseCandidateReviewBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return ReleaseCandidateArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=list(ARTIFACT_FILES),
    )
