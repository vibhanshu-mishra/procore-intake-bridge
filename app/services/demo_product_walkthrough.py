import json
import re
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.config import Settings
from app.main import app
from app.schemas.demo_product_walkthrough import (
    DemoWalkthroughArtifactResult,
    DemoWalkthroughChecklist,
    DemoWalkthroughFinding,
    DemoWalkthroughReport,
    DemoWalkthroughStatus,
    DemoWalkthroughStep,
    DemoWalkthroughStepStatus,
)


class DemoProductWalkthroughError(ValueError):
    pass


class DemoProductWalkthroughBlockedError(DemoProductWalkthroughError):
    pass


STEP_GROUPS = (
    "clone_and_setup",
    "demo_mode",
    "product_dashboard",
    "intake_review",
    "lifecycle_flow",
    "triage_queue",
    "attachment_review",
    "export_pack",
    "safety_boundaries",
    "sandbox_pilot_next_steps",
)
IGNORED_OUTPUTS = (
    "demo-walkthrough-output/",
    "demo-product-output/",
    "demo-tour-output/",
    "demo-evaluation-output/",
    "*.demo-walkthrough-report.json",
    "*.demo-walkthrough-report.md",
    "*.demo-product-tour.md",
    "*.demo-evaluation-checklist.md",
)
REQUIRED_COMMANDS = (
    "first-run",
    "try-demo",
    "product-dashboard-check",
    "review-workspace-check",
    "intake-lifecycle-check",
    "operator-triage-check",
    "attachment-review-check",
    "operator-export-check",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:token|password|client_secret|webhook_secret)"
    r"\s*[:=]\s*(?!false\b)\S+)"
)
REAL_DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|pilot approved|release approved|"
    r"compliance certif(?:ied|ication)|official customer report|approval granted)\b"
)
FORBIDDEN_KEYS = {
    "raw_payload",
    "raw_payload_json",
    "source_url",
    "signed_url",
    "storage_key",
    "storage_path",
    "original_filename",
    "file_contents",
    "report_contents",
    "procore_project_id",
    "procore_item_id",
}
SAFE_OUTPUT_ROOT_NAMES = {
    "demo-walkthrough-output",
    "demo-product-output",
    "demo-tour-output",
    "demo-evaluation-output",
}


