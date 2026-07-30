import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.final_public_readiness import (
    FinalPublicReadinessArtifactResult,
    FinalPublicReadinessCategory,
    FinalPublicReadinessDecision,
    FinalPublicReadinessFinding,
    FinalPublicReadinessReport,
    FinalPublicReadinessRequirement,
    FinalPublicReadinessStatus,
)

RAW_URL = re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mongodb)://\S+")
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")
IDENTITY = re.compile(
    r"(?i)\b(?:reviewer|approver|operator|maintainer)\s*[:=]\s*"
    r"(?![A-Z0-9_-]*PLACEHOLDER)[A-Za-z][A-Za-z .'-]{2,}"
)
LONG_ID = re.compile(r"\b(?:\d{9,}|[a-f0-9]{24,}|[A-Za-z0-9_-]{40,})\b")
CLOUD_ID = re.compile(
    r"(?i)(?:\barn:aws[a-z-]*:\S+|\b\d{12}\b|/subscriptions/[0-9a-f-]{20,}|"
    r"\bprojects/[a-z0-9-]{6,}\b)"
)
REGISTRY_REF = re.compile(
    r"(?i)\b[a-z0-9.-]+/[a-z0-9._/-]+:(?:latest|v?\d[\w.-]*|[a-f0-9]{7,})\b"
)
CERTIFICATE = re.compile(
    r"(?i)(?:-----BEGIN (?:RSA |EC |OPENSSH )?(?:CERTIFICATE|PRIVATE KEY)|"
    r"-----BEGIN CERTIFICATE REQUEST-----|_acme-challenge\.|"
    r"\b(?:private_key|certificate|csr|acme[-_ ]challenge)\s*[:=]\s*\S+)"
)
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+|(?:secret|token|password|credential|"
    r"app[_ -]?version[_ -]?key)\s*[:=]\s*\S+)"
)
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
REPORT_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:report|payload|response|evidence)|"
    r"(?:report|evidence|support bundle)[_ -]?contents?\s*[:=])"
)
LIVE_RESULT = re.compile(
    r'(?i)^\s*\{.*"(?:status_code|response_body|records|results|deployment_id)"\s*:'
)
OPERATION_LOG = re.compile(
    r"(?i)(?:deployment|build|release|migration|restore|backup) "
    r"(?:log|output|result)|\.(?:sql|dump|backup|pgdump)\b"
)
APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:approved for (?:launch|pilot|production|release)|"
    r"(?:pilot|launch|release|production) (?:is )?approved|"
    r"production[- ]ready|ready for production|security (?:is )?complete)\b"
)
ENDORSEMENT_CLAIM = re.compile(
    r"(?i)\bprocore[- ](?:endorsed|partner|partnership|certified|certification|"
    r"officially supported)\b"
)

ARTIFACT_FILES = [
    "final-readiness-report.json",
    "final-readiness-report.md",
    "public-repo-checklist.md",
    "maintainer-handoff.md",
    "final-audit-summary.md",
    "manifest.json",
]
SAFE_OUTPUT_ROOTS = {
    "final-readiness-output",
    "public-readiness-output",
    "repo-readiness-output",
    "maintainer-handoff-output",
}


class FinalPublicReadinessError(RuntimeError):
    """Final readiness inspection failed with private details suppressed."""


class FinalPublicReadinessBlockedError(FinalPublicReadinessError):
    pass


