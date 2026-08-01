import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from app.config import Settings
from app.schemas.api_docs_review import (
    ApiDocsArtifactResult,
    ApiDocsDecision,
    ApiDocsFinding,
    ApiDocsReport,
    ApiDocsReviewStatus,
    ApiMethodRisk,
    ApiProtectionType,
    ApiRouteClass,
    ApiRouteDocumentationItem,
    ApiUsageExample,
)
from app.schemas.auth_boundary_audit import (
    AuthBoundaryMethodRisk,
    AuthBoundaryProtectionType,
)
from app.services.auth_boundary_audit import classify_route_auth_boundary


class ApiDocsReviewError(ValueError):
    pass


class ApiDocsReviewBlockedError(ApiDocsReviewError):
    pass


PUBLIC_HEALTH_PATHS = {"/health", "/safety"}
PUBLIC_READINESS_PATHS = {"/ready"}
WEBHOOK_INGRESS_PATHS = {"/webhooks/procore", "/webhooks/procore/dry-run"}
LIFECYCLE_POST_PATHS = {
    "/review/intake/{record_id}/lifecycle",
    "/review/api/intake/{record_id}/lifecycle",
}
ARTIFACT_FILES = (
    "api-docs-report.json",
    "api-docs-report.md",
    "api-route-reference.md",
    "api-route-matrix.csv",
    "api-usage-examples.md",
    "openapi-local-guide.md",
    "manifest.json",
)
SAFE_ROOT_NAMES = {
    "api-docs-output",
    "api-reference-output",
    "route-reference-output",
    "openapi-review-output",
}

URL_PATTERN = re.compile(r"(?i)\b(?:https?|s3|gs|postgres|postgresql)://\S+")
EMAIL_PATTERN = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{8,}\d)(?!\w)")
DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|dev|cloud|app|co)\b"
)
PRIVATE_PATH_PATTERN = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
LONG_ID_PATTERN = re.compile(
    r"(?<![\w{}.-])(?:\d{12,}|[0-9a-f]{8}-[0-9a-f-]{27,})(?![\w{}.-])",
    re.I,
)
TOKEN_PATTERN = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9]{20,}|npm_[A-Za-z0-9]{20,}|"
    r"pypi-[A-Za-z0-9_-]{20,})\b"
)
SECRET_PATTERN = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:github_token|registry_token|"
    r"package_registry_token|publish_token|ci_secret|admin_token|webhook_secret|"
    r"database_url|signed_url|source_url|storage_key|object_key)\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+)"
)
CLOUD_ID_PATTERN = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
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
FORBIDDEN_PATH_TERMS = {
    "delete",
    "file-content",
    "purge",
    "send-to-procore",
    "serve-file",
    "write-back",
    "writeback",
}


def sanitize_api_docs_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        PRIVATE_PATH_PATTERN,
        LONG_ID_PATTERN,
        TOKEN_PATTERN,
        SECRET_PATTERN,
        CLOUD_ID_PATTERN,
        PRIVATE_CONTENT_PATTERN,
    )
    return "[redacted]" if any(pattern.search(text) for pattern in patterns) else text[:500]


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _application_routes(app: Any) -> list[APIRoute]:
    routes: list[APIRoute] = []
    for candidate in getattr(app, "routes", ()):  # mounted application routers are local only
        if isinstance(candidate, APIRoute):
            routes.append(candidate)
            continue
        original_router = getattr(candidate, "original_router", None)
        if original_router is not None:
            routes.extend(
                route
                for route in getattr(original_router, "routes", ())
                if isinstance(route, APIRoute)
            )
    return routes


