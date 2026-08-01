import csv
import io
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.version_prep import (
    PackageMetadataItem,
    PackageMetadataStatus,
    ReleaseBoundaryChecklistItem,
    ReleaseBoundaryStatus,
    VersionPrepArtifactResult,
    VersionPrepDecision,
    VersionPrepFinding,
    VersionPrepReport,
    VersionPrepStatus,
    VersionReadinessMatrixItem,
    VersionSourceItem,
    VersionSourceType,
)
from app.services.docs_site_polish import sanitize_docs_site_value
from app.version import get_version


class VersionPrepError(ValueError):
    pass


class VersionPrepBlockedError(VersionPrepError):
    pass


REQUIRED_CONTROLS = (
    "version_prep_require_version_source",
    "version_prep_require_package_metadata",
    "version_prep_require_changelog_entry",
    "version_prep_require_release_boundary",
    "version_prep_require_no_build",
    "version_prep_require_no_publish",
    "version_prep_require_no_tag",
    "version_prep_require_no_deploy",
    "version_prep_require_no_workflow_changes",
)
REQUIRED_IGNORES = (
    "version-prep-output/",
    "package-metadata-output/",
    "release-prep-output/",
    "version-review-output/",
    "package-review-output/",
    "*.version-prep-report.json",
    "*.version-prep-report.md",
    "*.package-metadata-summary.md",
    "*.version-source-map.md",
    "*.release-boundary-checklist.md",
    "*.version-readiness-matrix.csv",
)
ARTIFACT_FILES = (
    "version-prep-report.json",
    "version-prep-report.md",
    "package-metadata-summary.md",
    "version-source-map.md",
    "release-boundary-checklist.md",
    "version-readiness-matrix.csv",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "version-prep-output",
    "package-metadata-output",
    "release-prep-output",
    "version-review-output",
    "package-review-output",
}
SEMANTIC_VERSION_PATTERN = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
FORBIDDEN_MAKE_TARGET_PATTERN = re.compile(
    r"(?m)^(?:build-package|docker-build|package-build|publish|tag|release|deploy)\s*:"
)
RELEASE_AUTOMATION_PATTERN = re.compile(
    r"(?i)(?:pypi|twine|hatch\s+publish|docker\s+(?:build|push)|gh\s+release|"
    r"create[-_ ]release|publish[-_ ]package)"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:package|version) (?:is )?published\b|\brelease (?:is )?complete\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance) certified\b|"
    r"\bprocore (?:endorsed|partner|certified|officially supported)\b"
)
NEGATED_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:not|no|does not|do not|never|without|cannot|isn't|is not|"
    r"doesn't|out of scope|requires separate|prepared|candidate)\b"
)


def sanitize_version_prep_value(value: Any) -> str:
    return sanitize_docs_site_value(value)


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _validate_settings(settings: Settings) -> str:
    if not _setting(settings, "version_prep_enabled", True):
        raise VersionPrepBlockedError("Version preparation review is disabled.")
    if not _setting(settings, "version_prep_fail_closed", True):
        raise VersionPrepBlockedError("Version preparation must remain fail closed.")
    if not all(bool(_setting(settings, name, True)) for name in REQUIRED_CONTROLS):
        raise VersionPrepBlockedError("A required version preparation control is disabled.")
    allow_settings = (
        "version_prep_allow_real_identities",
        "version_prep_allow_real_domains",
        "version_prep_allow_real_urls",
        "version_prep_allow_report_contents",
        "version_prep_allow_private_paths",
    )
    if any(bool(_setting(settings, name, False)) for name in allow_settings):
        raise VersionPrepBlockedError("Unsafe version preparation material is enabled.")
    target = str(_setting(settings, "version_prep_target_version", "0.1.0"))
    if not SEMANTIC_VERSION_PATTERN.fullmatch(target):
        raise VersionPrepBlockedError("The prepared target version is not valid semantic metadata.")
    return target


