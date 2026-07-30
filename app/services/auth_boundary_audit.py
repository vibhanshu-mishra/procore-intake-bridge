import csv
import io
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.config import Settings
from app.schemas.auth_boundary_audit import (
    AuthBoundaryArtifactResult,
    AuthBoundaryAuditStatus,
    AuthBoundaryCommandItem,
    AuthBoundaryControl,
    AuthBoundaryDecision,
    AuthBoundaryFinding,
    AuthBoundaryMethodRisk,
    AuthBoundaryProtectionType,
    AuthBoundaryReport,
    AuthBoundaryRouteClass,
    AuthBoundaryRouteItem,
)


class AuthBoundaryAuditError(ValueError):
    pass


class AuthBoundaryAuditBlockedError(AuthBoundaryAuditError):
    pass


PUBLIC_HEALTH_PATHS = {"/health", "/safety"}
PUBLIC_READINESS_PATHS = {"/ready"}
WEBHOOK_INGRESS_PATHS = {"/webhooks/procore", "/webhooks/procore/dry-run"}
LIFECYCLE_POST_PATHS = {
    "/review/intake/{record_id}/lifecycle",
    "/review/api/intake/{record_id}/lifecycle",
}
LOCAL_ROUTE_PREFIXES = (
    "/connections",
    "/sync-profiles",
    "/polling",
    "/webhook-events",
    "/event-queue",
    "/attachments",
    "/intake-records",
    "/onboarding",
)
LIVE_COMMANDS = {
    "sandbox-read-validation",
    "postgres-connectivity-check",
    "postgres-migration-status-check",
}
COMMANDS = (
    "operator-export-check",
    "operator-export-summary",
    "operator-export-artifact-check",
    "sandbox-smoke-explain",
    "sandbox-smoke-preflight",
    "sandbox-read-plan",
    "sandbox-read-preflight",
    "sandbox-read-validation",
    "cloud-secret-template",
    "cloud-secret-check",
    "cloud-secret-explain",
    "cloud-storage-template",
    "cloud-storage-check",
    "cloud-storage-explain",
    "postgres-runtime-template",
    "postgres-runtime-check",
    "postgres-connectivity-check",
    "postgres-migration-status-check",
    "hosted-deployment-template",
    "hosted-deployment-check",
    "https-webhook-template",
    "https-webhook-check",
    "hosted-pilot-dry-run-template",
    "hosted-pilot-dry-run-check",
    "demo-product-tour",
    "demo-product-check",
    "security-threat-model",
    "security-boundary-map",
    "security-review-checklist",
)
IGNORED_OUTPUTS = (
    "auth-boundary-audit-output/",
    "permission-boundary-output/",
    "auth-review-output/",
    "permission-review-output/",
    "*.auth-boundary-audit-report.json",
    "*.auth-boundary-audit-report.md",
    "*.auth-boundary-map.md",
    "*.permission-boundary-checklist.md",
    "*.route-permission-matrix.csv",
)
SAFE_ROOTS = {
    "auth-boundary-audit-output",
    "permission-boundary-output",
    "auth-review-output",
    "permission-review-output",
}
ARTIFACT_FILES = (
    "auth-boundary-audit-report.json",
    "auth-boundary-audit-report.md",
    "auth-boundary-map.md",
    "permission-boundary-checklist.md",
    "route-permission-matrix.csv",
    "manifest.json",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|sqlite)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\+?\d[\d(). -]{8,}\d")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:token|password|client_secret|"
    r"cookie_secret|session_secret|webhook_secret|oauth_client_secret|"
    r"sso_provider_secret)\s*[:=]\s*(?!false\b)\S+)"
)
DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
LONG_ID = re.compile(r"\b(?:\d{12}|[0-9a-f]{8}-[0-9a-f-]{27,})\b", re.I)
CLOUD_ID = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
KEY_MATERIAL = re.compile(
    r"(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE REQUEST)|"
    r"_acme-challenge|registry\S+:\S+)"
)
PRIVATE_CONTENT = re.compile(
    r"(?i)(?:raw report contents?|private security review contents?|scanner output|"
    r"raw_payload|deployment logs?|support bundles?)"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:soc ?2|iso ?27001|hipaa|security certified|compliance certified|"
    r"production[- ]ready|launch approved|pilot approved|procore (?:endorsed|"
    r"partner|certified|officially supported))\b"
)
FORBIDDEN_KEYS = {
    "raw_payload",
    "source_url",
    "signed_url",
    "database_url",
    "storage_key",
    "private_path",
    "report_contents",
    "authorization",
    "access_token",
    "session_secret",
    "cookie_secret",
}


