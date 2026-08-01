import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.docs_site_polish import (
    DocsAudiencePath,
    DocsLinkInventoryItem,
    DocsNavigationGroup,
    DocsNavigationMapItem,
    DocsPageClass,
    DocsPageItem,
    DocsReaderPathItem,
    DocsSiteArtifactResult,
    DocsSiteChecklistItem,
    DocsSiteDecision,
    DocsSiteFinding,
    DocsSitePolishReport,
    DocsSitePolishStatus,
)
from app.services.hosted_ui_review import sanitize_hosted_ui_value
from scripts.check_docs_site import check_docs_site


class DocsSitePolishError(ValueError):
    pass


class DocsSitePolishBlockedError(DocsSitePolishError):
    pass


REQUIRED_CONTROLS = (
    "docs_site_polish_require_local_only",
    "docs_site_polish_require_nav_groups",
    "docs_site_polish_require_reader_paths",
    "docs_site_polish_require_no_hosting_automation",
    "docs_site_polish_require_no_external_analytics",
    "docs_site_polish_require_no_external_assets",
    "docs_site_polish_require_generated_output_ignores",
)
CORE_NAV_DOCS = {
    "local-installer-guide.md",
    "setup-experience-review.md",
    "demo-data-seed-reset.md",
    "demo-seed-plan.md",
    "api-docs-review.md",
    "api-route-reference.md",
    "hosted-ui-preparation.md",
    "hosted-ui-page-inventory.md",
    "hosted-ui-readiness-checklist.md",
    "hosted-ui-private-gates.md",
}
SECURITY_NAV_DOCS = {
    "security-threat-model.md",
    "auth-permission-boundary-audit.md",
    "webhook-replay-signature-hardening.md",
    "data-retention-redaction-policy.md",
    "secrets-storage-db-security-review.md",
    "dependency-supply-chain-security.md",
    "incident-response-forensics.md",
    "final-security-readiness-review.md",
    "security-gap-closeout.md",
}
PRODUCT_NAV_DOCS = {
    "intake-review-workspace.md",
    "intake-lifecycle-status-flow.md",
    "operator-triage-queue.md",
    "attachment-review-manifest-ux.md",
    "operator-export-pack.md",
    "product-dashboard.md",
    "demo-product-walkthrough.md",
}
REQUIRED_IGNORES = (
    "docs-site-polish-output/",
    "docs-site-review-output/",
    "docs-navigation-output/",
    "docs-reader-path-output/",
    "docs-link-check-output/",
    "*.docs-site-polish-report.json",
    "*.docs-site-polish-report.md",
    "*.docs-reader-paths.md",
    "*.docs-navigation-map.md",
    "*.docs-site-checklist.md",
    "*.docs-link-inventory.csv",
)
ARTIFACT_FILES = (
    "docs-site-polish-report.json",
    "docs-site-polish-report.md",
    "docs-reader-paths.md",
    "docs-navigation-map.md",
    "docs-site-checklist.md",
    "docs-link-inventory.csv",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "docs-site-polish-output",
    "docs-site-review-output",
    "docs-navigation-output",
    "docs-reader-path-output",
    "docs-link-check-output",
}
NAV_GROUP_PATTERN = re.compile(r"^\s{2}-\s+([^:\n]+):\s*$")
NAV_ITEM_PATTERN = re.compile(r"^\s{6}-\s+([^:\n]+):\s+([A-Za-z0-9_./-]+\.md)\s*$")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
EXTERNAL_CONFIG_PATTERN = re.compile(
    r"(?im)^\s*(?:google_analytics|analytics|extra_javascript|extra_css|"
    r"external_search|search_service|cdn_assets)\s*:"
)
HOSTING_WORKFLOW_PATTERN = re.compile(
    r"(?i)(?:mkdocs\s+gh-deploy|gh-pages|pages\s+deploy|deploy[-_ ]docs)"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance) certified\b|"
    r"\b(?:gdpr|ccpa|hipaa|privacy|legally) compliant\b"
)
NEGATED_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:not|no|does not|do not|never|without|cannot|isn't|is not|"
    r"doesn't|out of scope|requires separate)\b"
)