def _read(path: str | Path) -> str:
    candidate = Path(path)
    return candidate.read_text(encoding="utf-8") if candidate.is_file() else ""


def _pyproject() -> dict[str, Any]:
    path = Path("pyproject.toml")
    if not path.is_file():
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def collect_version_sources(settings: Settings) -> list[VersionSourceItem]:
    target = _validate_settings(settings)
    project = _pyproject().get("project", {})
    pyproject_version = str(project.get("version", ""))
    changelog = _read("CHANGELOG.md")
    project_status = _read("docs/project-status.md")
    release_readiness = _read("docs/release-readiness.md")
    changelog_present = target in changelog or "## Unreleased" in changelog
    rows = (
        (
            VersionSourceType.APP_VERSION_FILE,
            "app/version.py",
            get_version(),
            Path("app/version.py").is_file(),
            "Runtime version mirror kept consistent with project metadata.",
        ),
        (
            VersionSourceType.PYPROJECT_PROJECT_VERSION,
            "pyproject.toml",
            pyproject_version,
            bool(pyproject_version),
            "Canonical package project version.",
        ),
        (
            VersionSourceType.CHANGELOG_ENTRY,
            "CHANGELOG.md",
            target if changelog_present else "[not-declared]",
            changelog_present,
            "Unreleased or prepared-version changelog context.",
        ),
        (
            VersionSourceType.DOCS_PROJECT_STATUS,
            "docs/project-status.md",
            target if target in project_status else "[not-declared]",
            target in project_status,
            "Prepared target version in project status guidance.",
        ),
        (
            VersionSourceType.RELEASE_READINESS,
            "docs/release-readiness.md",
            target if target in release_readiness else "[not-declared]",
            target in release_readiness,
            "Release-candidate review guidance.",
        ),
        (
            VersionSourceType.PACKAGE_METADATA,
            "pyproject.toml project metadata",
            pyproject_version,
            bool(project),
            "Local package metadata; no package was built.",
        ),
    )
    return [
        VersionSourceItem(
            source_type=source_type,
            source=source,
            version=version,
            present=present,
            consistent_with_target=present and version == target,
            description=description,
        )
        for source_type, source, version, present, description in rows
    ]


def collect_package_metadata(settings: Settings) -> list[PackageMetadataItem]:
    _validate_settings(settings)
    data = _pyproject()
    project = data.get("project", {})
    build = data.get("build-system", {})
    wheel = (
        data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
    )
    rows = (
        ("name", project.get("name"), True, "Package distribution name."),
        ("version", project.get("version"), True, "Prepared package version metadata."),
        ("description", project.get("description"), True, "Short public package description."),
        ("readme", project.get("readme"), True, "Package long-description source."),
        ("requires-python", project.get("requires-python"), True, "Supported Python boundary."),
        ("dependencies", project.get("dependencies"), True, "Runtime dependency declarations."),
        ("build-backend", build.get("build-backend"), True, "Declared packaging backend."),
        ("wheel-packages", wheel.get("packages"), True, "Included Python package roots."),
        ("license", project.get("license"), False, "License metadata requires maintainer review."),
        ("authors", project.get("authors"), False, "Author metadata is optional for this review."),
        ("classifiers", project.get("classifiers"), False, "Classifiers remain optional metadata."),
        (
            "project-urls",
            project.get("urls"),
            False,
            "External project URLs are intentionally absent.",
        ),
    )
    items: list[PackageMetadataItem] = []
    for name, value, required, description in rows:
        if value not in (None, "", [], {}):
            status = PackageMetadataStatus.PRESENT
            rendered_value = (
                f"{len(value)} declared item(s)" if isinstance(value, (list, dict)) else str(value)
            )
        elif required:
            status = PackageMetadataStatus.MISSING
            rendered_value = "[missing]"
        elif name == "project-urls":
            status = PackageMetadataStatus.NOT_APPLICABLE
            rendered_value = "[intentionally-absent]"
        else:
            status = PackageMetadataStatus.NEEDS_REVIEW
            rendered_value = "[needs-review]"
        items.append(
            PackageMetadataItem(
                name=name,
                value=rendered_value,
                status=status,
                source="pyproject.toml",
                required=required,
                description=description,
            )
        )
    return items