def _strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def sanitize_final_public_readiness_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_final_public_readiness_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_final_public_readiness_value(item) for item in value]
    if isinstance(value, Path):
        return "[masked-path]"
    if isinstance(value, str):
        for pattern, replacement in (
            (SIGNED_URL, "[masked-url]"),
            (RAW_URL, "[masked-url]"),
            (DOMAIN, "[masked-domain]"),
            (EMAIL, "[masked-identity]"),
            (PHONE, "[masked-identity]"),
            (IDENTITY, "[masked-identity]"),
            (CLOUD_ID, "[masked-infrastructure-identifier]"),
            (REGISTRY_REF, "[masked-registry-reference]"),
            (CERTIFICATE, "[masked-certificate-material]"),
            (SECRET, "[masked-secret]"),
            (ABSOLUTE_PATH, "[masked-path]"),
            (REPORT_CONTENT, "[masked-report-content]"),
            (LIVE_RESULT, "[masked-live-result]"),
            (OPERATION_LOG, "[masked-operation-output]"),
            (APPROVAL_CLAIM, "[masked-claim]"),
            (ENDORSEMENT_CLAIM, "[masked-claim]"),
            (LONG_ID, "[masked-identifier]"),
        ):
            if pattern.search(value):
                return replacement
    return value


def _exists(root: Path, *names: str) -> tuple[int, int]:
    return len(names), sum((root / name).is_file() for name in names)


def _contains(text: str, *markers: str) -> tuple[int, int]:
    lowered = text.casefold()
    return len(markers), sum(marker.casefold() in lowered for marker in markers)