def sanitize_docs_site_value(value: Any) -> str:
    return sanitize_hosted_ui_value(value)


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _validate_settings(settings: Settings) -> None:
    if not _setting(settings, "docs_site_polish_enabled", True):
        raise DocsSitePolishBlockedError("Documentation-site polish review is disabled.")
    if not _setting(settings, "docs_site_polish_fail_closed", True):
        raise DocsSitePolishBlockedError("Documentation-site polish must remain fail closed.")
    if not all(bool(_setting(settings, name, True)) for name in REQUIRED_CONTROLS):
        raise DocsSitePolishBlockedError("A required documentation-site control is disabled.")
    allow_settings = (
        "docs_site_polish_allow_real_identities",
        "docs_site_polish_allow_real_domains",
        "docs_site_polish_allow_real_urls",
        "docs_site_polish_allow_report_contents",
        "docs_site_polish_allow_private_paths",
    )
    if any(bool(_setting(settings, name, False)) for name in allow_settings):
        raise DocsSitePolishBlockedError("Unsafe documentation-site material is enabled.")


def _classify_page(path: Path) -> tuple[DocsPageClass, DocsNavigationGroup]:
    name = path.name.casefold()
    if name == "index.md":
        return DocsPageClass.LANDING, DocsNavigationGroup.START_HERE
    if any(term in name for term in ("installer", "setup", "first-run", "quickstart")):
        return DocsPageClass.SETUP, DocsNavigationGroup.SETUP_AND_DEMO
    if any(term in name for term in ("demo", "walkthrough")):
        return DocsPageClass.DEMO, DocsNavigationGroup.EXAMPLES_AND_WALKTHROUGHS
    if any(
        term in name
        for term in (
            "intake-review",
            "lifecycle",
            "triage",
            "attachment-review",
            "product-dashboard",
        )
    ):
        return DocsPageClass.PRODUCT, DocsNavigationGroup.PRODUCT_UI
    if any(term in name for term in ("api-", "openapi")):
        return DocsPageClass.API, DocsNavigationGroup.API_REFERENCE
    if any(
        term in name
        for term in ("security", "auth-", "permission", "redaction", "forensic", "incident")
    ):
        return DocsPageClass.SECURITY, DocsNavigationGroup.SECURITY_AND_READINESS
    if any(term in name for term in ("hosted", "deployment", "https", "tls", "cloud")):
        return DocsPageClass.HOSTED, DocsNavigationGroup.HOSTED_PREPARATION
    if any(term in name for term in ("release", "roadmap", "project-status", "handoff")):
        return DocsPageClass.RELEASE, DocsNavigationGroup.RELEASE_AND_MAINTENANCE
    if any(term in name for term in ("operation", "diagnostic", "migration", "backup", "webhook")):
        return DocsPageClass.OPERATIONS, DocsNavigationGroup.OPERATIONS
    if any(term in name for term in ("sandbox", "pilot", "evidence")):
        return DocsPageClass.REFERENCE, DocsNavigationGroup.SANDBOX_AND_PILOT
    return DocsPageClass.REFERENCE, DocsNavigationGroup.RELEASE_AND_MAINTENANCE


def _title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return sanitize_docs_site_value(line[2:])
    except (OSError, UnicodeError):
        pass
    return path.stem.replace("-", " ").title()


def collect_docs_pages(settings: Settings) -> list[DocsPageItem]:
    _validate_settings(settings)
    paths = sorted(path for path in Path("docs").rglob("*.md") if path.is_file())
    maximum = int(_setting(settings, "docs_site_polish_max_docs", 400))
    if len(paths) > maximum:
        raise DocsSitePolishBlockedError("Documentation count exceeds the configured limit.")
    nav_docs = {item.document for item in collect_mkdocs_nav(settings)}
    required = (
        CORE_NAV_DOCS
        | SECURITY_NAV_DOCS
        | PRODUCT_NAV_DOCS
        | {
            "index.md",
            "docs-navigation.md",
        }
    )
    pages = []
    for path in paths:
        page_class, group = _classify_page(path)
        relative = path.relative_to("docs").as_posix()
        pages.append(
            DocsPageItem(
                path=relative,
                title=_title(path),
                page_class=page_class,
                navigation_group=group,
                in_mkdocs_nav=relative in nav_docs,
                core_document=relative in required,
            )
        )
    return pages