def _release_automation_present() -> bool:
    root = Path(".github/workflows")
    if not root.is_dir():
        return False
    return any(
        path.is_file()
        and RELEASE_AUTOMATION_PATTERN.search(path.read_text(encoding="utf-8", errors="replace"))
        for path in root.iterdir()
    )


def build_release_boundary_checklist(
    settings: Settings,
) -> list[ReleaseBoundaryChecklistItem]:
    _validate_settings(settings)
    makefile = _read("Makefile")
    boundary_docs = "\n".join(
        _read(path)
        for path in (
            "README.md",
            "docs/release-readiness.md",
            "docs/final-public-readiness.md",
        )
    ).casefold()
    makefile_safe = not FORBIDDEN_MAKE_TARGET_PATTERN.search(makefile)
    workflow_safe = not _release_automation_present()
    documented = "does not" in boundary_docs or "no release" in boundary_docs
    rows = (
        ("package_build", "No package build is performed.", documented, "Release boundary docs"),
        (
            "docker_build",
            "No Docker image build is performed.",
            documented,
            "Release boundary docs",
        ),
        ("publish", "No package publication is performed.", documented, "Release boundary docs"),
        ("tag", "No version tag is created.", documented, "Release boundary docs"),
        ("release", "No release is created.", documented, "Release boundary docs"),
        (
            "deploy",
            "No application or docs deployment is performed.",
            documented,
            "Release boundary docs",
        ),
        (
            "makefile",
            "No build, publish, release, tag, or deploy target was added.",
            makefile_safe,
            "Makefile",
        ),
        (
            "workflow",
            "No release or publication workflow is present.",
            workflow_safe,
            "Local workflow files",
        ),
    )
    return [
        ReleaseBoundaryChecklistItem(
            code=code,
            description=description,
            status=(ReleaseBoundaryStatus.DOCUMENTED if passed else ReleaseBoundaryStatus.BLOCKED),
            evidence=evidence,
            operation_attempted=False,
        )
        for code, description, passed, evidence in rows
    ]


def build_version_readiness_matrix(settings: Settings) -> list[VersionReadinessMatrixItem]:
    sources = collect_version_sources(settings)
    metadata = collect_package_metadata(settings)
    boundaries = build_release_boundary_checklist(settings)
    target = _validate_settings(settings)
    rows = (
        (
            "version source",
            all(item.consistent_with_target for item in sources if item.present),
            "app/version.py and pyproject.toml",
            "Prepared metadata only; no released version is claimed.",
        ),
        (
            "package metadata",
            not any(
                item.required and item.status is PackageMetadataStatus.MISSING for item in metadata
            ),
            "pyproject.toml",
            "Optional license, author, and classifier metadata needs maintainer review.",
        ),
        (
            "changelog",
            any(
                item.source_type is VersionSourceType.CHANGELOG_ENTRY and item.present
                for item in sources
            ),
            "CHANGELOG.md",
            f"Target {target} remains prepared or unreleased metadata.",
        ),
        (
            "release boundary",
            all(item.status is ReleaseBoundaryStatus.DOCUMENTED for item in boundaries),
            "Release guidance and local automation inspection",
            "Build, publish, tag, release, and deployment remain out of scope.",
        ),
    )
    return [
        VersionReadinessMatrixItem(
            area=area,
            status="ready" if ready else "blocked",
            evidence=evidence,
            limitation=limitation,
            ready_for_candidate_review=ready,
        )
        for area, ready, evidence, limitation in rows
    ]