def build_final_public_readiness_requirements(
    settings: Settings,
) -> list[FinalPublicReadinessRequirement]:
    root = Path.cwd()
    makefile_path = root / "Makefile"
    gitignore_path = root / ".gitignore"
    makefile = (
        makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    )
    gitignore = (
        gitignore_path.read_text(encoding="utf-8")
        if gitignore_path.is_file()
        else ""
    )
    quality_lines = makefile.split("quality:", 1)[-1].splitlines()
    quality_header = quality_lines[0] if quality_lines else ""
    docs_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            root / "README.md",
            root / "QUICKSTART.md",
            root / "docs/safety-model.md",
            root / "docs/final-public-readiness.md",
        )
        if path.is_file()
    )
    checks: dict[FinalPublicReadinessCategory, tuple[int, int]] = {
        FinalPublicReadinessCategory.REPOSITORY_STRUCTURE: _exists(
            root, "README.md", "QUICKSTART.md", "Makefile", "pyproject.toml", ".env.example"
        ),
        FinalPublicReadinessCategory.CLONE_TO_DEMO: _contains(
            makefile, "start:", "first-run:", "try-demo:"
        ),
        FinalPublicReadinessCategory.COMMAND_UX: _contains(
            makefile,
            "help:",
            "prepare-sandbox:",
            "prepare-pilot:",
            "quality:",
            "safety-check:",
        ),
        FinalPublicReadinessCategory.DOCUMENTATION: _exists(
            root,
            "docs/index.md",
            "docs/project-status.md",
            "docs/roadmap.md",
            "docs/safety-model.md",
        ),
        FinalPublicReadinessCategory.DOCS_SITE: _exists(
            root, "mkdocs.yml", "scripts/check_docs_site.py", "docs/docs-navigation.md"
        ),
        FinalPublicReadinessCategory.EXAMPLES: _exists(
            root,
            "examples/demo-flow.md",
            "examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json",
            "examples/final-public-readiness/example_final_readiness_summary.md",
        ),
        FinalPublicReadinessCategory.FIXTURES: _exists(
            root, "app/fixtures/fake_rfis.json", "app/fixtures/fake_submittals.json"
        ),
        FinalPublicReadinessCategory.PUBLIC_SAFETY: _exists(
            root, "scripts/audit_public_safety.py", "docs/safety-model.md"
        ),
        FinalPublicReadinessCategory.ROUTE_SAFETY: _exists(
            root, "scripts/audit_routes_read_only.py"
        ),
        FinalPublicReadinessCategory.SECRET_SAFETY: _exists(
            root, "docs/cloud-secret-providers.md", "scripts/check_cloud_secret_provider.py"
        ),
        FinalPublicReadinessCategory.STORAGE_SAFETY: _exists(
            root, "docs/cloud-storage-providers.md", "scripts/check_cloud_storage_provider.py"
        ),
        FinalPublicReadinessCategory.DATABASE_SAFETY: _exists(
            root, "docs/postgres-runtime-operations.md", "scripts/check_postgres_runtime.py"
        ),
        FinalPublicReadinessCategory.WEBHOOK_SAFETY: _exists(
            root,
            "scripts/check_webhook_docs_record.py",
            "docs/webhook-production-verification.md",
        ),
        FinalPublicReadinessCategory.HOSTED_DEPLOYMENT_SAFETY: _exists(
            root,
            "docs/hosted-deployment-templates.md",
            "scripts/check_hosted_deployment_template.py",
        ),
        FinalPublicReadinessCategory.HTTPS_WEBHOOK_PLANNING_SAFETY: _exists(
            root,
            "docs/https-webhook-production-planning.md",
            "scripts/check_https_webhook_plan.py",
        ),
        FinalPublicReadinessCategory.HOSTED_PILOT_DRY_RUN_SAFETY: _exists(
            root,
            "docs/hosted-pilot-dry-run.md",
            "scripts/check_hosted_pilot_dry_run.py",
        ),
        FinalPublicReadinessCategory.GENERATED_OUTPUT_IGNORES: _contains(
            gitignore,
            "final-readiness-output/",
            "hosted-pilot-dry-run-output/",
            "https-webhook-output/",
            "hosted-deployment-output/",
        ),
        FinalPublicReadinessCategory.OPTIONAL_DEPENDENCIES: _exists(
            root, "docs/cloud-secret-providers.md", "docs/cloud-storage-providers.md"
        ),
        FinalPublicReadinessCategory.LIVE_GATED_COMMANDS: (
            8,
            sum(
                (root / script).is_file()
                for script in (
                    "scripts/run_sandbox_dmsa_smoke.py",
                    "scripts/run_sandbox_read_validation.py",
                    "scripts/run_postgres_connectivity_check.py",
                    "scripts/run_postgres_migration_status_check.py",
                )
            )
            + sum(
                marker not in quality_header
                for marker in (
                    "sandbox-read-validation",
                    "run_sandbox_dmsa_smoke.py",
                    "postgres-connectivity-check",
                    "postgres-migration-status-check",
                )
            ),
        ),
        FinalPublicReadinessCategory.RELEASE_READINESS: _exists(
            root, "docs/release-readiness.md", "scripts/check_release_readiness.py"
        ),
        FinalPublicReadinessCategory.PUBLIC_PRIVATE_BOUNDARY: _contains(
            docs_text, "outside git", "private", "no live operation"
        ),
        FinalPublicReadinessCategory.KNOWN_LIMITATIONS: _contains(
            docs_text, "known limitations"
        ),
        FinalPublicReadinessCategory.MAINTAINER_REVIEW: _exists(
            root, "docs/release-checklist.md", "docs/final-readiness-checklist.md"
        ),
    }
    requirements = []
    for category, (total, passed) in checks.items():
        status = (
            FinalPublicReadinessStatus.PASSED
            if passed == total
            else FinalPublicReadinessStatus.NEEDS_REVIEW
        )
        requirements.append(
            FinalPublicReadinessRequirement(
                category=category,
                status=status,
                checks_total=total,
                checks_passed=passed,
                message=(
                    "Required public repository markers are present."
                    if passed == total
                    else "One or more required public repository markers need review."
                ),
            )
        )
    if not settings.final_public_readiness_enabled:
        requirements[0] = requirements[0].model_copy(
            update={"status": FinalPublicReadinessStatus.BLOCKED}
        )
    return requirements