def collect_fastapi_routes(app_or_none: Any, settings: Settings) -> list[Any]:
    if not _setting(settings, "api_docs_review_enabled", True):
        raise ApiDocsReviewBlockedError("API documentation review is disabled.")
    required_controls = (
        "api_docs_require_route_reference",
        "api_docs_require_auth_boundary",
        "api_docs_require_demo_safe_examples",
        "api_docs_require_no_private_data",
        "api_docs_require_no_file_serving",
        "api_docs_require_no_export_downloads",
        "api_docs_require_no_procore_writes",
    )
    if not all(bool(_setting(settings, name, True)) for name in required_controls):
        raise ApiDocsReviewBlockedError(
            "A required fail-closed API documentation control is disabled."
        )
    if app_or_none is None:
        from app.main import app

        app_or_none = app
    routes = _application_routes(app_or_none)
    maximum = int(_setting(settings, "api_docs_max_routes", 300))
    if len(routes) > maximum:
        raise ApiDocsReviewBlockedError("The local route count exceeds the configured limit.")
    return routes


def _method(route: Any) -> str:
    methods = sorted(set(getattr(route, "methods", set()) or set()) - {"HEAD", "OPTIONS"})
    return methods[0] if methods else "UNKNOWN"


def _purpose(route: Any, route_class: ApiRouteClass) -> str:
    summary = getattr(route, "summary", None) or getattr(route, "description", None)
    if summary:
        return sanitize_api_docs_value(str(summary).splitlines()[0])
    purposes = {
        ApiRouteClass.PUBLIC_HEALTH: "Report local process health without private data.",
        ApiRouteClass.PUBLIC_READINESS: "Report local readiness without private data.",
        ApiRouteClass.ADMIN_DASHBOARD: "Present a protected administrative summary.",
        ApiRouteClass.DEPLOYMENT_READINESS: "Present protected deployment planning metadata.",
        ApiRouteClass.PRODUCT_DASHBOARD: "Present the protected product dashboard.",
        ApiRouteClass.REVIEW_WORKSPACE: "Present the protected intake review workspace.",
        ApiRouteClass.REVIEW_API: "Return protected review metadata.",
        ApiRouteClass.LIFECYCLE_LOCAL_MUTATION: "Apply a local lifecycle state transition.",
        ApiRouteClass.WEBHOOK_SIGNATURE_BOUNDARY: "Receive an event at the signature boundary.",
        ApiRouteClass.INTAKE_SYNC_DEMO: "Operate on local intake, sync, event, or Demo data.",
        ApiRouteClass.ATTACHMENT_METADATA: (
            "Inspect or plan attachment metadata without file serving."
        ),
        ApiRouteClass.ONBOARDING_PACKET: "Prepare local onboarding packet metadata.",
        ApiRouteClass.SANDBOX_GATED: "Describe a manually gated sandbox operation.",
        ApiRouteClass.DIAGNOSTICS_SUPPORT: "Present protected diagnostic metadata.",
        ApiRouteClass.STATIC_OR_DOCS: "Present local static documentation metadata.",
        ApiRouteClass.UNKNOWN: "Undocumented local route.",
    }
    return purposes[route_class]


