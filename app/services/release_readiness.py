import json
import re
import tomllib
from pathlib import Path

from app.schemas.release_readiness import (
    ReleaseReadinessArtifactResult,
    ReleaseReadinessChecklist,
    ReleaseReadinessFinding,
    ReleaseReadinessReport,
    ReleaseReadinessRequirement,
    ReleaseReadinessStatus,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_NAMES = (
    "release-readiness-report.json",
    "release-readiness-summary.md",
    "release-notes-draft.md",
    "release-blockers.md",
    "maintainer-review-checklist.md",
    "manifest.json",
)
REQUIRED_CATEGORIES = (
    "repository safety",
    "public data safety",
    "command usability",
    "docs completeness",
    "mode clarity",
    "tests and quality",
    "route safety",
    "secret safety",
    "generated output safety",
    "examples and fixtures",
    "changelog",
    "version metadata",
    "packaging metadata",
    "release notes draft",
    "known limitations",
    "manual maintainer approval",
)
SENSITIVE = re.compile(
    r"(?i)(?:authorization\s*:|bearer\s+|(?:secret|token|password)\s*[:=]\s*\S+|"
    r"(?:/Users/|/home/[^/\s]+/|[A-Z]:\\Users\\)|"
    r"(?:postgres(?:ql)?|mysql|mariadb)://)"
)


class ReleaseReadinessError(RuntimeError):
    """A sanitized local release-readiness operation failed."""


def _exists(root: Path, *names: str) -> bool:
    return all((root / name).is_file() for name in names)


def _contains(root: Path, name: str, *phrases: str) -> bool:
    try:
        text = (root / name).read_text(encoding="utf-8").casefold()
    except (OSError, UnicodeError):
        return False
    return all(phrase.casefold() in text for phrase in phrases)


def _version(root: Path) -> str:
    try:
        with (root / "pyproject.toml").open("rb") as handle:
            value = tomllib.load(handle)["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        return "VERSION_PLACEHOLDER"
    return (
        str(value)
        if re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z0-9.-]+)?", str(value))
        else "VERSION_PLACEHOLDER"
    )


def build_release_readiness_checklist(root: Path = ROOT) -> ReleaseReadinessChecklist:
    checks = {
        "repository safety": _exists(root, "LICENSE", "SECURITY.md", "CONTRIBUTING.md"),
        "public data safety": _exists(root, "scripts/audit_public_safety.py"),
        "command usability": _exists(root, "scripts/print_command_guide.py", "Makefile"),
        "docs completeness": _exists(
            root,
            "README.md",
            "QUICKSTART.md",
            "docs/index.md",
            "docs/walkthrough-index.md",
        ),
        "mode clarity": _contains(root, "README.md", "demo mode", "sandbox mode", "pilot mode"),
        "tests and quality": _exists(root, "tests/conftest.py")
        and _contains(root, "Makefile", "quality:"),
        "route safety": _exists(root, "scripts/audit_routes_read_only.py"),
        "secret safety": _contains(root, "docs/safety-model.md", "secret", "must not be committed"),
        "generated output safety": _contains(
            root,
            ".gitignore",
            "private-workspace/",
            "release-readiness-output/",
        ),
        "examples and fixtures": _contains(root, "examples/README.md", "fake", "placeholder"),
        "changelog": _contains(root, "CHANGELOG.md", "unreleased"),
        "version metadata": _version(root) != "VERSION_PLACEHOLDER",
        "packaging metadata": _contains(
            root,
            "pyproject.toml",
            "[build-system]",
            "[project]",
            "name =",
            "version =",
        ),
        "release notes draft": _exists(root, "docs/release-notes-template.md"),
        "known limitations": _contains(
            root,
            "docs/project-status.md",
            "known limitations",
            "not production-ready",
        ),
    }
    requirements = [
        ReleaseReadinessRequirement(
            category=category,
            status=(
                ReleaseReadinessStatus.READY_FOR_MAINTAINER_REVIEW
                if checks[category]
                else ReleaseReadinessStatus.BLOCKED
            ),
            summary=(
                "Required public-safe material is present."
                if checks[category]
                else "Required public-safe material is missing or incomplete."
            ),
            blocking=not checks[category],
        )
        for category in REQUIRED_CATEGORIES
        if category != "manual maintainer approval"
    ]
    requirements.append(
        ReleaseReadinessRequirement(
            category="manual maintainer approval",
            status=ReleaseReadinessStatus.NEEDS_REVIEW,
            summary="A maintainer must review every check and decide any future release manually.",
        )
    )
    findings = (
        ReleaseReadinessFinding(
            code="manual_review_required",
            status=ReleaseReadinessStatus.NEEDS_REVIEW,
            message="This checklist never grants final release approval.",
        ),
    )
    return ReleaseReadinessChecklist(
        requirements=tuple(requirements),
        findings=findings,
    )