def build_version_prep_report(settings: Settings) -> VersionPrepReport:
    target = _validate_settings(settings)
    sources = collect_version_sources(settings)
    metadata = collect_package_metadata(settings)
    boundaries = build_release_boundary_checklist(settings)
    matrix = build_version_readiness_matrix(settings)
    version_present = any(
        item.source_type is VersionSourceType.PYPROJECT_PROJECT_VERSION and item.present
        for item in sources
    )
    versions_consistent = all(item.consistent_with_target for item in sources if item.present)
    metadata_present = not any(
        item.required and item.status is PackageMetadataStatus.MISSING for item in metadata
    )
    changelog_present = any(
        item.source_type is VersionSourceType.CHANGELOG_ENTRY and item.present for item in sources
    )
    boundary_documented = all(
        item.status is ReleaseBoundaryStatus.DOCUMENTED for item in boundaries
    )
    gitignore = _read(".gitignore")
    ignores_present = all(item in gitignore for item in REQUIRED_IGNORES)
    findings: list[VersionPrepFinding] = []
    blocker_rows = (
        ("version_source", version_present, "Canonical package version metadata is missing."),
        ("version_consistency", versions_consistent, "Declared version metadata is inconsistent."),
        ("package_metadata", metadata_present, "Required package metadata is missing."),
        ("changelog", changelog_present, "Prepared or unreleased changelog context is missing."),
        ("release_boundary", boundary_documented, "A release boundary is not documented."),
        ("generated_ignores", ignores_present, "Generated version-prep ignores are incomplete."),
    )
    for code, passed, message in blocker_rows:
        if not passed:
            findings.append(VersionPrepFinding(code=code, message=message, severity="blocker"))
    findings.extend(
        VersionPrepFinding(
            code=f"metadata_{item.name}",
            message=f"Optional package metadata needs maintainer review: {item.name}.",
            severity="warning",
            source=item.source,
        )
        for item in metadata
        if item.status is PackageMetadataStatus.NEEDS_REVIEW
    )
    maximum = int(_setting(settings, "version_prep_max_findings", 300))
    if len(findings) > maximum:
        raise VersionPrepBlockedError("Version preparation findings exceed the configured limit.")
    blockers = [finding.message for finding in findings if finding.severity == "blocker"]
    warnings = [finding.message for finding in findings if finding.severity == "warning"]
    report = VersionPrepReport(
        status=(
            VersionPrepStatus.BLOCKED
            if blockers
            else VersionPrepStatus.NEEDS_REVIEW
            if warnings
            else VersionPrepStatus.READY
        ),
        decision=(
            VersionPrepDecision.BLOCKED
            if blockers
            else VersionPrepDecision.NEEDS_REVIEW
            if warnings
            else VersionPrepDecision.READY_FOR_RELEASE_CANDIDATE_REVIEW
        ),
        target_version=target,
        version_sources=sources,
        package_metadata=metadata,
        release_boundary_checklist=boundaries,
        readiness_matrix=matrix,
        version_sources_total=len(sources),
        package_metadata_items_total=len(metadata),
        release_boundary_items_total=len(boundaries),
        findings=findings,
        blockers=blockers,
        warnings=warnings,
        version_source_present=version_present,
        package_metadata_present=metadata_present,
        changelog_entry_present=changelog_present,
        release_boundary_documented=boundary_documented,
        recommended_next_steps=[
            "Review optional package metadata and prepared version consistency.",
            "Complete a separate release-candidate review before any build or publication.",
            "Keep build, publish, tag, release, deployment, and workflows separately gated.",
        ],
    )
    validate_version_prep_report_safe(report)
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