def sanitize_auth_boundary_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
        )
    ):
        return "[redacted]"
    return text[:400]


def _dependency_names(route: Any) -> set[str]:
    dependant = getattr(route, "dependant", None)
    dependencies = getattr(dependant, "dependencies", ()) if dependant else ()
    return {getattr(getattr(item, "call", None), "__name__", "") for item in dependencies}


def _route_method(route: Any) -> str:
    methods = sorted(set(getattr(route, "methods", set()) or set()) - {"HEAD", "OPTIONS"})
    return methods[0] if methods else "UNKNOWN"


def classify_route_auth_boundary(route: Any) -> AuthBoundaryRouteItem:
    path = str(getattr(route, "path", ""))
    method = _route_method(route)
    dependencies = _dependency_names(route)
    admin_guard = "admin_guard" in dependencies
    deployment_guard = "deployment_operator_guard" in dependencies

    if path in PUBLIC_HEALTH_PATHS and method == "GET":
        route_class = AuthBoundaryRouteClass.PUBLIC_HEALTH
        protection = AuthBoundaryProtectionType.INTENTIONALLY_PUBLIC
        risk = AuthBoundaryMethodRisk.SAFE_GET
    elif path in PUBLIC_READINESS_PATHS and method == "GET":
        route_class = AuthBoundaryRouteClass.PUBLIC_READINESS
        protection = AuthBoundaryProtectionType.INTENTIONALLY_PUBLIC
        risk = AuthBoundaryMethodRisk.SAFE_GET
    elif path in WEBHOOK_INGRESS_PATHS and method == "POST":
        route_class = AuthBoundaryRouteClass.WEBHOOK_SIGNATURE_REQUIRED
        protection = AuthBoundaryProtectionType.WEBHOOK_SIGNATURE_REQUIRED
        risk = AuthBoundaryMethodRisk.WEBHOOK_POST_SIGNATURE_REQUIRED
    elif path.startswith("/admin"):
        route_class = AuthBoundaryRouteClass.PROTECTED_ADMIN
        protection = (
            AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED
            if admin_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    elif path.startswith("/deployment"):
        route_class = AuthBoundaryRouteClass.PROTECTED_DEPLOYMENT
        protection = (
            AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED
            if deployment_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    elif path.startswith("/dashboard"):
        route_class = AuthBoundaryRouteClass.PROTECTED_PRODUCT_DASHBOARD
        protection = (
            AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED
            if admin_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    elif path in LIFECYCLE_POST_PATHS and method == "POST":
        route_class = AuthBoundaryRouteClass.PROTECTED_LIFECYCLE_LOCAL_MUTATION
        protection = (
            AuthBoundaryProtectionType.LOCAL_ONLY
            if admin_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = AuthBoundaryMethodRisk.LOCAL_ONLY_POST
    elif path.startswith("/review/api"):
        route_class = AuthBoundaryRouteClass.PROTECTED_REVIEW_API
        protection = (
            AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED
            if admin_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    elif path.startswith("/review"):
        route_class = AuthBoundaryRouteClass.PROTECTED_REVIEW_WORKSPACE
        protection = (
            AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED
            if admin_guard
            else AuthBoundaryProtectionType.UNKNOWN
        )
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    elif path.startswith(LOCAL_ROUTE_PREFIXES):
        route_class = AuthBoundaryRouteClass.DOCS_OR_STATIC_LOCAL
        protection = AuthBoundaryProtectionType.LOCAL_ONLY
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.LOCAL_ONLY_POST
        )
    else:
        route_class = AuthBoundaryRouteClass.UNKNOWN
        protection = AuthBoundaryProtectionType.UNKNOWN
        risk = (
            AuthBoundaryMethodRisk.SAFE_GET
            if method == "GET"
            else AuthBoundaryMethodRisk.UNSAFE_MUTATION
        )
    return AuthBoundaryRouteItem(
        path=path or "[unknown-route]",
        method=method,
        route_class=route_class,
        protection_type=protection,
        method_risk=risk,
        admin_guard_present=admin_guard or deployment_guard,
        local_only=protection is AuthBoundaryProtectionType.LOCAL_ONLY,
        notes="Offline classification; no permission check was executed.",
    )


def classify_command_auth_boundary(command_name_or_make_target: str) -> AuthBoundaryCommandItem:
    name = sanitize_auth_boundary_value(command_name_or_make_target)
    if name in LIVE_COMMANDS:
        protection = AuthBoundaryProtectionType.MANUAL_CONFIRMATION_REQUIRED
        live_capable = True
    elif name.startswith(("cloud-secret", "cloud-storage")):
        protection = AuthBoundaryProtectionType.DISABLED_BY_DEFAULT
        live_capable = False
    elif "artifact" in name or "export" in name:
        protection = AuthBoundaryProtectionType.PRIVATE_WORKSPACE_REQUIRED
        live_capable = False
    else:
        protection = AuthBoundaryProtectionType.NO_NETWORK
        live_capable = False
    return AuthBoundaryCommandItem(
        name=name,
        protection_type=protection,
        live_capable=live_capable,
        included_in_quality=False,
        documented_gate=True,
    )


def build_route_permission_matrix(
    app_or_routes: Any, settings: Settings
) -> list[AuthBoundaryRouteItem]:
    candidates: Iterable[Any]
    if hasattr(app_or_routes, "routes"):
        candidates = app_or_routes.routes
    else:
        candidates = app_or_routes
    items: list[AuthBoundaryRouteItem] = []
    for route in candidates:
        if not isinstance(route, APIRoute) and not hasattr(route, "methods"):
            continue
        methods = sorted(set(getattr(route, "methods", set()) or set()) - {"HEAD", "OPTIONS"})
        for method in methods or ["UNKNOWN"]:
            proxy = _RouteMethodProxy(route, method)
            item = classify_route_auth_boundary(proxy)
            if settings.auth_boundary_audit_fail_closed and (
                item.protection_type is AuthBoundaryProtectionType.UNKNOWN
                or item.method_risk is AuthBoundaryMethodRisk.UNSAFE_MUTATION
            ):
                raise AuthBoundaryAuditBlockedError(
                    f"Unsafe or unknown route boundary was blocked: {item.method} {item.path}."
                )
            items.append(item)
    return items


class _RouteMethodProxy:
    def __init__(self, route: Any, method: str):
        self.path = getattr(route, "path", "")
        self.methods = {method}
        self.dependant = getattr(route, "dependant", None)


def build_command_permission_matrix(settings: Settings) -> list[AuthBoundaryCommandItem]:
    makefile = Path("Makefile").read_text(encoding="utf-8") if Path("Makefile").is_file() else ""
    quality = "\n".join(line for line in makefile.splitlines() if line.startswith("quality:"))
    commands = [classify_command_auth_boundary(name) for name in COMMANDS]
    for command in commands:
        command.included_in_quality = command.name in quality
        if command.live_capable:
            command.documented_gate = (
                command.name in makefile
                and "ADVANCED — MANUALLY GATED LIVE READS" in makefile
                and command.name not in quality
            )
    return commands


def build_auth_boundary_controls(settings: Settings) -> list[AuthBoundaryControl]:
    return [
        AuthBoundaryControl(
            name="admin guard",
            protection_type=AuthBoundaryProtectionType.ADMIN_TOKEN_REQUIRED,
            evidence_path="app/security/admin_access.py",
            description="Protected surfaces use the existing fail-closed admin guard.",
        ),
        AuthBoundaryControl(
            name="webhook signature",
            protection_type=AuthBoundaryProtectionType.WEBHOOK_SIGNATURE_REQUIRED,
            evidence_path="app/security/webhook_signature.py",
            description="Webhook ingress uses the existing signature-verification boundary.",
        ),
        AuthBoundaryControl(
            name="manual live gates",
            protection_type=AuthBoundaryProtectionType.MANUAL_CONFIRMATION_REQUIRED,
            evidence_path="Makefile",
            description="Live-capable commands remain separate from offline quality checks.",
        ),
        AuthBoundaryControl(
            name="private outputs",
            protection_type=AuthBoundaryProtectionType.PRIVATE_WORKSPACE_REQUIRED,
            evidence_path=".gitignore",
            description="Generated and private outputs remain outside version control.",
        ),
    ]


def _forbidden_route_flags(routes: list[AuthBoundaryRouteItem]) -> tuple[bool, bool, bool]:
    export = any(
        item.path.startswith(("/review", "/dashboard"))
        and any(term in item.path.casefold() for term in ("export", "download"))
        for item in routes
    )
    file_serving = any(
        item.path.startswith(("/review/attachments", "/dashboard"))
        and any(term in item.path.casefold() for term in ("download", "file", "serve", "content"))
        for item in routes
    )
    procore_write = any(
        "/procore" in item.path.casefold()
        and item.path not in WEBHOOK_INGRESS_PATHS
        and item.method in {"POST", "PUT", "PATCH", "DELETE"}
        for item in routes
    )
    return export, file_serving, procore_write


def build_auth_boundary_audit_report(settings: Settings) -> AuthBoundaryReport:
    if not settings.auth_boundary_audit_enabled:
        raise AuthBoundaryAuditError("Auth boundary audit is disabled.")
    unsafe_policy = any(
        (
            not settings.auth_boundary_audit_require_placeholders,
            not settings.auth_boundary_audit_require_admin_protection,
            not settings.auth_boundary_audit_allow_public_health_routes,
            not settings.auth_boundary_audit_allow_lifecycle_post_only,
            not settings.auth_boundary_audit_require_webhook_signature,
            not settings.auth_boundary_audit_require_live_command_gates,
            settings.auth_boundary_audit_allow_real_identities,
            settings.auth_boundary_audit_allow_real_domains,
            settings.auth_boundary_audit_allow_real_urls,
            settings.auth_boundary_audit_allow_report_contents,
            settings.auth_boundary_audit_allow_private_paths,
        )
    )
    if settings.auth_boundary_audit_fail_closed and unsafe_policy:
        raise AuthBoundaryAuditBlockedError("Unsafe auth-boundary policy was blocked.")

    from scripts.audit_routes_read_only import application_routes

    routes = build_route_permission_matrix(application_routes(), settings)
    commands = build_command_permission_matrix(settings)
    export, file_serving, procore_write = _forbidden_route_flags(routes)
    public = [
        item
        for item in routes
        if item.protection_type is AuthBoundaryProtectionType.INTENTIONALLY_PUBLIC
    ]
    unknown = [
        item
        for item in routes
        if item.route_class is AuthBoundaryRouteClass.UNKNOWN
        or item.protection_type is AuthBoundaryProtectionType.UNKNOWN
    ]
    unsafe_routes = [
        item for item in routes if item.method_risk is AuthBoundaryMethodRisk.UNSAFE_MUTATION
    ]
    protected_classes = {
        AuthBoundaryRouteClass.PROTECTED_ADMIN,
        AuthBoundaryRouteClass.PROTECTED_DEPLOYMENT,
        AuthBoundaryRouteClass.PROTECTED_PRODUCT_DASHBOARD,
        AuthBoundaryRouteClass.PROTECTED_REVIEW_WORKSPACE,
        AuthBoundaryRouteClass.PROTECTED_REVIEW_API,
        AuthBoundaryRouteClass.PROTECTED_LIFECYCLE_LOCAL_MUTATION,
        AuthBoundaryRouteClass.WEBHOOK_SIGNATURE_REQUIRED,
    }
    admin_routes = [
        item
        for item in routes
        if item.route_class
        in {
            AuthBoundaryRouteClass.PROTECTED_ADMIN,
            AuthBoundaryRouteClass.PROTECTED_DEPLOYMENT,
            AuthBoundaryRouteClass.PROTECTED_PRODUCT_DASHBOARD,
        }
    ]
    review_routes = [item for item in routes if item.path.startswith("/review")]
    lifecycle_posts = [
        item for item in routes if item.path in LIFECYCLE_POST_PATHS and item.method == "POST"
    ]
    webhook_routes = [
        item
        for item in routes
        if item.route_class is AuthBoundaryRouteClass.WEBHOOK_SIGNATURE_REQUIRED
    ]
    findings = [
        AuthBoundaryFinding(
            code="unsafe_route",
            message=f"Unsafe or unknown route boundary: {item.method} {item.path}.",
        )
        for item in [*unknown, *unsafe_routes]
    ]
    if export:
        findings.append(
            AuthBoundaryFinding(
                code="export_download_route",
                message="A prohibited export or download route is present.",
                severity="blocker",
            )
        )
    if file_serving:
        findings.append(
            AuthBoundaryFinding(
                code="file_serving_route",
                message="A prohibited attachment file-serving route is present.",
                severity="blocker",
            )
        )
    if procore_write:
        findings.append(
            AuthBoundaryFinding(
                code="procore_write_route",
                message="A prohibited Procore write route is present.",
                severity="blocker",
            )
        )
    gitignore = (
        Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").is_file() else ""
    )
    findings.extend(
        AuthBoundaryFinding(
            code="missing_ignore_rule",
            message=f"Missing auth-boundary output ignore rule: {pattern}.",
        )
        for pattern in IGNORED_OUTPUTS
        if pattern not in gitignore
    )
    findings = findings[: settings.auth_boundary_audit_max_findings]
    blockers = [item.message for item in findings if item.severity == "blocker"]
    status = (
        AuthBoundaryAuditStatus.BLOCKED
        if blockers
        else AuthBoundaryAuditStatus.NEEDS_REVIEW
        if findings
        else AuthBoundaryAuditStatus.READY
    )
    decision = {
        AuthBoundaryAuditStatus.READY: AuthBoundaryDecision.READY_FOR_SECURITY_REVIEW,
        AuthBoundaryAuditStatus.NEEDS_REVIEW: AuthBoundaryDecision.NEEDS_REVIEW,
        AuthBoundaryAuditStatus.BLOCKED: AuthBoundaryDecision.BLOCKED,
    }[status]
    report = AuthBoundaryReport(
        status=status,
        decision=decision,
        routes=routes,
        commands=commands,
        controls=build_auth_boundary_controls(settings),
        routes_total=len(routes),
        commands_total=len(commands),
        protected_routes_total=sum(item.route_class in protected_classes for item in routes),
        public_routes_total=len(public),
        local_mutation_routes_total=sum(
            item.method_risk is AuthBoundaryMethodRisk.LOCAL_ONLY_POST for item in routes
        ),
        webhook_routes_total=len(webhook_routes),
        unknown_routes_total=len(unknown),
        unsafe_routes_total=len(unsafe_routes),
        findings=findings,
        blockers=blockers,
        warnings=[item.message for item in findings if item.severity != "blocker"],
        public_routes_are_limited={item.path for item in public}
        <= PUBLIC_HEALTH_PATHS | PUBLIC_READINESS_PATHS,
        admin_routes_protected=bool(admin_routes)
        and all(item.admin_guard_present for item in admin_routes),
        review_routes_protected=bool(review_routes)
        and all(
            item.admin_guard_present
            or item.route_class is AuthBoundaryRouteClass.PROTECTED_LIFECYCLE_LOCAL_MUTATION
            for item in review_routes
        ),
        lifecycle_posts_local_only=len(lifecycle_posts) == len(LIFECYCLE_POST_PATHS)
        and all(
            item.method_risk is AuthBoundaryMethodRisk.LOCAL_ONLY_POST for item in lifecycle_posts
        ),
        webhook_signature_required=len(webhook_routes) == len(WEBHOOK_INGRESS_PATHS),
        live_commands_gated=all(
            not item.live_capable or (item.documented_gate and not item.included_in_quality)
            for item in commands
        ),
        export_download_routes_present=export,
        file_serving_routes_present=file_serving,
        procore_write_routes_present=procore_write,
        recommended_next_steps=[
            "Review the offline route and command boundary maps.",
            "Keep environment-specific permission review private.",
            "Treat this audit as review input, not certification or production authorization.",
        ],
    )
    validate_auth_boundary_audit_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_auth_boundary_audit_report_safe(
    report: BaseModel | dict[str, Any] | str,
) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    text = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
    keys = set(_walk_keys(payload)) if not isinstance(payload, str) else set()
    if keys & FORBIDDEN_KEYS or any(
        pattern.search(text)
        for pattern in (
            URL,
            DB_URL,
            EMAIL,
            PHONE,
            PRIVATE_PATH,
            SECRET,
            DOMAIN,
            LONG_ID,
            CLOUD_ID,
            KEY_MATERIAL,
            PRIVATE_CONTENT,
        )
    ):
        raise AuthBoundaryAuditBlockedError("Unsafe auth-boundary content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise AuthBoundaryAuditBlockedError("Unsafe auth-boundary claim was blocked.")


def render_auth_boundary_map_markdown(report: AuthBoundaryReport) -> str:
    lines = [
        "# Auth Boundary Map",
        "",
        f"Status: `{report.status.value}`",
        f"Decision: `{report.decision.value}`",
        "",
    ]
    lines.extend(
        f"- `{item.method} {item.path}` — `{item.route_class.value}` / "
        f"`{item.protection_type.value}` / `{item.method_risk.value}`"
        for item in report.routes
    )
    lines.extend(
        [
            "",
            "Offline classification only. No live permission or external check was attempted.",
            "This map is not production authorization or security certification.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_auth_boundary_audit_report_safe(rendered)
    return rendered


def render_permission_boundary_checklist(report: AuthBoundaryReport) -> str:
    lines = [
        "# Permission Boundary Checklist",
        "",
        "- [ ] Confirm intentionally public health and readiness routes stay limited.",
        "- [ ] Confirm admin, dashboard, review, and deployment guards remain present.",
        "- [ ] Confirm lifecycle POST routes remain local-only and admin-protected.",
        "- [ ] Confirm webhook ingress retains signature verification.",
        "- [ ] Confirm live-capable commands remain separately gated.",
        "- [ ] Confirm exports remain CLI-only and attachments remain metadata-only.",
        "- [ ] Complete environment-specific authorization review privately.",
        "",
    ]
    rendered = "\n".join(lines)
    validate_auth_boundary_audit_report_safe(rendered)
    return rendered


def _csv_cell(value: Any) -> str:
    text = sanitize_auth_boundary_value(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def render_route_permission_matrix_csv(report: AuthBoundaryReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ("method", "route", "route_class", "protection_type", "method_risk", "admin_guard")
    )
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
                    str(item.admin_guard_present).lower(),
                )
            )
        )
    rendered = output.getvalue()
    validate_auth_boundary_audit_report_safe(rendered)
    return rendered


def _render_report_markdown(report: AuthBoundaryReport) -> str:
    rendered = "\n".join(
        (
            "# Auth / Permission Boundary Audit",
            "",
            f"Status: `{report.status.value}`",
            f"Routes: `{report.routes_total}`",
            f"Commands: `{report.commands_total}`",
            f"Unknown routes: `{report.unknown_routes_total}`",
            f"Unsafe routes: `{report.unsafe_routes_total}`",
            "",
            "Offline public-safe audit only. No live permission, Procore, external, or scanner "
            "operation was attempted.",
            "",
            "This report is not production authorization or security certification.",
            "",
        )
    )
    validate_auth_boundary_audit_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-auth-boundary-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise AuthBoundaryAuditBlockedError("Unsafe auth-boundary output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_ROOTS}:
        raise AuthBoundaryAuditBlockedError("Unapproved auth-boundary output root.")
    return root


def write_auth_boundary_audit_artifacts(
    report: AuthBoundaryReport, output_root: Path
) -> AuthBoundaryArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "auth-boundary-audit-report.json": report.model_dump_json(indent=2),
        "auth-boundary-audit-report.md": _render_report_markdown(report),
        "auth-boundary-map.md": render_auth_boundary_map_markdown(report),
        "permission-boundary-checklist.md": render_permission_boundary_checklist(report),
        "route-permission-matrix.csv": render_route_permission_matrix_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {"files": sorted(artifacts), "live_operations": False, "sanitized": True},
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_auth_boundary_audit_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return AuthBoundaryArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=sorted(artifacts),
    )