def sanitize_demo_walkthrough_value(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if (
        URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
        or REAL_DOMAIN.search(text)
    ):
        return "[redacted]"
    return text[:300]


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_demo_product_walkthrough_report_safe(
    report: BaseModel | dict[str, Any] | str,
) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    text = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
    keys = set(_walk_keys(payload)) if not isinstance(payload, str) else set()
    if (
        keys & FORBIDDEN_KEYS
        or URL.search(text)
        or PRIVATE_PATH.search(text)
        or SECRET.search(text)
        or REAL_DOMAIN.search(text)
    ):
        raise DemoProductWalkthroughBlockedError("Unsafe Demo walkthrough content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise DemoProductWalkthroughBlockedError("Unsafe Demo walkthrough claim was blocked.")


def _exists(root: Path, *paths: str) -> tuple[bool, list[str]]:
    missing = [path for path in paths if not (root / path).is_file()]
    return not missing, missing


def _step(
    group: str,
    title: str,
    description: str,
    *,
    passed: bool,
    commands: list[str] | None = None,
    docs: list[str] | None = None,
    missing: list[str] | None = None,
) -> DemoWalkthroughStep:
    findings = [
        DemoWalkthroughFinding(
            code="missing_public_component",
            message=f"Missing required public component: {item}",
            severity="warning",
        )
        for item in (missing or [])
    ]
    return DemoWalkthroughStep(
        group=group,
        title=title,
        status=(
            DemoWalkthroughStepStatus.READY if passed else DemoWalkthroughStepStatus.NEEDS_REVIEW
        ),
        description=description,
        commands=commands or [],
        docs=docs or [],
        findings=findings,
    )


def build_demo_product_walkthrough_steps(
    settings: Settings,
) -> list[DemoWalkthroughStep]:
    root = Path.cwd()
    makefile = (
        (root / "Makefile").read_text(encoding="utf-8") if (root / "Makefile").is_file() else ""
    )
    gitignore = (
        (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    )
    application_routes: list[APIRoute] = []
    for candidate in app.routes:
        if isinstance(candidate, APIRoute):
            application_routes.append(candidate)
            continue
        original_router = getattr(candidate, "original_router", None)
        if original_router is not None:
            application_routes.extend(
                route for route in original_router.routes if isinstance(route, APIRoute)
            )
    route_pairs = {
        (route.path, method) for route in application_routes for method in (route.methods or set())
    }

    base_ok, base_missing = _exists(root, "README.md", "QUICKSTART.md", "docs/walkthrough-demo.md")
    docs_ok, docs_missing = _exists(
        root,
        "docs/product-dashboard.md",
        "docs/intake-review-workspace.md",
        "docs/intake-lifecycle-status-flow.md",
        "docs/operator-triage-queue.md",
        "docs/attachment-review-manifest-ux.md",
        "docs/operator-export-pack.md",
    )
    commands_missing = [command for command in REQUIRED_COMMANDS if f"{command}:" not in makefile]
    safety_ok, safety_missing = _exists(
        root,
        "scripts/audit_routes_read_only.py",
        "scripts/audit_public_safety.py",
        "scripts/check_docs_site.py",
        "scripts/run_final_public_readiness_audit.py",
        "scripts/check_release_readiness.py",
    )
    routes = {
        "product_dashboard": ("/dashboard", "GET") in route_pairs,
        "intake_review": ("/review", "GET") in route_pairs,
        "triage_queue": ("/review/triage", "GET") in route_pairs,
        "attachment_review": ("/review/attachments", "GET") in route_pairs,
    }
    export_route = any(
        "export" in path.casefold() and method == "GET" for path, method in route_pairs
    )
    ignore_missing = [pattern for pattern in IGNORED_OUTPUTS if pattern not in gitignore]
    docs_text = "\n".join(
        (root / name).read_text(encoding="utf-8").casefold()
        for name in ("README.md", "QUICKSTART.md", "docs/walkthrough-demo.md")
        if (root / name).is_file()
    )
    docs_safe = (
        ("fake data" in docs_text or "synthetic fixture" in docs_text)
        and "production" in docs_text
        and "pilot" in docs_text
    )

    return [
        _step(
            "clone_and_setup",
            "Clone and first run",
            "Confirm the public onboarding path and quickstart are present.",
            passed=base_ok and not commands_missing,
            commands=["make first-run"],
            docs=["README.md", "QUICKSTART.md"],
            missing=base_missing + commands_missing,
        ),
        _step(
            "demo_mode",
            "Fixture-only Demo Mode",
            "Run committed fake fixtures without credentials or live checks.",
            passed=base_ok and docs_safe,
            commands=["make try-demo"],
            docs=["docs/walkthrough-demo.md"],
            missing=[] if docs_safe else ["fake-data and readiness boundary guidance"],
        ),
        _step(
            "product_dashboard",
            "Product dashboard",
            "Inspect the protected local product cockpit.",
            passed=docs_ok and routes["product_dashboard"],
            commands=["make product-dashboard-check"],
            docs=["docs/product-dashboard.md"],
            missing=[] if routes["product_dashboard"] else ["/dashboard GET"],
        ),
        _step(
            "intake_review",
            "Intake review workspace",
            "Review sanitized local intake records.",
            passed=docs_ok and routes["intake_review"],
            commands=["make review-workspace-check"],
            docs=["docs/intake-review-workspace.md"],
        ),
        _step(
            "lifecycle_flow",
            "Lifecycle status flow",
            "Inspect bounded local lifecycle behavior.",
            passed=docs_ok and "intake-lifecycle-check:" in makefile,
            commands=["make intake-lifecycle-check"],
            docs=["docs/intake-lifecycle-status-flow.md"],
        ),
        _step(
            "triage_queue",
            "Operator triage queue",
            "Use deterministic local sorting guidance.",
            passed=docs_ok and routes["triage_queue"],
            commands=["make operator-triage-check"],
            docs=["docs/operator-triage-queue.md"],
        ),
        _step(
            "attachment_review",
            "Attachment metadata review",
            "Inspect metadata summaries without opening files.",
            passed=docs_ok and routes["attachment_review"],
            commands=["make attachment-review-check"],
            docs=["docs/attachment-review-manifest-ux.md"],
        ),
        _step(
            "export_pack",
            "Operator export pack",
            "Validate sanitized command-only export rendering.",
            passed=docs_ok and not export_route and "operator-export-check:" in makefile,
            commands=["make operator-export-check"],
            docs=["docs/operator-export-pack.md"],
            missing=["unexpected GET export route"] if export_route else [],
        ),
        _step(
            "safety_boundaries",
            "Public safety and readiness",
            "Run offline audits and maintainer-readiness checks.",
            passed=safety_ok and not ignore_missing,
            commands=["make safety-check", "make final-readiness", "make release-readiness"],
            docs=["docs/safety-model.md"],
            missing=safety_missing + ignore_missing,
        ),
        _step(
            "sandbox_pilot_next_steps",
            "Next private step",
            "Stop at the private, manually gated Sandbox and Pilot boundary.",
            passed=docs_safe,
            commands=["make prepare-sandbox", "make prepare-pilot"],
            docs=["docs/walkthrough-sandbox.md", "docs/walkthrough-pilot.md"],
        ),
    ]


def build_demo_product_walkthrough_report(settings: Settings) -> DemoWalkthroughReport:
    if not settings.demo_walkthrough_enabled:
        raise DemoProductWalkthroughError("The Demo Product Walkthrough is disabled.")
    unsafe = any(
        (
            not settings.demo_walkthrough_require_fake_data,
            settings.demo_walkthrough_allow_real_identities,
            settings.demo_walkthrough_allow_real_domains,
            settings.demo_walkthrough_allow_real_urls,
            settings.demo_walkthrough_allow_report_contents,
            settings.demo_walkthrough_allow_private_paths,
        )
    )
    if settings.demo_walkthrough_fail_closed and unsafe:
        raise DemoProductWalkthroughBlockedError(
            "Unsafe Demo Product Walkthrough settings were blocked."
        )
    steps = build_demo_product_walkthrough_steps(settings)
    ready = sum(step.status is DemoWalkthroughStepStatus.READY for step in steps)
    needs_review = sum(step.status is DemoWalkthroughStepStatus.NEEDS_REVIEW for step in steps)
    blockers = [
        finding.message
        for step in steps
        for finding in step.findings
        if finding.severity == "error"
    ]
    warnings = [
        finding.message
        for step in steps
        for finding in step.findings
        if finding.severity == "warning"
    ]
    report = DemoWalkthroughReport(
        status=(
            DemoWalkthroughStatus.READY
            if ready == len(steps)
            else DemoWalkthroughStatus.NEEDS_REVIEW
        ),
        steps=steps,
        checklist=DemoWalkthroughChecklist(
            title="Demo Product Evaluation Checklist",
            items=[
                "Start from the public first-run guidance.",
                "Use committed fake data only.",
                "Walk from dashboard through review, lifecycle, triage, and attachment metadata.",
                "Validate command-only export summaries.",
                "Run public safety and readiness checks.",
                "Stop before private Sandbox or Pilot work.",
            ],
        ),
        steps_total=len(steps),
        steps_ready=ready,
        steps_needing_review=needs_review,
        blockers=blockers,
        warnings=warnings,
        findings=[finding for step in steps for finding in step.findings],
        recommended_next_steps=[
            "Run `make first-run`.",
            "Run `make try-demo`.",
            "Open `/dashboard` and follow the safe local links.",
            "Run `make demo-evaluation-checklist`.",
            "Keep any later Sandbox or Pilot work private and manually gated.",
        ],
    )
    validate_demo_product_walkthrough_report_safe(report)
    return report


def render_demo_product_tour_markdown(report: DemoWalkthroughReport) -> str:
    lines = [
        "# Demo Product Tour",
        "",
        "Fake data only. No Procore, external, live Sandbox, deployment, or release operation.",
        "",
    ]
    for index, step in enumerate(report.steps, 1):
        lines.extend(
            [
                f"## {index}. {step.title}",
                "",
                f"Status: `{step.status.value}`",
                "",
                step.description,
                "",
            ]
        )
        lines.extend(f"- `{command}`" for command in step.commands)
        if step.commands:
            lines.append("")
    lines.extend(
        [
            "Demo Mode does not establish production readiness, Pilot authorization, "
            "compliance certification, customer reporting, or external system status.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_demo_product_walkthrough_report_safe(rendered)
    return rendered


def render_demo_evaluation_checklist(report: DemoWalkthroughReport) -> str:
    lines = [
        "# Demo Evaluation Checklist",
        "",
        "Use fake public fixtures only; read no private reports.",
        "",
    ]
    for item in report.checklist.items:
        lines.append(f"- [ ] {item}")
    lines.extend(
        [
            "",
            "- [ ] Confirm no Procore or external call was made.",
            "- [ ] Confirm no deployment, release, or authorization is represented.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_demo_product_walkthrough_report_safe(rendered)
    return rendered


def render_demo_next_steps_markdown(report: DemoWalkthroughReport) -> str:
    lines = ["# Demo Next Steps", ""]
    lines.extend(f"- {item}" for item in report.recommended_next_steps)
    lines.extend(
        [
            "",
            "Sandbox and Pilot begin later in a private, manually gated workspace.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_demo_product_walkthrough_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-demo-product-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise DemoProductWalkthroughBlockedError("Unsafe Demo artifact output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_OUTPUT_ROOT_NAMES}:
        raise DemoProductWalkthroughBlockedError("Unapproved Demo artifact output root.")
    return root


def write_demo_product_walkthrough_artifacts(
    report: DemoWalkthroughReport, output_root: Path
) -> DemoWalkthroughArtifactResult:
    validate_demo_product_walkthrough_report_safe(report)
    root = _safe_output_root(Path(output_root))
    artifacts = {
        "demo.demo-product-tour.md": render_demo_product_tour_markdown(report),
        "demo.demo-evaluation-checklist.md": render_demo_evaluation_checklist(report),
        "demo.demo-walkthrough-report.md": render_demo_next_steps_markdown(report),
        "demo.demo-walkthrough-report.json": report.model_dump_json(indent=2),
    }
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_demo_product_walkthrough_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return DemoWalkthroughArtifactResult(
        status=DemoWalkthroughStatus.READY,
        output_directory=root.name,
        files=sorted(artifacts),
    )