def build_final_public_readiness_report(settings: Settings) -> FinalPublicReadinessReport:
    requirements = build_final_public_readiness_requirements(settings)
    findings: list[FinalPublicReadinessFinding] = []
    unsafe_policy = any(
        (
            settings.final_public_readiness_allow_real_identities,
            settings.final_public_readiness_allow_real_domains,
            settings.final_public_readiness_allow_real_urls,
            settings.final_public_readiness_allow_real_infra_ids,
            settings.final_public_readiness_allow_report_contents,
            settings.final_public_readiness_allow_absolute_paths,
            not settings.final_public_readiness_fail_closed,
        )
    )
    if unsafe_policy:
        findings.append(
            FinalPublicReadinessFinding(
                category=FinalPublicReadinessCategory.PUBLIC_SAFETY,
                code="unsafe_policy",
                severity="blocking",
                message="Final readiness safety policy must remain fail closed.",
            )
        )
    for requirement in requirements:
        if requirement.status == FinalPublicReadinessStatus.NEEDS_REVIEW:
            findings.append(
                FinalPublicReadinessFinding(
                    category=requirement.category,
                    code="required_marker_missing",
                    severity="warning",
                    message="A required public repository marker needs maintainer review.",
                )
            )
        elif requirement.status == FinalPublicReadinessStatus.BLOCKED:
            findings.append(
                FinalPublicReadinessFinding(
                    category=requirement.category,
                    code="audit_disabled",
                    severity="blocking",
                    message="Final public readiness inspection is disabled.",
                )
            )
    if len(findings) > settings.final_public_readiness_max_findings:
        findings = findings[: settings.final_public_readiness_max_findings]
        findings.append(
            FinalPublicReadinessFinding(
                category=FinalPublicReadinessCategory.PUBLIC_SAFETY,
                code="finding_limit_exceeded",
                severity="blocking",
                message="The configured finding limit was exceeded.",
            )
        )
    blockers = [item.code for item in findings if item.severity == "blocking"]
    warnings = [item.code for item in findings if item.severity == "warning"]
    categories_blocked = sum(
        item.status == FinalPublicReadinessStatus.BLOCKED for item in requirements
    )
    categories_needing_review = sum(
        item.status == FinalPublicReadinessStatus.NEEDS_REVIEW for item in requirements
    )
    if blockers:
        status = FinalPublicReadinessStatus.BLOCKED
        decision = FinalPublicReadinessDecision.BLOCKED
    elif warnings:
        status = FinalPublicReadinessStatus.NEEDS_REVIEW
        decision = FinalPublicReadinessDecision.NEEDS_REVIEW
    else:
        status = FinalPublicReadinessStatus.READY_FOR_MAINTAINER_REVIEW
        decision = FinalPublicReadinessDecision.READY
    return FinalPublicReadinessReport(
        status=status,
        decision=decision,
        categories_total=len(requirements),
        categories_ready=len(requirements)
        - categories_needing_review
        - categories_blocked,
        categories_needing_review=categories_needing_review,
        categories_blocked=categories_blocked,
        blockers=blockers,
        warnings=warnings,
        checks_attempted=[item.category.value for item in requirements],
        requirements=requirements,
        findings=findings,
        recommended_next_steps=[
            "Run the documented offline maintainer checks.",
            "Review warnings and known limitations.",
            "Keep private values and real reports outside Git.",
            "Make any release, deployment, or pilot decision separately.",
        ],
    )


def validate_final_public_readiness_report_safe(
    report: FinalPublicReadinessReport,
) -> None:
    for value in _strings(report.model_dump(mode="json")):
        for pattern in (
            RAW_URL,
            DOMAIN,
            EMAIL,
            PHONE,
            IDENTITY,
            CLOUD_ID,
            REGISTRY_REF,
            CERTIFICATE,
            SECRET,
            ABSOLUTE_PATH,
            REPORT_CONTENT,
            LIVE_RESULT,
            OPERATION_LOG,
            APPROVAL_CLAIM,
            ENDORSEMENT_CLAIM,
            LONG_ID,
        ):
            if pattern.search(value):
                raise FinalPublicReadinessBlockedError(
                    "Final readiness report failed safety validation."
                )
    flags = (
        report.live_operation_attempted,
        report.external_call_attempted,
        report.deployment_attempted,
        report.release_attempted,
        report.procore_call_attempted,
        report.db_connection_attempted,
        report.cloud_call_attempted,
        report.webhook_registration_attempted,
        report.private_report_contents_exposed,
        report.secrets_exposed,
        report.ids_exposed,
        report.real_urls_exposed,
        report.real_domains_exposed,
        report.private_paths_exposed,
        report.production_approval_claimed,
    )
    if any(flags):
        raise FinalPublicReadinessBlockedError(
            "Final readiness report contains unsafe operation flags."
        )