def classify_api_route(route_item: Any) -> ApiRouteDocumentationItem:
    path = str(getattr(route_item, "path", ""))
    method = _method(route_item)
    boundary = classify_route_auth_boundary(route_item)
    protection_map = {
        AuthBoundaryProtectionType.INTENTIONALLY_PUBLIC: (ApiProtectionType.INTENTIONALLY_PUBLIC),
        AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED: (ApiProtectionType.ADMIN_TOKEN_REQUIRED),
        AuthBoundaryProtectionType.WEBHOOK_SIGNATURE_REQUIRED: (
            ApiProtectionType.WEBHOOK_SIGNATURE_REQUIRED
        ),
        AuthBoundaryProtectionType.MANUAL_CONFIRMATION_REQUIRED: (
            ApiProtectionType.MANUAL_CONFIRMATION_REQUIRED
        ),
        AuthBoundaryProtectionType.PRIVATE_WORKSPACE_REQUIRED: (
            ApiProtectionType.PRIVATE_WORKSPACE_REQUIRED
        ),
        AuthBoundaryProtectionType.DISABLED_BY_DEFAULT: (ApiProtectionType.DISABLED_BY_DEFAULT),
        AuthBoundaryProtectionType.LOCAL_ONLY: ApiProtectionType.LOCAL_ONLY,
        AuthBoundaryProtectionType.NO_NETWORK: ApiProtectionType.LOCAL_ONLY,
        AuthBoundaryProtectionType.SECRET_PROVIDER_REQUIRED: (
            ApiProtectionType.MANUAL_CONFIRMATION_REQUIRED
        ),
        AuthBoundaryProtectionType.UNKNOWN: ApiProtectionType.UNKNOWN,
    }
    protection = protection_map[boundary.protection_type]

    if path in PUBLIC_HEALTH_PATHS and method == "GET":
        route_class = ApiRouteClass.PUBLIC_HEALTH
    elif path in PUBLIC_READINESS_PATHS and method == "GET":
        route_class = ApiRouteClass.PUBLIC_READINESS
    elif path in WEBHOOK_INGRESS_PATHS and method == "POST":
        route_class = ApiRouteClass.WEBHOOK_SIGNATURE_BOUNDARY
    elif path in LIFECYCLE_POST_PATHS and method == "POST":
        route_class = ApiRouteClass.LIFECYCLE_LOCAL_MUTATION
    elif path.startswith("/admin"):
        route_class = ApiRouteClass.ADMIN_DASHBOARD
    elif path.startswith("/deployment"):
        route_class = (
            ApiRouteClass.DIAGNOSTICS_SUPPORT
            if path.endswith("/diagnostics")
            else ApiRouteClass.DEPLOYMENT_READINESS
        )
    elif path.startswith("/dashboard"):
        route_class = ApiRouteClass.PRODUCT_DASHBOARD
    elif path.startswith("/review/api"):
        route_class = ApiRouteClass.REVIEW_API
    elif path.startswith("/review"):
        route_class = ApiRouteClass.REVIEW_WORKSPACE
    elif path.startswith("/attachments") or (
        path.startswith("/intake-records/") and path.endswith("/attachments")
    ):
        route_class = ApiRouteClass.ATTACHMENT_METADATA
        protection = ApiProtectionType.METADATA_ONLY
    elif (
        path.startswith("/onboarding")
        or path.startswith("/onboarding-packets")
        or (path.startswith("/connections/") and path.endswith("/onboarding-packet"))
    ):
        route_class = ApiRouteClass.ONBOARDING_PACKET
        protection = ApiProtectionType.LOCAL_ONLY
    elif path.startswith(
        ("/connections", "/sync-profiles", "/polling", "/webhook-events", "/event-queue")
    ):
        route_class = ApiRouteClass.INTAKE_SYNC_DEMO
        protection = ApiProtectionType.LOCAL_ONLY
    elif path.startswith("/sandbox"):
        route_class = ApiRouteClass.SANDBOX_GATED
        protection = ApiProtectionType.MANUAL_CONFIRMATION_REQUIRED
    elif path.startswith(("/docs", "/redoc", "/openapi")):
        route_class = ApiRouteClass.STATIC_OR_DOCS
        protection = ApiProtectionType.LOCAL_ONLY
    else:
        route_class = ApiRouteClass.UNKNOWN
        protection = ApiProtectionType.UNKNOWN

    risk_map = {
        AuthBoundaryMethodRisk.SAFE_GET: ApiMethodRisk.SAFE_GET,
        AuthBoundaryMethodRisk.LOCAL_ONLY_POST: ApiMethodRisk.LOCAL_ONLY_POST,
        AuthBoundaryMethodRisk.WEBHOOK_POST_SIGNATURE_REQUIRED: (
            ApiMethodRisk.WEBHOOK_POST_SIGNATURE_REQUIRED
        ),
        AuthBoundaryMethodRisk.UNSAFE_MUTATION: (ApiMethodRisk.DESTRUCTIVE_OR_LIVE_MUTATION),
        AuthBoundaryMethodRisk.UNKNOWN: ApiMethodRisk.UNKNOWN,
    }
    risk = risk_map[boundary.method_risk]

    lowered = path.casefold()
    serves_files = any(term in lowered for term in ("/download", "/serve", "/content"))
    export_download = "export" in lowered and method == "GET"
    procore_write = "/procore" in lowered and path not in WEBHOOK_INGRESS_PATHS
    name = sanitize_api_docs_value(getattr(route_item, "name", "local-route"))
    return ApiRouteDocumentationItem(
        path=path or "[unknown-route]",
        method=method,
        name=name,
        purpose=_purpose(route_item, route_class),
        route_class=route_class,
        protection_type=protection,
        method_risk=risk,
        intentionally_public=protection is ApiProtectionType.INTENTIONALLY_PUBLIC,
        admin_guard_present=boundary.admin_guard_present,
        local_only=protection
        in {
            ApiProtectionType.LOCAL_ONLY,
            ApiProtectionType.DEMO_ONLY,
            ApiProtectionType.METADATA_ONLY,
        },
        serves_files=serves_files,
        export_download=export_download,
        procore_write_back=procore_write,
        notes="Static route-table classification; the route was not invoked.",
    )