def build_release_readiness_report(root: Path = ROOT) -> ReleaseReadinessReport:
    checklist = build_release_readiness_checklist(root)
    if any(item.blocking for item in checklist.requirements):
        status = ReleaseReadinessStatus.BLOCKED
    elif any(
        item.status == ReleaseReadinessStatus.NEEDS_REVIEW
        for item in checklist.requirements
    ):
        status = ReleaseReadinessStatus.NEEDS_REVIEW
    else:
        status = ReleaseReadinessStatus.READY_FOR_MAINTAINER_REVIEW
    report = ReleaseReadinessReport(
        status=status,
        version=_version(root),
        checklist=checklist,
        known_limitations=(
            "Production security, operations, and tenant controls require independent review.",
            "A passing sandbox read probe is not production or pilot approval.",
            "Release publication, tags, packages, and deployment remain manual and out of scope.",
        ),
    )
    validate_release_readiness_report_safe(report)
    return report


def render_release_readiness_markdown(report: ReleaseReadinessReport) -> str:
    lines = [
        "# Release readiness summary",
        "",
        f"Status: **{report.status.value}**",
        f"Version metadata: `{report.version}`",
        "",
        "This is preparation for maintainer review, not final release approval.",
        "",
        "## Checklist",
        "",
    ]
    lines.extend(
        f"- {item.category}: {item.status.value} — {item.summary}"
        for item in report.checklist.requirements
    )
    lines.extend(("", "## Known limitations", ""))
    lines.extend(f"- {item}" for item in report.known_limitations)
    return "\n".join(lines) + "\n"


def render_release_notes_draft(report: ReleaseReadinessReport) -> str:
    return "\n".join(
        (
            "# Draft release notes",
            "",
            f"Version: {report.version}",
            "Status: DRAFT_PLACEHOLDER — maintainer review required",
            "",
            "## Public story",
            "",
            "- Read-only, local-first Procore intake planning and fixture workflows.",
            "- Separate Demo, private Sandbox, and controlled private Pilot guidance.",
            "- Public safety, route, usability, walkthrough, and release-readiness checks.",
            "",
            "## Known limitations",
            "",
            *(f"- {item}" for item in report.known_limitations),
            "",
            "This draft does not create or approve a release, tag, package, image, or deployment.",
        )
    ) + "\n"


def render_release_blockers_summary(report: ReleaseReadinessReport) -> str:
    blockers = [item for item in report.checklist.requirements if item.blocking]
    lines = ["# Release blockers", ""]
    if blockers:
        lines.extend(f"- {item.category}: {item.summary}" for item in blockers)
    else:
        lines.append("- No automated blockers; manual maintainer review is still required.")
    return "\n".join(lines) + "\n"


def render_maintainer_review_checklist(report: ReleaseReadinessReport) -> str:
    lines = ["# Maintainer review checklist", ""]
    lines.extend(f"- [ ] Review {item.category}." for item in report.checklist.requirements)
    lines.extend(
        (
            "- [ ] Confirm no private/generated artifacts are staged.",
            "- [ ] Decide separately whether a future manual tag or release is appropriate.",
            "",
            "Completion is a maintainer decision; this file records no approval.",
        )
    )
    return "\n".join(lines) + "\n"


def validate_release_readiness_report_safe(report: ReleaseReadinessReport) -> None:
    payload = report.model_dump_json()
    if (
        report.release_approved
        or report.release_created
        or report.tag_created
        or report.package_created
        or report.deployment_executed
        or report.external_calls
        or report.procore_calls
        or report.private_values_included
        or report.local_paths_included
        or SENSITIVE.search(payload)
    ):
        raise ReleaseReadinessError("Release readiness report failed public safety validation.")


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise ReleaseReadinessError("Release artifact generation blocked: unsafe output root.")
    if not output_root.is_absolute() and output_root.parts[0] != "release-readiness-output":
        raise ReleaseReadinessError(
            "Release artifact generation blocked: use release-readiness-output."
        )
    resolved = output_root.resolve()
    if resolved == ROOT.resolve():
        raise ReleaseReadinessError("Release artifact generation blocked: unsafe output root.")
    return resolved


def write_release_readiness_artifacts(
    report: ReleaseReadinessReport,
    output_root: Path,
) -> ReleaseReadinessArtifactResult:
    validate_release_readiness_report_safe(report)
    root = _safe_output_root(Path(output_root))
    root.mkdir(parents=True, exist_ok=False)
    files = {
        "release-readiness-report.json": json.dumps(
            report.model_dump(mode="json"), indent=2, sort_keys=True
        )
        + "\n",
        "release-readiness-summary.md": render_release_readiness_markdown(report),
        "release-notes-draft.md": render_release_notes_draft(report),
        "release-blockers.md": render_release_blockers_summary(report),
        "maintainer-review-checklist.md": render_maintainer_review_checklist(report),
        "manifest.json": json.dumps(
            {
                "files": list(ARTIFACT_NAMES),
                "release_created": False,
                "tag_created": False,
                "package_created": False,
                "deployment_executed": False,
                "external_calls": False,
                "private_values_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in files.items():
        if SENSITIVE.search(content):
            raise ReleaseReadinessError("Release artifact content failed safety validation.")
        (root / name).write_text(content, encoding="utf-8")
    return ReleaseReadinessArtifactResult(
        output_directory=root.name,
        files=ARTIFACT_NAMES,
    )