def _header(title: str, report: FinalPublicReadinessReport) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Status: `{report.status}`",
        f"Decision: `{report.decision}`",
        "",
        "Maintainer-review aid only. This is not release, production, or pilot approval.",
        "No live operation, external call, release, or deployment was attempted.",
        "",
    ]


def render_final_public_readiness_markdown(report: FinalPublicReadinessReport) -> str:
    lines = _header("Final public repository readiness", report)
    lines.extend(
        f"- {item.category}: {item.status} ({item.checks_passed}/{item.checks_total})"
        for item in report.requirements
    )
    return "\n".join(lines) + "\n"


def render_public_repo_checklist(report: FinalPublicReadinessReport) -> str:
    lines = _header("Public repository checklist", report)
    lines.extend(
        f"- [{'x' if item.status == 'passed' else ' '}] {item.category}"
        for item in report.requirements
    )
    lines.append("- [ ] Complete separate maintainer review before deciding next steps.")
    return "\n".join(lines) + "\n"


def render_maintainer_handoff_summary(report: FinalPublicReadinessReport) -> str:
    lines = _header("Maintainer handoff summary", report)
    lines.extend(
        [
            "- Run `make quality`.",
            "- Run `make safety-check`.",
            "- Run `make docs-site-check`.",
            "- Run `make release-readiness`.",
            "- Review known limitations and preserve the public/private boundary.",
            "- Decide any private Sandbox/Pilot work separately.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_final_audit_summary(report: FinalPublicReadinessReport) -> str:
    lines = _header("Final audit summary", report)
    lines.extend(
        [
            f"- Categories: {report.categories_total}",
            f"- Ready: {report.categories_ready}",
            f"- Needs review: {report.categories_needing_review}",
            f"- Blocked: {report.categories_blocked}",
            "- Private values and real reports remain outside Git.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_final_public_readiness_artifacts(
    report: FinalPublicReadinessReport, output_root: Path
) -> FinalPublicReadinessArtifactResult:
    temporary_absolute = (
        output_root.is_absolute()
        and output_root.name.startswith("procore-intake-bridge-final-readiness-")
        and (output_root.parent == Path("/tmp") or "pytest-" in output_root.as_posix())
    )
    if ".." in output_root.parts or (output_root.is_absolute() and not temporary_absolute):
        raise FinalPublicReadinessBlockedError("Final readiness output root is unsafe.")
    if not temporary_absolute and output_root.parts[:1] not in {
        (name,) for name in SAFE_OUTPUT_ROOTS
    }:
        raise FinalPublicReadinessBlockedError(
            "Final readiness output root is not approved."
        )
    validate_final_public_readiness_report_safe(report)
    output_root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "final-readiness-report.json": json.dumps(
            report.model_dump(mode="json"), indent=2, sort_keys=True
        )
        + "\n",
        "final-readiness-report.md": render_final_public_readiness_markdown(report),
        "public-repo-checklist.md": render_public_repo_checklist(report),
        "maintainer-handoff.md": render_maintainer_handoff_summary(report),
        "final-audit-summary.md": render_final_audit_summary(report),
        "manifest.json": json.dumps(
            {
                "files": ARTIFACT_FILES,
                "live_operations": False,
                "external_calls": False,
                "release_attempted": False,
                "deployment_attempted": False,
                "private_values_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in rendered.items():
        (output_root / name).write_text(content, encoding="utf-8")
    return FinalPublicReadinessArtifactResult(
        output_directory=output_root.name,
        files=ARTIFACT_FILES,
    )