def build_api_route_reference(settings: Settings) -> list[ApiRouteDocumentationItem]:
    items: list[ApiRouteDocumentationItem] = []
    for route in collect_fastapi_routes(None, settings):
        for method in sorted(set(route.methods or set()) - {"HEAD", "OPTIONS"}):
            proxy = _RouteMethodProxy(route, method)
            items.append(classify_api_route(proxy))
    return items


class _RouteMethodProxy:
    def __init__(self, route: Any, method: str):
        self.path = route.path
        self.methods = {method}
        self.name = route.name
        self.summary = route.summary
        self.description = route.description
        self.dependant = route.dependant


def build_api_usage_examples(settings: Settings) -> list[ApiUsageExample]:
    del settings
    return [
        ApiUsageExample(
            title="Local health metadata",
            method="GET",
            route="/health",
            example="Open the local API documentation, then try GET /health with fake data only.",
            description="Reads public local health metadata; it performs no external call.",
        ),
        ApiUsageExample(
            title="Protected Demo dashboard",
            method="GET",
            route="/dashboard/api/overview",
            example="Use the configured local Demo admin token to inspect dashboard metadata.",
            description="Requires the local admin boundary and uses fake Demo records only.",
        ),
        ApiUsageExample(
            title="Local lifecycle transition",
            method="POST",
            route="/review/api/intake/{record_id}/lifecycle",
            example="Use RECORD_ID_PLACEHOLDER and LIFECYCLE_STATE_PLACEHOLDER locally.",
            description="A local-only mutation; it is not a Procore write-back.",
        ),
        ApiUsageExample(
            title="Webhook signature boundary",
            method="POST",
            route="/webhooks/procore/dry-run",
            example="Use WEBHOOK_SIGNATURE_PLACEHOLDER with a fake local event fixture.",
            description="Documentation only; no webhook request is sent by this review.",
        ),
        ApiUsageExample(
            title="Attachment metadata",
            method="GET",
            route="/attachments/{attachment_id}",
            example="Use ATTACHMENT_ID_PLACEHOLDER to inspect fake metadata locally.",
            description="Returns metadata; no attachment file is served.",
        ),
    ]


def _unsafe_route(item: ApiRouteDocumentationItem) -> bool:
    lowered = item.path.casefold()
    return (
        item.route_class is ApiRouteClass.UNKNOWN
        or item.protection_type is ApiProtectionType.UNKNOWN
        or item.method_risk in {ApiMethodRisk.UNKNOWN, ApiMethodRisk.DESTRUCTIVE_OR_LIVE_MUTATION}
        or item.serves_files
        or item.export_download
        or item.procore_write_back
        or any(term in lowered for term in FORBIDDEN_PATH_TERMS)
        or (item.intentionally_public and item.method != "GET")
    )