def collect_mkdocs_nav(settings: Settings) -> list[DocsNavigationMapItem]:
    _validate_settings(settings)
    config_path = Path("mkdocs.yml")
    if not config_path.is_file():
        return []
    config = config_path.read_text(encoding="utf-8")
    items: list[DocsNavigationMapItem] = []
    order = 0
    for line in config.splitlines():
        group_match = NAV_GROUP_PATTERN.match(line)
        if group_match:
            continue
        item_match = NAV_ITEM_PATTERN.match(line)
        if not item_match:
            continue
        order += 1
        label, document = item_match.groups()
        page_class, normalized_group = _classify_page(Path(document))
        items.append(
            DocsNavigationMapItem(
                group=normalized_group,
                label=sanitize_docs_site_value(label),
                document=document,
                page_class=page_class,
                order=order,
                target_exists=(Path("docs") / document).is_file(),
            )
        )
    return items


def build_docs_audience_paths(settings: Settings) -> list[DocsReaderPathItem]:
    _validate_settings(settings)
    rows = (
        (
            DocsAudiencePath.FIRST_TIME_EVALUATOR,
            "First-time evaluator",
            "Understand scope, safety, setup, and the local Demo.",
            ["index.md", "quickstart-site.md", "local-installer-guide.md"],
        ),
        (
            DocsAudiencePath.DEMO_USER,
            "Demo user",
            "Prepare fake local data and walk through product surfaces.",
            ["demo-data-seed-reset.md", "demo-product-walkthrough.md", "product-dashboard.md"],
        ),
        (
            DocsAudiencePath.SANDBOX_PREPARER,
            "Sandbox preparer",
            "Review the separately gated sandbox preparation path.",
            ["sandbox-mode.md", "sandbox-read-validation.md", "sandbox-evidence-linkage.md"],
        ),
        (
            DocsAudiencePath.PILOT_PREPARER,
            "Pilot preparer",
            "Review private pilot prerequisites without granting approval.",
            ["pilot-mode.md", "pilot-readiness-gate.md", "private-workspace-bootstrap.md"],
        ),
        (
            DocsAudiencePath.HOSTED_PREPARER,
            "Hosted preparer",
            "Review hosted planning and private gates without deployment.",
            [
                "hosted-ui-preparation.md",
                "hosted-deployment-templates.md",
                "hosted-ui-private-gates.md",
            ],
        ),
        (
            DocsAudiencePath.SECURITY_REVIEWER,
            "Security reviewer",
            "Trace public security boundaries and required private review.",
            [
                "security-threat-model.md",
                "final-security-readiness-review.md",
                "security-gap-closeout.md",
            ],
        ),
        (
            DocsAudiencePath.OPERATOR_USER,
            "Operator user",
            "Review local operational and diagnostic guidance.",
            ["operations-runbook.md", "operator-diagnostics.md", "command-reference.md"],
        ),
        (
            DocsAudiencePath.MAINTAINER_RELEASE_REVIEWER,
            "Maintainer release reviewer",
            "Review readiness and release boundaries without publishing.",
            ["final-public-readiness.md", "release-readiness.md", "project-status.md"],
        ),
        (
            DocsAudiencePath.DEVELOPER_CONTRIBUTOR,
            "Developer contributor",
            "Locate commands, API boundaries, and documentation navigation.",
            ["command-reference.md", "api-route-reference.md", "docs-navigation.md"],
        ),
    )
    return [
        DocsReaderPathItem(
            audience=audience,
            title=title,
            description=description,
            documents=documents,
        )
        for audience, title, description, documents in rows
    ]


