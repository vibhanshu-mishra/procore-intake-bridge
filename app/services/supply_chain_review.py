# ruff: noqa: E501
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.supply_chain_review import (
    DependencyBoundary,
    OptionalExtraMatrixItem,
    PackageSurfaceBoundary,
    SupplyChainArtifactResult,
    SupplyChainCategory,
    SupplyChainControl,
    SupplyChainDecision,
    SupplyChainFinding,
    SupplyChainReviewReport,
    SupplyChainReviewStatus,
    SupplyChainScenario,
)


class SupplyChainReviewError(ValueError):
    pass


class SupplyChainReviewBlockedError(SupplyChainReviewError):
    pass


IGNORED_OUTPUTS = (
    "supply-chain-review-output/",
    "dependency-security-output/",
    "dependency-review-output/",
    "package-security-output/",
    "sbom-review-output/",
    "*.supply-chain-review-report.json",
    "*.supply-chain-review-report.md",
    "*.dependency-boundary-map.md",
    "*.optional-extras-matrix.csv",
    "*.package-surface-map.md",
    "*.supply-chain-checklist.md",
)
SAFE_ROOTS = {x.rstrip("/") for x in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "supply-chain-review-report.json",
    "supply-chain-review-report.md",
    "dependency-boundary-map.md",
    "package-surface-map.md",
    "supply-chain-checklist.md",
    "optional-extras-matrix.csv",
    "manifest.json",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:github_token|registry_token|publish_token|ci_secret|signing_key|password)\s*[:=]\s*(?!placeholder)\S+)"
)
CLAIM = re.compile(
    r"(?i)\b(?:slsa|sbom|gdpr|ccpa|hipaa) compliant\b|\b(?:soc ?2|iso ?27001|security|compliance) certified\b|\bproduction[- ]ready\b|\b(?:launch|pilot) approved\b|\bprocore (?:endorsed|partner|certified)\b"
)
FORBIDDEN_KEYS = {
    "github_token",
    "registry_token",
    "publish_token",
    "ci_secret",
    "signing_key",
    "authorization",
    "database_url",
    "source_url",
    "signed_url",
    "private_path",
    "report_contents",
}


