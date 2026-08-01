import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.api_docs_review import (
    ApiProtectionType,
    ApiRouteDocumentationItem,
)
from app.schemas.hosted_ui_review import (
    HostedUiArtifactResult,
    HostedUiDecision,
    HostedUiFinding,
    HostedUiModeReadiness,
    HostedUiPageClass,
    HostedUiPageItem,
    HostedUiPrivateGate,
    HostedUiProtectionType,
    HostedUiReadinessChecklistItem,
    HostedUiReviewReport,
    HostedUiReviewStatus,
    HostedUiRouteItem,
    HostedUiSurface,
)
from app.services.api_docs_review import (
    build_api_route_reference,
    sanitize_api_docs_value,
)


class HostedUiReviewError(ValueError):
    pass


class HostedUiReviewBlockedError(HostedUiReviewError):
    pass


TEMPLATE_ROOT = Path("app/templates")
UI_ROUTE_PREFIXES = ("/admin", "/dashboard", "/review", "/deployment")
GUIDANCE_PAGES = (
    ("docs/operator-export-pack.md", HostedUiSurface.EXPORT_GUIDANCE),
    ("docs/local-installer-guide.md", HostedUiSurface.SETUP_GUIDANCE),
    ("docs/demo-product-walkthrough.md", HostedUiSurface.DEMO_WALKTHROUGH),
    ("docs/api-route-reference.md", HostedUiSurface.API_REFERENCE),
    ("docs/hosted-deployment-templates.md", HostedUiSurface.DEPLOYMENT_READINESS),
    ("docs/final-security-readiness-review.md", HostedUiSurface.SECURITY_READINESS),
    ("docs/security-gap-closeout.md", HostedUiSurface.SECURITY_READINESS),
)
REQUIRED_CONTROLS = (
    "hosted_ui_require_route_inventory",
    "hosted_ui_require_page_inventory",
    "hosted_ui_require_admin_protection",
    "hosted_ui_require_demo_safe_labels",
    "hosted_ui_require_metadata_only_attachments",
    "hosted_ui_require_no_file_serving",
    "hosted_ui_require_no_export_downloads",
    "hosted_ui_require_no_external_frontend_assets",
    "hosted_ui_require_private_review_gates",
)
FRONTEND_BUILD_FILES = (
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "vite.config.js",
    "vite.config.ts",
    "webpack.config.js",
    "rollup.config.js",
)
ARTIFACT_FILES = (
    "hosted-ui-review-report.json",
    "hosted-ui-review-report.md",
    "hosted-ui-page-inventory.md",
    "hosted-ui-route-matrix.csv",
    "hosted-ui-readiness-checklist.md",
    "hosted-ui-private-gates.md",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "hosted-ui-review-output",
    "hosted-ui-output",
    "ui-readiness-output",
    "hosted-page-review-output",
}
EXTERNAL_ASSET_PATTERN = re.compile(
    r"(?i)(?:src|href)\s*=\s*['\"](?:https?:)?//|@import\s+(?:url\()?['\"]?"
    r"(?:https?:)?//|url\(['\"]?(?:https?:)?//"
)
ANALYTICS_PATTERN = re.compile(
    r"(?i)(?:google-analytics|googletagmanager|segment\.com|mixpanel|amplitude|"
    r"tracking[-_ ]script|telemetry[-_ ]sdk)"
)
PRIVATE_CONTENT_PATTERN = re.compile(
    r"(?i)(?:private_report_contents|raw_log|raw_payload|db_dump_content|"
    r"backup_manifest|live_webhook_(?:headers|payload))\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+"
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


def sanitize_hosted_ui_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    sanitized = sanitize_api_docs_value(text)
    if sanitized == "[redacted]" or PRIVATE_CONTENT_PATTERN.search(text):
        return "[redacted]"
    return sanitized


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _validate_settings(settings: Settings) -> None:
    if not _setting(settings, "hosted_ui_review_enabled", True):
        raise HostedUiReviewBlockedError("Hosted UI review is disabled.")
    if not _setting(settings, "hosted_ui_fail_closed", True):
        raise HostedUiReviewBlockedError("Hosted UI review must remain fail closed.")
    if not all(bool(_setting(settings, name, True)) for name in REQUIRED_CONTROLS):
        raise HostedUiReviewBlockedError("A required hosted UI review control is disabled.")
    allow_settings = (
        "hosted_ui_allow_real_identities",
        "hosted_ui_allow_real_domains",
        "hosted_ui_allow_real_urls",
        "hosted_ui_allow_report_contents",
        "hosted_ui_allow_private_paths",
    )
    if any(bool(_setting(settings, name, False)) for name in allow_settings):
        raise HostedUiReviewBlockedError("Unsafe hosted UI review material is enabled.")


def collect_hosted_ui_routes(settings: Settings) -> list[ApiRouteDocumentationItem]:
    _validate_settings(settings)
    return [
        item
        for item in build_api_route_reference(settings)
        if item.path.startswith(UI_ROUTE_PREFIXES)
    ]


def collect_hosted_ui_templates(settings: Settings) -> list[Path]:
    _validate_settings(settings)
    templates = sorted(path for path in TEMPLATE_ROOT.rglob("*.html") if path.is_file())
    maximum = int(_setting(settings, "hosted_ui_max_pages", 200))
    if len(templates) + len(GUIDANCE_PAGES) > maximum:
        raise HostedUiReviewBlockedError("Hosted UI page count exceeds the configured limit.")
    return templates


def _page_source(page_or_template: str | Path) -> str:
    path = Path(page_or_template)
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def classify_hosted_ui_page(page_or_template: str | Path) -> HostedUiPageItem:
    source = _page_source(page_or_template)
    lowered = source.casefold()
    name = Path(source).stem.replace("_", " ").title()
    external_assets = False
    source_path = Path(source)
    if source_path.is_file() and source_path.suffix == ".html":
        contents = source_path.read_text(encoding="utf-8")
        external_assets = bool(
            EXTERNAL_ASSET_PATTERN.search(contents) or ANALYTICS_PATTERN.search(contents)
        )

    if "product_dashboard/" in lowered:
        surface = HostedUiSurface.PRODUCT_DASHBOARD
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        protection = HostedUiProtectionType.ADMIN_TOKEN_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_CANDIDATE
        purpose = "Protected product overview backed by local Demo metadata."
    elif "admin/" in lowered:
        surface = HostedUiSurface.ADMIN_DASHBOARD
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        protection = HostedUiProtectionType.ADMIN_TOKEN_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Protected administrative metadata view."
    elif "review/triage" in lowered:
        surface = HostedUiSurface.TRIAGE_QUEUE
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        protection = HostedUiProtectionType.ADMIN_TOKEN_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Protected local triage queue."
    elif "review/attachment" in lowered:
        surface = HostedUiSurface.ATTACHMENT_METADATA
        page_class = HostedUiPageClass.METADATA_ONLY
        protection = HostedUiProtectionType.METADATA_ONLY
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Protected attachment metadata view with no file serving."
    elif "review/history" in lowered or "review/detail" in lowered:
        surface = HostedUiSurface.LIFECYCLE_CONTROLS
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        protection = HostedUiProtectionType.ADMIN_TOKEN_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Protected local lifecycle status and history view."
    elif "review/" in lowered:
        surface = HostedUiSurface.REVIEW_WORKSPACE
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        protection = HostedUiProtectionType.ADMIN_TOKEN_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Protected intake review workspace."
    elif "operator-export" in lowered:
        surface = HostedUiSurface.EXPORT_GUIDANCE
        page_class = HostedUiPageClass.COMMAND_GUIDANCE_ONLY
        protection = HostedUiProtectionType.COMMAND_ONLY
        readiness = HostedUiModeReadiness.NOT_FOR_HOSTED_USE
        purpose = "Command-only export guidance; no web download is exposed."
    elif "installer" in lowered or "setup" in lowered:
        surface = HostedUiSurface.SETUP_GUIDANCE
        page_class = HostedUiPageClass.LOCAL_DEMO_SAFE
        protection = HostedUiProtectionType.LOCAL_ONLY
        readiness = HostedUiModeReadiness.DEMO_READY
        purpose = "Local setup and first-run guidance."
    elif "demo-product" in lowered:
        surface = HostedUiSurface.DEMO_WALKTHROUGH
        page_class = HostedUiPageClass.LOCAL_DEMO_SAFE
        protection = HostedUiProtectionType.LOCAL_ONLY
        readiness = HostedUiModeReadiness.DEMO_READY
        purpose = "Fake-data local Demo walkthrough."
    elif "api-route-reference" in lowered:
        surface = HostedUiSurface.API_REFERENCE
        page_class = HostedUiPageClass.LOCAL_DEMO_SAFE
        protection = HostedUiProtectionType.LOCAL_ONLY
        readiness = HostedUiModeReadiness.DEMO_READY
        purpose = "Offline route-reference guidance."
    elif "hosted-deployment" in lowered:
        surface = HostedUiSurface.DEPLOYMENT_READINESS
        page_class = HostedUiPageClass.PRIVATE_REVIEW_REQUIRED
        protection = HostedUiProtectionType.MANUAL_CONFIRMATION_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Hosted deployment planning guidance; no deployment is performed."
    elif "security" in lowered:
        surface = HostedUiSurface.SECURITY_READINESS
        page_class = HostedUiPageClass.PRIVATE_REVIEW_REQUIRED
        protection = HostedUiProtectionType.PRIVATE_WORKSPACE_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
        purpose = "Public-safe security guidance requiring separate private review."
    else:
        surface = HostedUiSurface.UNKNOWN
        page_class = HostedUiPageClass.UNKNOWN
        protection = HostedUiProtectionType.UNKNOWN
        readiness = HostedUiModeReadiness.UNKNOWN
        purpose = "Unclassified hosted UI page."

    return HostedUiPageItem(
        name=name,
        source=source,
        surface=surface,
        page_class=page_class,
        protection_type=protection,
        mode_readiness=readiness,
        purpose=purpose,
        demo_safe=readiness
        in {HostedUiModeReadiness.DEMO_READY, HostedUiModeReadiness.HOSTED_CANDIDATE},
        uses_local_demo_sqlite=surface
        in {
            HostedUiSurface.PRODUCT_DASHBOARD,
            HostedUiSurface.ADMIN_DASHBOARD,
            HostedUiSurface.REVIEW_WORKSPACE,
            HostedUiSurface.TRIAGE_QUEUE,
            HostedUiSurface.LIFECYCLE_CONTROLS,
            HostedUiSurface.ATTACHMENT_METADATA,
        },
        admin_protected=protection is HostedUiProtectionType.ADMIN_TOKEN_REQUIRED,
        metadata_only=surface is HostedUiSurface.ATTACHMENT_METADATA,
        command_guidance_only=surface is HostedUiSurface.EXPORT_GUIDANCE,
        external_frontend_assets=external_assets,
    )


def _hosted_protection(item: ApiRouteDocumentationItem) -> HostedUiProtectionType:
    mapping = {
        ApiProtectionType.INTENTIONALLY_PUBLIC: HostedUiProtectionType.INTENTIONALLY_PUBLIC,
        ApiProtectionType.ADMIN_TOKEN_REQUIRED: HostedUiProtectionType.ADMIN_TOKEN_REQUIRED,
        ApiProtectionType.LOCAL_ONLY: HostedUiProtectionType.LOCAL_ONLY,
        ApiProtectionType.DEMO_ONLY: HostedUiProtectionType.LOCAL_ONLY,
        ApiProtectionType.MANUAL_CONFIRMATION_REQUIRED: (
            HostedUiProtectionType.MANUAL_CONFIRMATION_REQUIRED
        ),
        ApiProtectionType.PRIVATE_WORKSPACE_REQUIRED: (
            HostedUiProtectionType.PRIVATE_WORKSPACE_REQUIRED
        ),
        ApiProtectionType.DISABLED_BY_DEFAULT: HostedUiProtectionType.DISABLED_BY_DEFAULT,
        ApiProtectionType.METADATA_ONLY: HostedUiProtectionType.METADATA_ONLY,
        ApiProtectionType.WEBHOOK_SIGNATURE_REQUIRED: HostedUiProtectionType.DISABLED_BY_DEFAULT,
        ApiProtectionType.UNKNOWN: HostedUiProtectionType.UNKNOWN,
    }
    return mapping[item.protection_type]


def classify_hosted_ui_route(route_item: ApiRouteDocumentationItem) -> HostedUiRouteItem:
    protection = _hosted_protection(route_item)
    path = route_item.path
    if path.startswith("/dashboard"):
        surface = HostedUiSurface.PRODUCT_DASHBOARD
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        readiness = HostedUiModeReadiness.HOSTED_CANDIDATE
    elif path.startswith("/admin"):
        surface = HostedUiSurface.ADMIN_DASHBOARD
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    elif "/triage" in path:
        surface = HostedUiSurface.TRIAGE_QUEUE
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    elif "/attachments" in path:
        surface = HostedUiSurface.ATTACHMENT_METADATA
        page_class = HostedUiPageClass.METADATA_ONLY
        protection = HostedUiProtectionType.METADATA_ONLY
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    elif path.endswith("/lifecycle") or "/lifecycle/" in path:
        surface = HostedUiSurface.LIFECYCLE_CONTROLS
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    elif path.startswith("/review"):
        surface = HostedUiSurface.REVIEW_WORKSPACE
        page_class = HostedUiPageClass.ADMIN_PROTECTED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    elif path.startswith("/deployment"):
        surface = HostedUiSurface.DEPLOYMENT_READINESS
        page_class = HostedUiPageClass.PRIVATE_REVIEW_REQUIRED
        readiness = HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
    else:
        surface = HostedUiSurface.UNKNOWN
        page_class = HostedUiPageClass.UNKNOWN
        readiness = HostedUiModeReadiness.UNKNOWN
    return HostedUiRouteItem(
        path=path,
        method=route_item.method,
        surface=surface,
        page_class=page_class,
        protection_type=protection,
        mode_readiness=readiness,
        purpose=route_item.purpose,
        admin_protected=route_item.admin_guard_present,
        local_only=(route_item.local_only or surface is HostedUiSurface.LIFECYCLE_CONTROLS),
        metadata_only=surface is HostedUiSurface.ATTACHMENT_METADATA,
        export_download=route_item.export_download,
        file_serving=route_item.serves_files,
        procore_write_back=route_item.procore_write_back,
    )


def build_hosted_ui_page_inventory(settings: Settings) -> list[HostedUiPageItem]:
    pages = [classify_hosted_ui_page(path) for path in collect_hosted_ui_templates(settings)]
    pages.extend(
        classify_hosted_ui_page(path) for path, _surface in GUIDANCE_PAGES if Path(path).is_file()
    )
    return pages


def build_hosted_ui_route_matrix(settings: Settings) -> list[HostedUiRouteItem]:
    return [classify_hosted_ui_route(item) for item in collect_hosted_ui_routes(settings)]


def build_hosted_ui_private_gates(settings: Settings) -> list[HostedUiPrivateGate]:
    _validate_settings(settings)
    rows = (
        (
            "private_auth",
            "Private authentication review",
            "Review hosted identity and access controls.",
        ),
        (
            "infrastructure",
            "Private infrastructure review",
            "Review hosting, network, and provider controls.",
        ),
        (
            "data_handling",
            "Private data review",
            "Review real data minimization and access boundaries.",
        ),
        (
            "attachment_storage",
            "Private attachment review",
            "Keep the UI metadata-only and review storage privately.",
        ),
        (
            "operations",
            "Private operations review",
            "Review monitoring, recovery, and operator ownership.",
        ),
        (
            "pilot_approval",
            "Separate pilot decision",
            "Complete a separate private pilot decision process.",
        ),
    )
    return [
        HostedUiPrivateGate(code=code, title=title, description=description)
        for code, title, description in rows
    ]


def build_hosted_ui_readiness_checklist(
    settings: Settings,
) -> list[HostedUiReadinessChecklistItem]:
    _validate_settings(settings)
    rows = (
        ("route_inventory", "UI route inventory is complete.", True, False, "Local route table"),
        (
            "page_inventory",
            "Template and guidance inventory is complete.",
            True,
            False,
            "Local repository files",
        ),
        (
            "admin_boundary",
            "Admin, dashboard, and review surfaces are guarded.",
            True,
            False,
            "Auth boundary classifier",
        ),
        (
            "metadata_only",
            "Attachment UI remains metadata-only.",
            True,
            False,
            "API route classifier",
        ),
        ("command_export", "Exports remain command-only.", True, False, "No export download route"),
        (
            "external_assets",
            "No external frontend assets are present.",
            True,
            False,
            "Local templates",
        ),
        ("frontend_build", "No frontend build system is present.", True, False, "Repository root"),
        (
            "private_security",
            "Private security review remains required.",
            False,
            True,
            "Private review gate",
        ),
        (
            "private_infrastructure",
            "Private infrastructure review remains required.",
            False,
            True,
            "Private review gate",
        ),
        (
            "hosted_decision",
            "Hosted pilot decision remains separate.",
            False,
            True,
            "Private review gate",
        ),
    )
    return [
        HostedUiReadinessChecklistItem(
            code=code,
            description=description,
            passed=passed,
            private_review_required=private,
            evidence=evidence,
        )
        for code, description, passed, private, evidence in rows
    ]


def _frontend_build_system_present() -> bool:
    return any(Path(name).exists() for name in FRONTEND_BUILD_FILES)


def build_hosted_ui_review_report(settings: Settings) -> HostedUiReviewReport:
    pages = build_hosted_ui_page_inventory(settings)
    routes = build_hosted_ui_route_matrix(settings)
    gates = build_hosted_ui_private_gates(settings)
    checklist = build_hosted_ui_readiness_checklist(settings)
    unknown_pages = [page for page in pages if page.page_class is HostedUiPageClass.UNKNOWN]
    unknown_routes = [route for route in routes if route.page_class is HostedUiPageClass.UNKNOWN]
    unprotected = [
        route
        for route in routes
        if route.surface
        in {
            HostedUiSurface.ADMIN_DASHBOARD,
            HostedUiSurface.PRODUCT_DASHBOARD,
            HostedUiSurface.REVIEW_WORKSPACE,
            HostedUiSurface.TRIAGE_QUEUE,
            HostedUiSurface.LIFECYCLE_CONTROLS,
        }
        and not route.admin_protected
    ]
    attachment_not_metadata = [
        route
        for route in routes
        if route.surface is HostedUiSurface.ATTACHMENT_METADATA and not route.metadata_only
    ]
    external_assets = any(page.external_frontend_assets for page in pages)
    frontend_build = _frontend_build_system_present()
    unsafe_routes = [
        route
        for route in routes
        if route.export_download or route.file_serving or route.procore_write_back
    ]
    findings: list[HostedUiFinding] = []
    for page in unknown_pages:
        findings.append(
            HostedUiFinding(
                code="unknown_page",
                message="A hosted UI page lacks a classification.",
                severity="blocker",
                location=page.source,
            )
        )
    for route in unknown_routes + unprotected + attachment_not_metadata + unsafe_routes:
        findings.append(
            HostedUiFinding(
                code="unsafe_route",
                message="A hosted UI route lacks a safe complete boundary.",
                severity="blocker",
                surface=route.surface,
                location=f"{route.method} {route.path}",
            )
        )
    if external_assets:
        findings.append(
            HostedUiFinding(
                code="external_frontend_asset",
                message="An external frontend asset reference was found.",
                severity="blocker",
            )
        )
    if frontend_build:
        findings.append(
            HostedUiFinding(
                code="frontend_build_system",
                message="A frontend build-system file was found.",
                severity="blocker",
            )
        )
    maximum = int(_setting(settings, "hosted_ui_max_findings", 300))
    if len(findings) > maximum:
        raise HostedUiReviewBlockedError("Hosted UI findings exceed the configured limit.")
    blockers = [finding.message for finding in findings if finding.severity == "blocker"]
    report = HostedUiReviewReport(
        status=(
            HostedUiReviewStatus.BLOCKED if blockers else HostedUiReviewStatus.NEEDS_PRIVATE_REVIEW
        ),
        decision=(HostedUiDecision.BLOCKED if blockers else HostedUiDecision.NEEDS_PRIVATE_REVIEW),
        pages=pages,
        routes=routes,
        private_gates=gates,
        checklist=checklist,
        pages_total=len(pages),
        routes_total=len(routes),
        demo_ready_pages_total=sum(
            page.mode_readiness is HostedUiModeReadiness.DEMO_READY for page in pages
        ),
        hosted_candidate_pages_total=sum(
            page.mode_readiness is HostedUiModeReadiness.HOSTED_CANDIDATE for page in pages
        ),
        private_review_pages_total=sum(
            page.mode_readiness is HostedUiModeReadiness.HOSTED_NEEDS_PRIVATE_REVIEW
            for page in pages
        ),
        blocked_pages_total=sum(
            page.mode_readiness in {HostedUiModeReadiness.BLOCKED, HostedUiModeReadiness.UNKNOWN}
            for page in pages
        ),
        findings=findings,
        blockers=blockers,
        warnings=[
            "Hosted UI preparation does not approve production, pilot, release, or deployment."
        ],
        route_inventory_complete=not unknown_routes and bool(routes),
        page_inventory_complete=not unknown_pages and bool(pages),
        admin_surfaces_protected=not unprotected,
        attachment_surfaces_metadata_only=not attachment_not_metadata,
        export_download_routes_present=any(route.export_download for route in routes),
        file_serving_routes_present=any(route.file_serving for route in routes),
        external_frontend_assets_present=external_assets,
        frontend_build_system_added=frontend_build,
        recommended_next_steps=[
            "Review hosted candidates and their existing admin boundaries.",
            "Complete private security and infrastructure review before hosted evaluation.",
            "Keep attachments metadata-only and exports command-only.",
        ],
    )
    validate_hosted_ui_review_report_safe(report)
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


def validate_hosted_ui_review_report_safe(report: HostedUiReviewReport) -> None:
    unsafe_flags = (
        report.export_download_routes_present,
        report.file_serving_routes_present,
        report.external_frontend_assets_present,
        report.frontend_build_system_added,
        report.hosted_deployment_attempted,
        report.external_call_attempted,
        report.procore_call_attempted,
        report.cloud_call_attempted,
        report.db_external_connection_attempted,
        report.scanner_attempted,
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
        report.route_inventory_complete,
        report.page_inventory_complete,
        report.admin_surfaces_protected,
        report.attachment_surfaces_metadata_only,
    )
    if any(unsafe_flags) or not all(required) or report.blockers:
        raise HostedUiReviewBlockedError("The hosted UI review failed closed.")
    for value in _walk_strings(report.model_dump(mode="json")):
        if sanitize_hosted_ui_value(value) == "[redacted]":
            raise HostedUiReviewBlockedError("The hosted UI review contains unsafe material.")
        for match in UNSAFE_CLAIM_PATTERN.finditer(value):
            window = value[max(0, match.start() - 100) : match.end() + 20]
            if not NEGATED_CLAIM_PATTERN.search(window):
                raise HostedUiReviewBlockedError(
                    "The hosted UI review contains an approval or compliance claim."
                )


def render_hosted_ui_review_markdown(report: HostedUiReviewReport) -> str:
    validate_hosted_ui_review_report_safe(report)
    return "\n".join(
        (
            "# Hosted UI preparation review",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Pages inventoried: {report.pages_total}",
            f"- UI routes inventoried: {report.routes_total}",
            "- Hosted deployment attempted: false",
            "- External frontend assets present: false",
            "- Frontend build system added: false",
            "",
            "This offline preparation does not approve production, pilot, release, or deployment.",
            "",
        )
    )


def render_hosted_ui_page_inventory_markdown(report: HostedUiReviewReport) -> str:
    validate_hosted_ui_review_report_safe(report)
    lines = [
        "# Hosted UI page inventory",
        "",
        "| Source | Surface | Page class | Protection | Readiness | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for page in report.pages:
        values = (
            page.source,
            page.surface.value,
            page.page_class.value,
            page.protection_type.value,
            page.mode_readiness.value,
            page.purpose,
        )
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines) + "\n"


def render_hosted_ui_readiness_checklist_markdown(report: HostedUiReviewReport) -> str:
    validate_hosted_ui_review_report_safe(report)
    lines = ["# Hosted UI readiness checklist", ""]
    for item in report.checklist:
        marker = "x" if item.passed else " "
        suffix = " Private review required." if item.private_review_required else ""
        lines.append(f"- [{marker}] {item.description}{suffix} Evidence: {item.evidence}.")
    return "\n".join(lines) + "\n"


def render_hosted_ui_private_gates_markdown(report: HostedUiReviewReport) -> str:
    validate_hosted_ui_review_report_safe(report)
    lines = [
        "# Hosted UI private gates",
        "",
        "These gates require private review before hosted evaluation; no deployment is performed.",
        "",
    ]
    for gate in report.private_gates:
        lines.extend((f"## {gate.title}", "", gate.description, ""))
    return "\n".join(lines)


def _csv_cell(value: Any) -> str:
    text = sanitize_hosted_ui_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_hosted_ui_route_matrix_csv(report: HostedUiReviewReport) -> str:
    validate_hosted_ui_review_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        ("method", "route", "surface", "page_class", "protection", "readiness", "purpose")
    )
    for route in report.routes:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    route.method,
                    route.path,
                    route.surface.value,
                    route.page_class.value,
                    route.protection_type.value,
                    route.mode_readiness.value,
                    route.purpose,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if ".." in raw.parts:
        raise HostedUiReviewBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        (
            "/tmp/procore-intake-bridge-hosted-ui-",
            "/private/tmp/procore-intake-bridge-hosted-ui-",
        )
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise HostedUiReviewBlockedError("Output root is outside the hosted UI boundary.")
    return resolved


def write_hosted_ui_review_artifacts(
    report: HostedUiReviewReport, output_root: str | Path
) -> HostedUiArtifactResult:
    validate_hosted_ui_review_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "hosted-ui-review-report.json": json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        "hosted-ui-review-report.md": render_hosted_ui_review_markdown(report),
        "hosted-ui-page-inventory.md": render_hosted_ui_page_inventory_markdown(report),
        "hosted-ui-route-matrix.csv": render_hosted_ui_route_matrix_csv(report),
        "hosted-ui-readiness-checklist.md": (render_hosted_ui_readiness_checklist_markdown(report)),
        "hosted-ui-private-gates.md": render_hosted_ui_private_gates_markdown(report),
    }
    rendered["manifest.json"] = (
        json.dumps(
            {
                "status": report.status.value,
                "files": list(ARTIFACT_FILES[:-1]),
                "sanitized": True,
                "live_operations": False,
                "hosted_deployment": False,
                "frontend_build": False,
            },
            indent=2,
        )
        + "\n"
    )
    for filename, contents in rendered.items():
        target = (root / filename).resolve()
        if target.parent != root:
            raise HostedUiReviewBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return HostedUiArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=list(ARTIFACT_FILES),
    )