def build_docs_navigation_groups(settings: Settings) -> list[DocsNavigationGroup]:
    _validate_settings(settings)
    return list(DocsNavigationGroup)


def build_docs_navigation_map(settings: Settings) -> list[DocsNavigationMapItem]:
    return collect_mkdocs_nav(settings)


def _hosting_automation_present() -> bool:
    workflow_root = Path(".github/workflows")
    if not workflow_root.is_dir():
        return False
    for path in workflow_root.iterdir():
        if path.is_file() and HOSTING_WORKFLOW_PATTERN.search(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            return True
    return False


def _local_preview_documented() -> bool:
    candidates = (Path("docs/docs-site.md"), Path("docs/docs-navigation.md"), Path("README.md"))
    return any(
        path.is_file()
        and any(
            marker in path.read_text(encoding="utf-8").casefold()
            for marker in ("docs-preview-instructions", "mkdocs serve", "local preview")
        )
        for path in candidates
    )


def build_docs_site_checklist(settings: Settings) -> list[DocsSiteChecklistItem]:
    _validate_settings(settings)
    nav = collect_mkdocs_nav(settings)
    nav_docs = {item.document for item in nav}
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    config = Path("mkdocs.yml").read_text(encoding="utf-8") if Path("mkdocs.yml").is_file() else ""
    checks = (
        ("mkdocs", "MkDocs configuration exists.", Path("mkdocs.yml").is_file(), "mkdocs.yml"),
        (
            "landing",
            "Documentation landing page exists.",
            Path("docs/index.md").is_file(),
            "docs/index.md",
        ),
        (
            "navigation",
            "Navigation guide exists.",
            Path("docs/docs-navigation.md").is_file(),
            "docs/docs-navigation.md",
        ),
        (
            "core_nav",
            "J1 through J4 core docs are navigable.",
            CORE_NAV_DOCS <= nav_docs,
            "MkDocs nav",
        ),
        (
            "security_nav",
            "I1 through I9 security docs are navigable.",
            SECURITY_NAV_DOCS <= nav_docs,
            "MkDocs nav",
        ),
        (
            "product_nav",
            "H3 through H9 product docs are navigable.",
            PRODUCT_NAV_DOCS <= nav_docs,
            "MkDocs nav",
        ),
        (
            "preview",
            "Local preview guidance is documented.",
            _local_preview_documented(),
            "Local docs guidance",
        ),
        (
            "hosting",
            "No docs hosting automation is present.",
            not _hosting_automation_present(),
            "Workflow inspection",
        ),
        (
            "analytics",
            "No external analytics or assets are configured.",
            not EXTERNAL_CONFIG_PATTERN.search(config),
            "MkDocs config",
        ),
        (
            "ignores",
            "Generated J5 outputs are ignored.",
            all(item in gitignore for item in REQUIRED_IGNORES),
            ".gitignore",
        ),
    )
    return [
        DocsSiteChecklistItem(
            code=code,
            description=description,
            passed=bool(passed),
            evidence=evidence,
            blocker=not bool(passed),
        )
        for code, description, passed, evidence in checks
    ]


def _resolve_link(source: Path, target: str) -> tuple[bool, bool]:
    clean = target.split("#", 1)[0]
    if not clean:
        return True, True
    if clean.startswith(("http://", "https://", "mailto:", "tel:")):
        return False, False
    if clean.startswith("/") and not clean.endswith(".md"):
        return False, False
    candidate = (source.parent / clean).resolve()
    root = Path.cwd().resolve()
    if root not in candidate.parents and candidate != root:
        return True, False
    return True, candidate.is_file()


def build_docs_link_inventory(settings: Settings) -> list[DocsLinkInventoryItem]:
    pages = collect_docs_pages(settings)
    items: list[DocsLinkInventoryItem] = []
    for page in pages:
        source = Path("docs") / page.path
        text = source.read_text(encoding="utf-8")
        for label, raw_target in MARKDOWN_LINK_PATTERN.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            internal, exists = _resolve_link(source, target)
            if not internal:
                continue
            items.append(
                DocsLinkInventoryItem(
                    source=page.path,
                    label=sanitize_docs_site_value(label),
                    target=target,
                    internal=True,
                    target_exists=exists,
                    anchor_only=target.startswith("#"),
                )
            )
    return items


def build_docs_site_polish_report(settings: Settings) -> DocsSitePolishReport:
    pages = collect_docs_pages(settings)
    reader_paths = build_docs_audience_paths(settings)
    nav_groups = build_docs_navigation_groups(settings)
    navigation_map = build_docs_navigation_map(settings)
    checklist = build_docs_site_checklist(settings)
    links = build_docs_link_inventory(settings)
    findings = [
        DocsSiteFinding(
            code=item.code,
            message=item.description,
            severity="blocker",
            document=item.evidence,
        )
        for item in checklist
        if item.blocker
    ]
    findings.extend(
        DocsSiteFinding(
            code="broken_internal_link",
            message="An internal documentation link target was not found.",
            severity="warning",
            document=item.source,
        )
        for item in links
        if not item.target_exists
    )
    existing_checker_failures = [
        finding for finding in check_docs_site(Path.cwd()) if finding.level == "FAIL"
    ]
    findings.extend(
        DocsSiteFinding(
            code="docs_site_checker",
            message=finding.message,
            severity="blocker",
            document=finding.check,
        )
        for finding in existing_checker_failures
    )
    maximum = int(_setting(settings, "docs_site_polish_max_findings", 300))
    if len(findings) > maximum:
        raise DocsSitePolishBlockedError("Documentation findings exceed the configured limit.")
    blockers = [finding.message for finding in findings if finding.severity == "blocker"]
    config = Path("mkdocs.yml").read_text(encoding="utf-8") if Path("mkdocs.yml").is_file() else ""
    external_config = bool(EXTERNAL_CONFIG_PATTERN.search(config))
    report = DocsSitePolishReport(
        status=DocsSitePolishStatus.BLOCKED if blockers else DocsSitePolishStatus.READY,
        decision=(
            DocsSiteDecision.BLOCKED if blockers else DocsSiteDecision.READY_FOR_MAINTAINER_REVIEW
        ),
        pages=pages,
        reader_paths=reader_paths,
        navigation_map=navigation_map,
        link_inventory=links,
        checklist=checklist,
        docs_total=len(pages),
        nav_groups_total=len(nav_groups),
        audience_paths_total=len(reader_paths),
        checklist_items_total=len(checklist),
        findings=findings,
        blockers=blockers,
        warnings=[
            "Local docs-site polish does not approve production, pilot, release, or deployment."
        ],
        mkdocs_config_present=Path("mkdocs.yml").is_file(),
        nav_structure_present=bool(navigation_map)
        and not any(not item.target_exists for item in navigation_map),
        reader_paths_present=len(reader_paths) == len(DocsAudiencePath),
        local_preview_documented=_local_preview_documented(),
        hosting_automation_present=_hosting_automation_present(),
        external_analytics_present=external_config,
        external_assets_present=external_config,
        recommended_next_steps=[
            "Review the local reader paths and navigation map.",
            "Use documented local preview instructions only when a maintainer chooses.",
            "Keep docs hosting, publishing, and deployment separately gated.",
        ],
    )
    validate_docs_site_polish_report_safe(report)
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


def validate_docs_site_polish_report_safe(report: DocsSitePolishReport) -> None:
    unsafe_flags = (
        not report.local_only,
        report.hosting_automation_present,
        report.external_analytics_present,
        report.external_assets_present,
        report.docs_deploy_attempted,
        report.external_call_attempted,
        report.github_api_attempted,
        report.package_build_attempted,
        report.release_attempted,
        report.deploy_attempted,
        report.workflow_changed,
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
        report.mkdocs_config_present,
        report.nav_structure_present,
        report.reader_paths_present,
        report.local_preview_documented,
    )
    if any(unsafe_flags) or not all(required) or report.blockers:
        raise DocsSitePolishBlockedError("The documentation-site polish review failed closed.")
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_docs_site_value(value) == "[redacted]":
            raise DocsSitePolishBlockedError("The documentation report contains unsafe material.")
        for match in UNSAFE_CLAIM_PATTERN.finditer(value):
            window = value[max(0, match.start() - 100) : match.end() + 20]
            if not NEGATED_CLAIM_PATTERN.search(window):
                raise DocsSitePolishBlockedError(
                    "The documentation report contains an approval or compliance claim."
                )


def render_docs_site_polish_markdown(report: DocsSitePolishReport) -> str:
    validate_docs_site_polish_report_safe(report)
    return "\n".join(
        (
            "# Documentation-site polish review",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Documents inventoried: {report.docs_total}",
            f"- Navigation groups: {report.nav_groups_total}",
            f"- Reader paths: {report.audience_paths_total}",
            "- Docs deployment attempted: false",
            "- External analytics or assets present: false",
            "",
            "This local-only review does not approve production, pilot, release, or deployment.",
            "",
        )
    )


def render_docs_reader_paths_markdown(report: DocsSitePolishReport) -> str:
    validate_docs_site_polish_report_safe(report)
    lines = ["# Documentation reader paths", "", "All paths are local-only.", ""]
    for path in report.reader_paths:
        lines.extend((f"## {path.title}", "", path.description, ""))
        lines.extend(f"- `{document}`" for document in path.documents)
        lines.append("")
    return "\n".join(lines)


def render_docs_navigation_map_markdown(report: DocsSitePolishReport) -> str:
    validate_docs_site_polish_report_safe(report)
    lines = [
        "# Documentation navigation map",
        "",
        "| Group | Label | Document | Page class |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.navigation_map:
        values = (item.group.value, item.label, item.document, item.page_class.value)
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines) + "\n"


def render_docs_site_checklist_markdown(report: DocsSitePolishReport) -> str:
    validate_docs_site_polish_report_safe(report)
    lines = ["# Documentation-site checklist", ""]
    for item in report.checklist:
        marker = "x" if item.passed else " "
        lines.append(f"- [{marker}] {item.description} Evidence: {item.evidence}.")
    return "\n".join(lines) + "\n"


def _csv_cell(value: Any) -> str:
    text = sanitize_docs_site_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_docs_link_inventory_csv(report: DocsSitePolishReport) -> str:
    validate_docs_site_polish_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("source", "label", "target", "internal", "target_exists"))
    for item in report.link_inventory:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.source,
                    item.label,
                    item.target,
                    item.internal,
                    item.target_exists,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if ".." in raw.parts:
        raise DocsSitePolishBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        (
            "/tmp/procore-intake-bridge-docs-site-polish-",
            "/private/tmp/procore-intake-bridge-docs-site-polish-",
        )
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise DocsSitePolishBlockedError("Output root is outside the docs-site polish boundary.")
    return resolved


def write_docs_site_polish_artifacts(
    report: DocsSitePolishReport, output_root: str | Path
) -> DocsSiteArtifactResult:
    validate_docs_site_polish_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "docs-site-polish-report.json": json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        "docs-site-polish-report.md": render_docs_site_polish_markdown(report),
        "docs-reader-paths.md": render_docs_reader_paths_markdown(report),
        "docs-navigation-map.md": render_docs_navigation_map_markdown(report),
        "docs-site-checklist.md": render_docs_site_checklist_markdown(report),
        "docs-link-inventory.csv": render_docs_link_inventory_csv(report),
    }
    rendered["manifest.json"] = (
        json.dumps(
            {
                "status": report.status.value,
                "files": list(ARTIFACT_FILES[:-1]),
                "sanitized": True,
                "live_operations": False,
                "docs_deployment": False,
            },
            indent=2,
        )
        + "\n"
    )
    for filename, contents in rendered.items():
        target = (root / filename).resolve()
        if target.parent != root:
            raise DocsSitePolishBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return DocsSiteArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=list(ARTIFACT_FILES),
    )