def validate_version_prep_report_safe(report: VersionPrepReport) -> None:
    unsafe_flags = (
        report.package_build_attempted,
        report.docker_build_attempted,
        report.publish_attempted,
        report.tag_attempted,
        report.release_attempted,
        report.deploy_attempted,
        report.workflow_changed,
        report.github_api_attempted,
        report.package_registry_call_attempted,
        report.external_call_attempted,
        report.private_report_contents_exposed,
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
        report.production_approval_claimed,
        report.release_approval_claimed,
        report.pilot_approval_claimed,
        report.deployment_approval_claimed,
    )
    required = (
        report.version_source_present,
        report.package_metadata_present,
        report.changelog_entry_present,
        report.release_boundary_documented,
    )
    if any(unsafe_flags) or not all(required) or report.blockers:
        raise VersionPrepBlockedError("The version preparation review failed closed.")
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_version_prep_value(value) == "[redacted]":
            raise VersionPrepBlockedError(
                "The version preparation report contains unsafe material."
            )
        for match in UNSAFE_CLAIM_PATTERN.finditer(value):
            window = value[max(0, match.start() - 100) : match.end() + 20]
            if not NEGATED_CLAIM_PATTERN.search(window):
                raise VersionPrepBlockedError(
                    "The version preparation report contains an approval or release claim."
                )


def render_version_prep_report_markdown(report: VersionPrepReport) -> str:
    validate_version_prep_report_safe(report)
    return "\n".join(
        (
            "# Version preparation review",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Prepared target version: `{report.target_version}`",
            f"- Version sources: {report.version_sources_total}",
            f"- Package metadata items: {report.package_metadata_items_total}",
            "- Package or Docker build attempted: false",
            "- Publish, tag, release, or deployment attempted: false",
            "",
            "Prepared metadata is not a released version and grants no production, pilot, release, "
            "or deployment approval.",
            "",
        )
    )


def render_package_metadata_summary_markdown(report: VersionPrepReport) -> str:
    validate_version_prep_report_safe(report)
    lines = [
        "# Package metadata summary",
        "",
        "| Field | Status | Value | Source |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.package_metadata:
        values = (item.name, item.status.value, item.value, item.source)
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines) + "\n"


def render_version_source_map_markdown(report: VersionPrepReport) -> str:
    validate_version_prep_report_safe(report)
    lines = [
        "# Version source map",
        "",
        "`pyproject.toml` owns the package version; `app/version.py` is its runtime mirror.",
        "",
        "| Source type | Source | Version | Present | Consistent |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in report.version_sources:
        values = (
            item.source_type.value,
            item.source,
            item.version,
            str(item.present).lower(),
            str(item.consistent_with_target).lower(),
        )
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def render_release_boundary_checklist_markdown(report: VersionPrepReport) -> str:
    validate_version_prep_report_safe(report)
    lines = ["# Release boundary checklist", ""]
    for item in report.release_boundary_checklist:
        marker = "x" if item.status is ReleaseBoundaryStatus.DOCUMENTED else " "
        lines.append(f"- [{marker}] {item.description} Evidence: {item.evidence}.")
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_version_prep_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_version_readiness_matrix_csv(report: VersionPrepReport) -> str:
    validate_version_prep_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("area", "status", "evidence", "limitation", "candidate_review"))
    for item in report.readiness_matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.area,
                    item.status,
                    item.evidence,
                    item.limitation,
                    item.ready_for_candidate_review,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if ".." in raw.parts:
        raise VersionPrepBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        (
            "/tmp/procore-intake-bridge-version-prep-",
            "/private/tmp/procore-intake-bridge-version-prep-",
        )
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise VersionPrepBlockedError("Output root is outside the version-prep boundary.")
    return resolved


def write_version_prep_artifacts(
    report: VersionPrepReport, output_root: str | Path
) -> VersionPrepArtifactResult:
    validate_version_prep_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "version-prep-report.json": json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        "version-prep-report.md": render_version_prep_report_markdown(report),
        "package-metadata-summary.md": render_package_metadata_summary_markdown(report),
        "version-source-map.md": render_version_source_map_markdown(report),
        "release-boundary-checklist.md": render_release_boundary_checklist_markdown(report),
        "version-readiness-matrix.csv": render_version_readiness_matrix_csv(report),
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
            raise VersionPrepBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return VersionPrepArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=list(ARTIFACT_FILES),
    )
