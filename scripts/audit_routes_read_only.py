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
PROHIBITED_PATH_TERMS = {
    "approve",
    "close",
    "delete",
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
    issues: list[RouteIssue] = []
    for route in application_routes():
        methods = route.methods or set()
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            lowered = route.path.casefold()
            if route.path.startswith("/admin") and method != "GET":
                issues.append(RouteIssue(route.path, method, "admin routes must be GET-only"))
            if route.path.startswith("/review") and method != "GET":
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