def build_api_docs_report(settings: Settings) -> ApiDocsReport:
    routes = build_api_route_reference(settings)
    examples = build_api_usage_examples(settings)
    undocumented = [item for item in routes if item.route_class is ApiRouteClass.UNKNOWN]
    unsafe = [item for item in routes if _unsafe_route(item)]
    findings = [
        ApiDocsFinding(
            code="unsafe_or_undocumented_route",
            message="A route lacks a safe complete classification.",
            severity="blocker",
            route=f"{item.method} {item.path}",
        )
        for item in unsafe
    ]
    blockers = [finding.message for finding in findings]
    all_documented = not undocumented and len(routes) > 0
    report = ApiDocsReport(
        status=ApiDocsReviewStatus.BLOCKED if blockers else ApiDocsReviewStatus.READY,
        decision=(
            ApiDocsDecision.BLOCKED if blockers else ApiDocsDecision.READY_FOR_MAINTAINER_REVIEW
        ),
        routes=routes,
        usage_examples=examples,
        routes_total=len(routes),
        documented_routes_total=len(routes) - len(undocumented),
        undocumented_routes_total=len(undocumented),
        public_routes_total=sum(item.intentionally_public for item in routes),
        protected_routes_total=sum(not item.intentionally_public for item in routes),
        local_mutation_routes_total=sum(
            item.method_risk is ApiMethodRisk.LOCAL_ONLY_POST for item in routes
        ),
        webhook_routes_total=sum(
            item.route_class is ApiRouteClass.WEBHOOK_SIGNATURE_BOUNDARY for item in routes
        ),
        unsafe_routes_total=len(unsafe),
        findings=findings,
        blockers=blockers,
        warnings=[
            "This offline route reference does not approve production, pilot, release, "
            "or deployment."
        ],
        all_routes_documented=all_documented,
        no_export_download_routes=not any(item.export_download for item in routes),
        no_file_serving_routes=not any(item.serves_files for item in routes),
        no_procore_write_routes=not any(item.procore_write_back for item in routes),
        demo_examples_safe=all(
            item.local_only and item.fake_data_only and not item.live_call for item in examples
        ),
        recommended_next_steps=[
            "Review the local route reference and protection classifications.",
            "Run the app locally only when choosing to view its built-in OpenAPI interface.",
            "Complete separate private security and deployment reviews before live use.",
        ],
    )
    validate_api_docs_report_safe(report)
    return report


def _report_text(report: ApiDocsReport) -> str:
    return json.dumps(report.model_dump(mode="json"), sort_keys=True)


def validate_api_docs_report_safe(report: ApiDocsReport) -> None:
    blocked_flags = (
        report.external_call_attempted,
        report.procore_call_attempted,
        report.cloud_call_attempted,
        report.db_external_connection_attempted,
        report.scanner_attempted,
        report.openapi_external_tool_attempted,
        report.private_report_contents_exposed,
        report.secrets_exposed,
        report.urls_exposed,
        report.private_paths_exposed,
        report.ids_exposed,
        report.real_domains_exposed,
        report.production_approval_claimed,
        report.release_approval_claimed,
        report.pilot_approval_claimed,
    )
    required = (
        report.all_routes_documented,
        report.no_export_download_routes,
        report.no_file_serving_routes,
        report.no_procore_write_routes,
        report.demo_examples_safe,
    )
    if any(blocked_flags) or not all(required) or report.unsafe_routes_total:
        raise ApiDocsReviewBlockedError("The API documentation report failed closed.")
    text = _report_text(report)
    sensitive_patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        PRIVATE_PATH_PATTERN,
        LONG_ID_PATTERN,
        TOKEN_PATTERN,
        SECRET_PATTERN,
        CLOUD_ID_PATTERN,
        PRIVATE_CONTENT_PATTERN,
    )
    if any(pattern.search(text) for pattern in sensitive_patterns):
        raise ApiDocsReviewBlockedError("The API documentation report contains unsafe material.")
    for match in UNSAFE_CLAIM_PATTERN.finditer(text):
        window = text[max(0, match.start() - 100) : match.end() + 20]
        if not NEGATED_CLAIM_PATTERN.search(window):
            raise ApiDocsReviewBlockedError(
                "The API documentation report contains an approval claim."
            )