def sanitize_supply_chain_value(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return (
        "[redacted]"
        if any(p.search(text) for p in (URL, EMAIL, PRIVATE_PATH, SECRET))
        else text[:400]
    )


def build_supply_chain_categories(settings):
    return list(SupplyChainCategory)


def build_dependency_boundaries(settings):
    return list(DependencyBoundary)


def build_package_surface_boundaries(settings):
    return list(PackageSurfaceBoundary)


def build_supply_chain_controls(settings):
    items = (
        ("package metadata", "pyproject.toml"),
        ("developer commands", "Makefile"),
        ("documentation navigation", "mkdocs.yml"),
        ("public safety", "scripts/audit_public_safety.py"),
        ("documentation checker", "scripts/check_docs_site.py"),
        ("route audit", "scripts/audit_routes_read_only.py"),
        ("release boundary", "docs/release-readiness.md"),
        ("final readiness", "docs/final-public-readiness.md"),
    )
    return [
        SupplyChainControl(
            name=n,
            evidence_path=p,
            description="Offline local repository evidence.",
            implemented=Path(p).is_file(),
        )
        for n, p in items
    ]


def build_supply_chain_scenarios(settings):
    return [
        SupplyChainScenario(
            category=x,
            expectation="Inspect local declarations and surfaces without external operations.",
        )
        for x in SupplyChainCategory
    ]


def build_optional_extras_matrix(settings):
    names = (
        "aws-secrets",
        "azure-secrets",
        "gcp-secrets",
        "cloud-secrets",
        "s3-storage",
        "azure-storage",
        "gcs-storage",
        "cloud-storage",
        "postgres",
        "docs",
        "test",
        "dev",
    )
    bounds = list(DependencyBoundary)[1:]
    return [OptionalExtraMatrixItem(extra=n, boundary=bounds[i]) for i, n in enumerate(names)]


def build_supply_chain_review_report(settings: Settings):
    if not settings.supply_chain_review_enabled:
        raise SupplyChainReviewError("Supply-chain review disabled.")
    req = (
        settings.supply_chain_review_require_placeholders,
        settings.supply_chain_review_require_offline_only,
        settings.supply_chain_review_require_no_external_scanners,
        settings.supply_chain_review_require_no_publish_automation,
        settings.supply_chain_review_require_no_deploy_automation,
        settings.supply_chain_review_require_no_workflow_changes,
        settings.supply_chain_review_require_optional_extras_boundaries,
        settings.supply_chain_review_require_package_metadata,
        settings.supply_chain_review_require_generated_output_ignores,
    )
    allow = (
        settings.supply_chain_review_allow_real_identities,
        settings.supply_chain_review_allow_real_domains,
        settings.supply_chain_review_allow_real_urls,
        settings.supply_chain_review_allow_report_contents,
        settings.supply_chain_review_allow_private_paths,
    )
    if settings.supply_chain_review_fail_closed and (not all(req) or any(allow)):
        raise SupplyChainReviewBlockedError("Unsafe supply-chain policy blocked.")
    findings = []
    gitignore = Path(".gitignore").read_text()
    findings += [
        SupplyChainFinding(
            code="missing_ignore_rule",
            message=f"Missing generated-output ignore rule: {x}.",
            severity="blocker",
        )
        for x in IGNORED_OUTPUTS
        if x not in gitignore
    ]
    findings += [
        SupplyChainFinding(
            code="private_dependency_review_needed",
            message="Private vulnerability, provenance, and license review remains required.",
        ),
        SupplyChainFinding(
            code="automation_out_of_scope",
            message="Build, publish, release, deploy, scanner, registry, and workflow automation remain outside I6.",
        ),
    ]
    blockers = [x.message for x in findings if x.severity == "blocker"]
    status = SupplyChainReviewStatus.BLOCKED if blockers else SupplyChainReviewStatus.NEEDS_REVIEW
    cats = build_supply_chain_categories(settings)
    deps = build_dependency_boundaries(settings)
    surfaces = build_package_surface_boundaries(settings)
    matrix = build_optional_extras_matrix(settings)
    report = SupplyChainReviewReport(
        status=status,
        decision=SupplyChainDecision.BLOCKED if blockers else SupplyChainDecision.NEEDS_REVIEW,
        categories=cats,
        dependency_boundaries=deps,
        package_surface_boundaries=surfaces,
        controls=build_supply_chain_controls(settings),
        scenarios=build_supply_chain_scenarios(settings),
        optional_extras_matrix=matrix,
        categories_total=len(cats),
        dependency_boundaries_total=len(deps),
        package_surface_boundaries_total=len(surfaces),
        optional_extra_matrix_items_total=len(matrix),
        findings=findings,
        blockers=blockers,
        warnings=[x.message for x in findings if x.severity != "blocker"],
        recommended_next_steps=[
            "Perform authorized private vulnerability, license, and provenance review.",
            "Keep build, publish, release, deploy, and workflow changes separately reviewed.",
            "Treat I6 as review input, not certification or approval.",
        ],
    )
    validate_supply_chain_review_report_safe(report)
    return report


def _keys(v):
    if isinstance(v, dict):
        for k, c in v.items():
            yield str(k).casefold()
            yield from _keys(c)
    elif isinstance(v, list):
        for c in v:
            yield from _keys(c)


def validate_supply_chain_review_report_safe(report):
    p = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    text = json.dumps(p, default=str) if not isinstance(p, str) else p
    if (set(_keys(p)) if not isinstance(p, str) else set()) & FORBIDDEN_KEYS or any(
        x.search(text) for x in (URL, EMAIL, PRIVATE_PATH, SECRET)
    ):
        raise SupplyChainReviewBlockedError("Unsafe supply-chain content blocked.")
    for line in text.splitlines():
        if CLAIM.search(line) and not re.search(r"(?i)\b(?:no|not|never|does not|is not)\b", line):
            raise SupplyChainReviewBlockedError("Unsafe supply-chain claim blocked.")


def _map(title, items):
    text = "\n".join(
        [
            f"# {title}",
            "",
            "Offline boundary only; no external operation was attempted.",
            "",
            *(f"- `{x.value}`" for x in items),
            "",
        ]
    )
    validate_supply_chain_review_report_safe(text)
    return text


def render_supply_chain_review_markdown(r):
    text = "\n".join(
        [
            "# Dependency and Supply Chain Security Review",
            "",
            f"Status: `{r.status.value}`",
            f"Decision: `{r.decision.value}`",
            "",
            "Offline only. No scanner, package audit, GitHub API, dependency bot, workflow change, build, Docker build, publish, release, tag, deploy, registry call, external call, or Procore call was attempted.",
            "",
            *(f"- `{x.code}` — {x.message}" for x in r.findings),
            "",
            "This is not SLSA, SBOM, security, or compliance certification and is not production or pilot approval.",
            "",
        ]
    )
    validate_supply_chain_review_report_safe(text)
    return text


def render_dependency_boundary_map_markdown(r):
    return _map("Dependency Boundary Map", r.dependency_boundaries)


def render_package_surface_map_markdown(r):
    return _map("Package Surface Map", r.package_surface_boundaries)


def render_supply_chain_checklist_markdown(r):
    return _map(
        "Supply Chain Checklist",
        [
            SupplyChainCategory.OPTIONAL_EXTRAS_BOUNDARY,
            SupplyChainCategory.EXTERNAL_SCANNER_BOUNDARY,
            SupplyChainCategory.PUBLISH_DEPLOY_BOUNDARY,
            SupplyChainCategory.WORKFLOW_AUTOMATION_BOUNDARY,
        ],
    )


def _cell(v):
    t = sanitize_supply_chain_value(v)
    return "'" + t if t.lstrip().startswith(("=", "+", "-", "@")) else t


def render_optional_extras_matrix_csv(r):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(("extra", "boundary", "optional", "external_call"))
    [
        w.writerow(
            tuple(
                _cell(v)
                for v in (
                    x.extra,
                    x.boundary.value,
                    str(x.optional).lower(),
                    str(x.external_call_attempted).lower(),
                )
            )
        )
        for x in r.optional_extras_matrix
    ]
    text = out.getvalue()
    validate_supply_chain_review_report_safe(text)
    return text


def _root(root):
    root = Path(root)
    temp = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-supply-chain-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if (
        ".." in root.parts
        or (root.is_absolute() and not temp)
        or (not temp and root.parts[:1] not in {(x,) for x in SAFE_ROOTS})
    ):
        raise SupplyChainReviewBlockedError("Unsafe output root.")
    return root


def write_supply_chain_review_artifacts(r, output_root):
    root = _root(output_root)
    a = {
        "supply-chain-review-report.json": r.model_dump_json(indent=2),
        "supply-chain-review-report.md": render_supply_chain_review_markdown(r),
        "dependency-boundary-map.md": render_dependency_boundary_map_markdown(r),
        "package-surface-map.md": render_package_surface_map_markdown(r),
        "supply-chain-checklist.md": render_supply_chain_checklist_markdown(r),
        "optional-extras-matrix.csv": render_optional_extras_matrix_csv(r),
    }
    a["manifest.json"] = json.dumps(
        {
            "files": sorted(a),
            "sanitized": True,
            "live_operations": False,
            "scanner_operations": False,
            "build_publish_release_deploy_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for n, c in a.items():
        validate_supply_chain_review_report_safe(c)
        (root / n).write_text(c)
    return SupplyChainArtifactResult(status=r.status, output_directory=root.name, files=sorted(a))
