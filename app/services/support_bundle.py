import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.operator_diagnostics import (
    OperatorDiagnosticsReport,
    SupportBundleFileManifestItem,
    SupportBundleRedactionReport,
    SupportBundleResult,
)
from app.services.diagnostic_redaction import (
    contains_sensitive_material,
    detect_sensitive_patterns,
)
from app.services.operator_diagnostics import build_operator_diagnostics_report

EXPECTED_FILES = {
    "diagnostics.json",
    "diagnostics.md",
    "redaction-report.json",
    "manifest.json",
}


class SupportBundleError(RuntimeError):
    """A sanitized local support bundle operation failed."""


class SupportBundleBlockedError(SupportBundleError):
    """Support bundle safety gates blocked local generation."""


def render_support_bundle_markdown(report: OperatorDiagnosticsReport) -> str:
    counts = report.database.table_counts
    count_lines = "\n".join(f"- {name}: {count}" for name, count in sorted(counts.items()))
    sections = "\n".join(
        f"- {section.name}: {section.status}" for section in report.sections
    )
    return f"""# Sanitized operator diagnostics

- Generated: {report.generated_at.isoformat()}
- Environment: {report.environment}
- Application version: {report.app_version}
- External calls: false
- Procore calls: false
- Values exposed: false
- Raw logs, database files, attachments, and payloads included: false

## Aggregate database counts

{count_lines or "- Unavailable"}

## Queue counts

- Pending: {report.queue.pending}
- Failed: {report.queue.failed}
- Done: {report.queue.done}
- Skipped: {report.queue.skipped}

## Readiness summaries

{sections}

This local support artifact contains aggregate posture only. It is not production monitoring,
security certification, or authorization to share private operational data.
"""


def build_support_bundle_manifest(
    directory: Path, names: list[str]
) -> list[SupportBundleFileManifestItem]:
    items = []
    for name in sorted(names):
        content = (directory / name).read_bytes()
        items.append(SupportBundleFileManifestItem(
            name=name,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        ))
    return items


def check_support_bundle_redaction(path: Path) -> SupportBundleRedactionReport:
    if not path.exists():
        raise SupportBundleBlockedError("Support bundle path does not exist.")
    files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
    issue_types = set()
    for file in files:
        if file.suffix.casefold() in {".db", ".sqlite", ".sqlite3", ".log"}:
            issue_types.add("forbidden_file_type")
            continue
        try:
            text = file.read_text()
        except UnicodeDecodeError:
            issue_types.add("binary_file")
            continue
        issue_types.update(detect_sensitive_patterns(text))
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = text
        if contains_sensitive_material(parsed):
            issue_types.add("sensitive_material")
    return SupportBundleRedactionReport(
        safe=not issue_types,
        files_checked=len(files),
        issues_count=len(issue_types),
        issue_types=sorted(issue_types),
    )


def validate_support_bundle_files_safe(directory: Path) -> None:
    names = {item.name for item in directory.iterdir() if item.is_file()}
    if not names.issubset(EXPECTED_FILES):
        raise SupportBundleBlockedError("Support bundle contains an unexpected file.")
    result = check_support_bundle_redaction(directory)
    if not result.safe:
        raise SupportBundleBlockedError(
            "Support bundle failed redaction validation; issue values were suppressed."
        )


def _safe_output_directory(output_root: Path) -> Path:
    if output_root in {Path("."), Path("/")} or ".." in output_root.parts:
        raise SupportBundleBlockedError("Support bundle output path is unsafe.")
    root = output_root.resolve()
    directory = root / "support-bundle"
    if not directory.is_relative_to(root):
        raise SupportBundleBlockedError("Support bundle output escaped its configured root.")
    return directory


def write_support_bundle_files(
    report: OperatorDiagnosticsReport,
    output_root: Path,
    *,
    include_markdown: bool = True,
    include_json: bool = True,
    max_files: int = 10,
) -> SupportBundleResult:
    directory = _safe_output_directory(output_root)
    directory.mkdir(parents=True, exist_ok=True)
    contents = {}
    if include_json:
        contents["diagnostics.json"] = report.model_dump_json(indent=2) + "\n"
    if include_markdown:
        contents["diagnostics.md"] = render_support_bundle_markdown(report)
    redaction = SupportBundleRedactionReport(
        safe=True, files_checked=len(contents), issues_count=0
    )
    contents["redaction-report.json"] = redaction.model_dump_json(indent=2) + "\n"
    if len(contents) + 1 > max_files:
        raise SupportBundleBlockedError("Support bundle file count exceeds the configured cap.")
    for name, content in contents.items():
        (directory / name).write_text(content)
    manifest = build_support_bundle_manifest(directory, list(contents))
    (directory / "manifest.json").write_text(
        json.dumps(
            {"files": [item.model_dump() for item in manifest]},
            indent=2,
            sort_keys=True,
        ) + "\n"
    )
    validate_support_bundle_files_safe(directory)
    return SupportBundleResult(
        output_directory=directory.name,
        files=sorted(EXPECTED_FILES),
        manifest=manifest,
    )


def build_support_bundle(
    settings: Settings,
    db_session: Session | None = None,
    app: FastAPI | None = None,
    output_root: Path | None = None,
    include_markdown: bool = True,
    include_json: bool = True,
) -> SupportBundleResult:
    if not settings.support_bundle_enabled:
        raise SupportBundleBlockedError("Support bundle generation is disabled.")
    if (
        settings.support_bundle_include_raw_logs
        or settings.support_bundle_include_db_file
        or settings.support_bundle_include_attachments
        or settings.support_bundle_include_payloads
    ):
        raise SupportBundleBlockedError(
            "Support bundle generation blocked by unsafe inclusion settings."
        )
    report = build_operator_diagnostics_report(settings, db_session, app)
    return write_support_bundle_files(
        report,
        output_root or settings.support_bundle_output_root,
        include_markdown=include_markdown and settings.support_bundle_write_markdown,
        include_json=include_json and settings.support_bundle_write_json,
        max_files=settings.support_bundle_max_files,
    )