def render_api_docs_report_markdown(report: ApiDocsReport) -> str:
    validate_api_docs_report_safe(report)
    return "\n".join(
        (
            "# API documentation review",
            "",
            f"- Status: `{report.status.value}`",
            f"- Decision: `{report.decision.value}`",
            f"- Routes documented: {report.documented_routes_total}/{report.routes_total}",
            f"- Unsafe routes: {report.unsafe_routes_total}",
            "- External calls attempted: false",
            "- Procore calls attempted: false",
            "",
            "API documentation is an offline maintainer aid. It does not approve production, "
            "pilot, release, or deployment.",
            "",
        )
    )


def render_api_route_reference_markdown(report: ApiDocsReport) -> str:
    validate_api_docs_report_safe(report)
    lines = [
        "# API route reference",
        "",
        "This table is generated from the local route table without invoking any route.",
        "",
        "| Method | Route | Class | Protection | Risk | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report.routes:
        values = (
            item.method,
            item.path,
            item.route_class.value,
            item.protection_type.value,
            item.method_risk.value,
            item.purpose,
        )
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    return "\n".join(lines) + "\n"


def render_api_usage_examples_markdown(report: ApiDocsReport) -> str:
    validate_api_docs_report_safe(report)
    lines = [
        "# Safe local API usage examples",
        "",
        "Examples use fake local data only and this renderer makes no API call.",
        "",
    ]
    for item in report.usage_examples:
        lines.extend(
            (
                f"## {item.title}",
                "",
                f"- Method and route: `{item.method} {item.route}`",
                f"- Example: {item.example}",
                f"- Boundary: {item.description}",
                "",
            )
        )
    return "\n".join(lines)


def render_openapi_local_guide_markdown(report: ApiDocsReport) -> str:
    validate_api_docs_report_safe(report)
    return """# Local OpenAPI guide

The built-in OpenAPI interface is available only after a maintainer deliberately starts the
application locally. This review makes no API call: it does not start the app, invoke an
endpoint, or use external OpenAPI tooling. Use fake Demo data and the local admin boundary
where required.

The interface documents existing behavior only. It does not approve production, pilot,
release, or deployment, and it provides no public export download or attachment file service.
"""


def _csv_cell(value: Any) -> str:
    text = sanitize_api_docs_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_api_route_matrix_csv(report: ApiDocsReport) -> str:
    validate_api_docs_report_safe(report)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("method", "route", "route_class", "protection_type", "method_risk", "purpose"))
    for item in report.routes:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.method,
                    item.path,
                    item.route_class.value,
                    item.protection_type.value,
                    item.method_risk.value,
                    item.purpose,
                )
            )
        )
    return stream.getvalue()


def _safe_output_root(output_root: str | Path) -> Path:
    raw = Path(output_root)
    if ".." in raw.parts:
        raise ApiDocsReviewBlockedError("Output path traversal was blocked.")
    resolved = raw.resolve()
    allowed_tmp = str(resolved).startswith(
        ("/tmp/procore-intake-bridge-api-docs-", "/private/tmp/procore-intake-bridge-api-docs-")
    )
    if raw.name not in SAFE_ROOT_NAMES and not allowed_tmp:
        raise ApiDocsReviewBlockedError("Output root is outside the API docs output boundary.")
    return resolved


def write_api_docs_artifacts(
    report: ApiDocsReport, output_root: str | Path
) -> ApiDocsArtifactResult:
    validate_api_docs_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = {
        "api-docs-report.json": json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        "api-docs-report.md": render_api_docs_report_markdown(report),
        "api-route-reference.md": render_api_route_reference_markdown(report),
        "api-route-matrix.csv": render_api_route_matrix_csv(report),
        "api-usage-examples.md": render_api_usage_examples_markdown(report),
        "openapi-local-guide.md": render_openapi_local_guide_markdown(report),
    }
    manifest = {
        "status": report.status.value,
        "files": list(ARTIFACT_FILES[:-1]),
        "sanitized": True,
        "live_operations": False,
    }
    rendered["manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    for filename, contents in rendered.items():
        target = (root / filename).resolve()
        if target.parent != root:
            raise ApiDocsReviewBlockedError("Artifact path traversal was blocked.")
        target.write_text(contents, encoding="utf-8")
    return ApiDocsArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=list(ARTIFACT_FILES),
    )
