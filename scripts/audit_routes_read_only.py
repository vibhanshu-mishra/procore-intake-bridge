#!/usr/bin/env python3
from dataclasses import dataclass

from fastapi.routing import APIRoute

from app.main import app


@dataclass(frozen=True)
class RouteIssue:
    path: str
    method: str
    reason: str


LOCAL_PATCH_PATHS = {"/sync-profiles/{sync_profile_id}"}
LOCAL_LIFECYCLE_POST_PATHS = {
    "/review/intake/{record_id}/lifecycle",
    "/review/api/intake/{record_id}/lifecycle",
}
REQUIRED_TRIAGE_GET_PATHS = {
    "/review/triage",
    "/review/api/triage",
    "/review/api/triage/summary",
}
REQUIRED_ATTACHMENT_REVIEW_GET_PATHS = {
    "/review/attachments",
    "/review/attachments/{record_id}",
    "/review/api/attachments",
    "/review/api/attachments/summary",
    "/review/api/attachments/{record_id}",
}
REQUIRED_PRODUCT_DASHBOARD_GET_PATHS = {
    "/dashboard",
    "/dashboard/api/overview",
}
PROHIBITED_PATH_TERMS = {
    "approve",
    "assign",
    "calendar",
    "close",
    "comment",
    "compliance",
    "delete",
    "email",
    "notify",
    "notification",
    "register-webhook",
    "send-to-customer",
    "send-to-procore",
    "slack",
    "submit",
    "upload",
    "write-back",
    "writeback",
}


def application_routes() -> list[APIRoute]:
    routes: list[APIRoute] = []
    for candidate in app.routes:
        if isinstance(candidate, APIRoute):
            routes.append(candidate)
            continue
        original_router = getattr(candidate, "original_router", None)
        if original_router is not None:
            routes.extend(
                route for route in original_router.routes if isinstance(route, APIRoute)
            )
    return routes


def audit_routes() -> list[RouteIssue]:
    from app.schemas.auth_boundary_audit import (
        AuthBoundaryMethodRisk,
        AuthBoundaryProtectionType,
        AuthBoundaryRouteClass,
    )
    from app.services.auth_boundary_audit import classify_route_auth_boundary

    issues: list[RouteIssue] = []
    routes = application_routes()
    available_gets = {
        route.path for route in routes if "GET" in (route.methods or set())
    }
    for missing in sorted(REQUIRED_TRIAGE_GET_PATHS - available_gets):
        issues.append(RouteIssue(missing, "GET", "required triage route is missing"))
    for missing in sorted(REQUIRED_ATTACHMENT_REVIEW_GET_PATHS - available_gets):
        issues.append(
            RouteIssue(missing, "GET", "required attachment review route is missing")
        )
    for missing in sorted(REQUIRED_PRODUCT_DASHBOARD_GET_PATHS - available_gets):
        issues.append(
            RouteIssue(missing, "GET", "required product dashboard route is missing")
        )
    for route in routes:
        methods = route.methods or set()
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            classified = classify_route_auth_boundary(route)
            if (
                classified.route_class is AuthBoundaryRouteClass.UNKNOWN
                or classified.protection_type is AuthBoundaryProtectionType.UNKNOWN
            ):
                issues.append(
                    RouteIssue(route.path, method, "route has an unknown auth boundary")
                )
            if classified.method_risk is AuthBoundaryMethodRisk.UNSAFE_MUTATION:
                issues.append(
                    RouteIssue(route.path, method, "route has an unsafe mutation boundary")
                )
            lowered = route.path.casefold()
            if route.path.startswith("/review") and "export" in lowered:
                issues.append(
                    RouteIssue(
                        route.path,
                        method,
                        "operator exports must remain CLI-only with no web route",
                    )
                )
            if route.path.startswith("/review/attachments") and any(
                term in lowered for term in ("download", "file", "serve", "content")
            ):
                issues.append(
                    RouteIssue(
                        route.path,
                        method,
                        "attachment review must not expose a file-serving route",
                    )
                )
            if route.path.startswith("/admin") and method != "GET":
                issues.append(RouteIssue(route.path, method, "admin routes must be GET-only"))
            if route.path.startswith("/dashboard"):
                if method != "GET":
                    issues.append(
                        RouteIssue(route.path, method, "dashboard routes must be GET-only")
                    )
                if any(term in lowered for term in ("download", "export", "file", "serve")):
                    issues.append(
                        RouteIssue(
                            route.path,
                            method,
                            "dashboard must not expose downloads, exports, or files",
                        )
                    )
            if (
                route.path.startswith("/review")
                and method != "GET"
                and not (
                    method == "POST"
                    and route.path in LOCAL_LIFECYCLE_POST_PATHS
                )
            ):
                issues.append(
                    RouteIssue(route.path, method, "review routes must be GET-only")
                )
            if route.path.startswith("/deployment") and method != "GET":
                issues.append(
                    RouteIssue(route.path, method, "deployment routes must be GET-only")
                )
            if method in {"DELETE", "PUT"}:
                issues.append(RouteIssue(route.path, method, "destructive method is not allowed"))
            if method == "PATCH" and route.path not in LOCAL_PATCH_PATHS:
                issues.append(
                    RouteIssue(route.path, method, "PATCH is not an approved local route")
                )
            if any(term in lowered for term in PROHIBITED_PATH_TERMS):
                issues.append(RouteIssue(route.path, method, "path suggests Procore mutation"))
            if "/procore" in lowered and route.path not in {
                "/webhooks/procore",
                "/webhooks/procore/dry-run",
            }:
                issues.append(RouteIssue(route.path, method, "unapproved Procore-facing route"))
    return issues


def main() -> int:
    issues = audit_routes()
    for issue in issues:
        print(f"{issue.method} {issue.path}: {issue.reason}")
    if issues:
        print(f"Route read-only audit failed with {len(issues)} issue(s).")
        return 1
    route_count = len(application_routes())
    print(f"Route read-only audit passed ({route_count} application routes inspected).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
