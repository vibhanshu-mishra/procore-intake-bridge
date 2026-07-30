import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.webhook_security_review import (
    WebhookFixtureMatrixItem,
    WebhookReplayExpectation,
    WebhookSecurityArtifactResult,
    WebhookSecurityBoundary,
    WebhookSecurityCategory,
    WebhookSecurityControl,
    WebhookSecurityDecision,
    WebhookSecurityFinding,
    WebhookSecurityReviewReport,
    WebhookSecurityReviewStatus,
    WebhookSecurityScenario,
    WebhookSignatureExpectation,
)


class WebhookSecurityReviewError(ValueError):
    pass


class WebhookSecurityReviewBlockedError(WebhookSecurityReviewError):
    pass


BOUNDARY_NAMES = (
    "webhook_receiver_route",
    "signature_header_boundary",
    "request_body_boundary",
    "shared_secret_boundary",
    "event_queue_boundary",
    "replay_route_boundary",
    "replay_cli_boundary",
    "fixture_boundary",
    "storage_boundary",
    "diagnostics_boundary",
    "docs_boundary",
    "live_procore_boundary",
)
REQUIRED_FILES = (
    "app/routers/webhooks.py",
    "app/security/webhook_signature.py",
    "app/services/event_queue.py",
    "app/services/webhook_normalizer.py",
    "app/services/webhook_verification.py",
    "docs/webhook-production-verification.md",
    "docs/https-webhook-production-planning.md",
    "docs/security-threat-model.md",
    "docs/auth-permission-boundary-audit.md",
    "scripts/audit_public_safety.py",
    "scripts/audit_routes_read_only.py",
    "tests/test_webhook_api.py",
    "tests/test_webhook_signature.py",
)
IGNORED_OUTPUTS = (
    "webhook-security-review-output/",
    "webhook-hardening-output/",
    "webhook-replay-review-output/",
    "webhook-signature-review-output/",
    "*.webhook-security-review-report.json",
    "*.webhook-security-review-report.md",
    "*.webhook-signature-boundary.md",
    "*.webhook-replay-checklist.md",
    "*.webhook-fixture-matrix.csv",
)
SAFE_ROOTS = {
    "webhook-security-review-output",
    "webhook-hardening-output",
    "webhook-replay-review-output",
    "webhook-signature-review-output",
}
ARTIFACT_FILES = (
    "webhook-security-review-report.json",
    "webhook-security-review-report.md",
    "webhook-signature-boundary.md",
    "webhook-replay-checklist.md",
    "webhook-fixture-matrix.csv",
    "manifest.json",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
DB_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|sqlite)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\+?\d[\d(). -]{8,}\d")
PRIVATE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:token|password|client_secret|"
    r"webhook_secret|shared_secret|signature)\s*[:=]\s*(?!false\b)\S+)"
)
DOMAIN = re.compile(r"(?i)\b[a-z0-9-]+\.(?:com|net|org|io|co)\b")
LONG_ID = re.compile(r"\b(?:\d{12}|[0-9a-f]{8}-[0-9a-f-]{27,})\b", re.I)
CLOUD_ID = re.compile(r"(?i)(?:\barn:aws\S+|/subscriptions/\S+|\bprojects/\S+)")
KEY_MATERIAL = re.compile(
    r"(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE REQUEST)|"
    r"_acme-challenge|registry\S+:\S+)"
)
PRIVATE_CONTENT = re.compile(
    r"(?i)(?:live webhook (?:headers?|payloads?|signatures?)|raw request body dump|"
    r"replay logs?|webhook registration output|deployment logs?|sql dumps?|"
    r"backup contents?|private report contents?|scanner output)"
)
UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:soc ?2|iso ?27001|hipaa|security certified|compliance certified|"
    r"production[- ]ready|launch approved|pilot approved|procore (?:endorsed|"
    r"partner|certified|officially supported))\b"
)
FORBIDDEN_KEYS = {
    "raw_payload",
    "raw_headers",
    "raw_body",
    "signature_value",
    "webhook_secret",
    "source_url",
    "signed_url",
    "database_url",
    "private_path",
    "report_contents",
    "authorization",
}


def sanitize_webhook_security_value(value: Any) -> str:
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


def build_webhook_security_categories(settings: Settings) -> list[WebhookSecurityCategory]:
    return list(WebhookSecurityCategory)


def build_webhook_security_boundaries(settings: Settings) -> list[WebhookSecurityBoundary]:
    private = {
        "shared_secret_boundary",
        "storage_boundary",
        "diagnostics_boundary",
        "live_procore_boundary",
    }
    return [
        WebhookSecurityBoundary(
            name=name,
            description=f"Offline review boundary for {name.replace('_', ' ')}.",
            private_review_required=name in private,
        )
        for name in BOUNDARY_NAMES
    ]


def build_webhook_security_controls(settings: Settings) -> list[WebhookSecurityControl]:
    return [
        WebhookSecurityControl(
            name="HMAC verification",
            category=WebhookSecurityCategory.SIGNATURE_VERIFICATION,
            evidence_path="app/security/webhook_signature.py",
            description="Configured verification uses HMAC-SHA256 over exact request bytes.",
        ),
        WebhookSecurityControl(
            name="constant-time comparison",
            category=WebhookSecurityCategory.CONSTANT_TIME_COMPARISON,
            evidence_path="app/security/webhook_signature.py",
            description="Supplied and expected digests use constant-time comparison.",
        ),
        WebhookSecurityControl(
            name="event fingerprint",
            category=WebhookSecurityCategory.EVENT_FINGERPRINTING,
            evidence_path="app/services/webhook_normalizer.py",
            description="Synthetic canonical fingerprints provide a fallback event key.",
        ),
        WebhookSecurityControl(
            name="queue deduplication",
            category=WebhookSecurityCategory.DEDUPLICATION,
            evidence_path="app/services/event_queue.py",
            description="Queue insertion checks event keys and handles uniqueness races.",
        ),
        WebhookSecurityControl(
            name="redacted failures",
            category=WebhookSecurityCategory.REDACTION_AND_LOGGING,
            evidence_path="app/services/event_queue.py",
            description="Signature and processing failures omit submitted values.",
        ),
        WebhookSecurityControl(
            name="fixture validation",
            category=WebhookSecurityCategory.FIXTURE_SAFETY,
            evidence_path="app/fixtures/webhooks",
            description="Committed fixtures are synthetic and local.",
        ),
        WebhookSecurityControl(
            name="registration boundary",
            category=WebhookSecurityCategory.LIVE_REGISTRATION_BOUNDARY,
            evidence_path="docs/webhook-production-verification.md",
            description="Registration remains outside repository automation.",
        ),
    ]


def build_webhook_security_scenarios(settings: Settings) -> list[WebhookSecurityScenario]:
    boundaries = list(BOUNDARY_NAMES)
    return [
        WebhookSecurityScenario(
            category=category,
            boundary=boundaries[index % len(boundaries)],
            expectation=f"Review {category.value.replace('_', ' ')} without live operations.",
        )
        for index, category in enumerate(WebhookSecurityCategory)
    ]


def build_webhook_fixture_matrix(settings: Settings) -> list[WebhookFixtureMatrixItem]:
    root = Path("app/fixtures/webhooks")
    return [
        WebhookFixtureMatrixItem(fixture_name=path.name)
        for path in sorted(root.glob("*.json"))
        if path.is_file()
    ]


def _read(path: str) -> str:
    candidate = Path(path)
    return candidate.read_text(encoding="utf-8") if candidate.is_file() else ""


def build_webhook_security_review_report(settings: Settings) -> WebhookSecurityReviewReport:
    if not settings.webhook_security_review_enabled:
        raise WebhookSecurityReviewError("Webhook security review is disabled.")
    unsafe = any(
        (
            not settings.webhook_security_review_require_placeholders,
            not settings.webhook_security_review_require_signature_verification,
            not settings.webhook_security_review_require_constant_time_compare,
            not settings.webhook_security_review_require_replay_boundary,
            not settings.webhook_security_review_require_deduplication,
            not settings.webhook_security_review_require_redacted_failures,
            not settings.webhook_security_review_require_no_header_logging,
            not settings.webhook_security_review_require_no_live_replay,
            settings.webhook_security_review_allow_real_identities,
            settings.webhook_security_review_allow_real_domains,
            settings.webhook_security_review_allow_real_urls,
            settings.webhook_security_review_allow_report_contents,
            settings.webhook_security_review_allow_private_paths,
        )
    )
    if settings.webhook_security_review_fail_closed and unsafe:
        raise WebhookSecurityReviewBlockedError("Unsafe webhook review policy was blocked.")

    signature_code = _read("app/security/webhook_signature.py")
    receiver_code = _read("app/routers/webhooks.py")
    queue_code = _read("app/services/event_queue.py")
    normalizer_code = _read("app/services/webhook_normalizer.py")
    docs = "\n".join(
        _read(path)
        for path in (
            "docs/webhook-production-verification.md",
            "docs/https-webhook-production-planning.md",
            "docs/webhook-disable-rollback.md",
        )
    ).casefold()
    from app.schemas.auth_boundary_audit import (
        AuthBoundaryProtectionType,
        AuthBoundaryRouteClass,
    )
    from app.services.auth_boundary_audit import classify_route_auth_boundary
    from scripts.audit_routes_read_only import application_routes

    webhook_routes = [
        route
        for route in application_routes()
        if route.path.startswith(("/webhooks/", "/webhook-events"))
    ]
    receiver_routes = [route for route in webhook_routes if route.path.startswith("/webhooks/")]
    findings = [
        WebhookSecurityFinding(
            code="missing_review_evidence",
            message=f"Required webhook review evidence is missing: {path}.",
        )
        for path in REQUIRED_FILES
        if not Path(path).is_file()
    ]
    gitignore = _read(".gitignore")
    findings.extend(
        WebhookSecurityFinding(
            code="missing_ignore_rule",
            message=f"Missing webhook review output ignore rule: {pattern}.",
        )
        for pattern in IGNORED_OUTPUTS
        if pattern not in gitignore
    )
    findings.extend(
        (
            WebhookSecurityFinding(
                code="timestamp_replay_window_needs_review",
                message="Timestamp, nonce, or freshness-window enforcement is not implemented.",
            ),
            WebhookSecurityFinding(
                code="replay_route_access_needs_review",
                message="The local replay route requires private deployment-boundary review.",
            ),
            WebhookSecurityFinding(
                code="signature_runtime_configuration_needs_review",
                message="Runtime signature enforcement remains environment configuration.",
            ),
        )
    )
    for route in receiver_routes:
        classified = classify_route_auth_boundary(route)
        if (
            classified.route_class is not AuthBoundaryRouteClass.WEBHOOK_SIGNATURE_REQUIRED
            or classified.protection_type
            is not AuthBoundaryProtectionType.WEBHOOK_SIGNATURE_REQUIRED
        ):
            findings.append(
                WebhookSecurityFinding(
                    code="signature_route_classification_missing",
                    message="A webhook receiver lacks the I2 signature-boundary classification.",
                    severity="blocker",
                )
            )
    findings = findings[: settings.webhook_security_review_max_findings]
    categories = build_webhook_security_categories(settings)
    controls = build_webhook_security_controls(settings)
    scenarios = build_webhook_security_scenarios(settings)
    fixtures = build_webhook_fixture_matrix(settings)
    signature_documented = (
        all(marker in signature_code for marker in ("hmac.new", "hashlib.sha256", "compare_digest"))
        and "request.body()" in receiver_code
    )
    dedup_documented = (
        all(marker in queue_code for marker in ("event_id", "IntegrityError"))
        and "build_event_fingerprint" in normalizer_code
    )
    replay_documented = "replay_webhook_event" in queue_code and "replay" in docs
    redacted_documented = "sensitive details were intentionally omitted" in queue_code
    blockers = [item.message for item in findings if item.severity == "blocker"]
    status = (
        WebhookSecurityReviewStatus.BLOCKED
        if blockers
        else WebhookSecurityReviewStatus.NEEDS_REVIEW
        if findings
        else WebhookSecurityReviewStatus.READY
    )
    decision = {
        WebhookSecurityReviewStatus.BLOCKED: WebhookSecurityDecision.BLOCKED,
        WebhookSecurityReviewStatus.NEEDS_REVIEW: WebhookSecurityDecision.NEEDS_REVIEW,
        WebhookSecurityReviewStatus.READY: WebhookSecurityDecision.READY_FOR_SECURITY_REVIEW,
    }[status]
    report = WebhookSecurityReviewReport(
        status=status,
        decision=decision,
        categories=categories,
        boundaries=build_webhook_security_boundaries(settings),
        controls=controls,
        scenarios=scenarios,
        signature_expectation=WebhookSignatureExpectation(
            raw_body_used="request.body()" in receiver_code,
            constant_time_compare="compare_digest" in signature_code,
        ),
        replay_expectation=WebhookReplayExpectation(
            local_only=True,
            timestamp_window_implemented=False,
            deduplication_implemented=dedup_documented,
        ),
        fixture_matrix=fixtures,
        categories_total=len(categories),
        controls_total=len(controls),
        scenarios_total=len(scenarios),
        findings=findings,
        blockers=blockers,
        warnings=[item.message for item in findings],
        webhook_routes_total=len(webhook_routes),
        webhook_post_routes_total=sum(
            "POST" in (route.methods or set()) for route in webhook_routes
        ),
        signature_verification_documented=signature_documented,
        constant_time_compare_documented="compare_digest" in signature_code,
        replay_boundary_documented=replay_documented,
        deduplication_documented=dedup_documented,
        redacted_failures_documented=redacted_documented,
        recommended_next_steps=[
            "Review timestamp and replay-window expectations privately.",
            "Review replay-route authorization before any hosted use.",
            "Enable signature enforcement through private environment configuration.",
            "Treat this review as input, not certification or production authorization.",
        ],
    )
    validate_webhook_security_review_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_webhook_security_review_report_safe(
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
        raise WebhookSecurityReviewBlockedError("Unsafe webhook review content was blocked.")
    for line in text.splitlines():
        if UNSAFE_CLAIM.search(line) and not re.search(
            r"(?i)\b(?:no|not|never|does not|is not)\b", line
        ):
            raise WebhookSecurityReviewBlockedError("Unsafe webhook review claim was blocked.")


def render_webhook_security_review_markdown(report: WebhookSecurityReviewReport) -> str:
    lines = [
        "# Webhook Replay and Signature Hardening Review",
        "",
        f"Status: `{report.status.value}`",
        f"Decision: `{report.decision.value}`",
        "",
        "Offline fake-fixture review only. No live replay, registration, endpoint, or Procore "
        "operation was attempted.",
        "",
    ]
    lines.extend(f"- `{item.code}` — {item.message}" for item in report.findings)
    lines.extend(
        [
            "",
            "This review is not production authorization or security certification.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_webhook_security_review_report_safe(rendered)
    return rendered


def render_webhook_signature_boundary_markdown(
    report: WebhookSecurityReviewReport,
) -> str:
    lines = [
        "# Webhook Signature Boundary",
        "",
        "- HMAC-SHA256 expectation documented: `true`.",
        f"- Exact request bytes used: `{str(report.signature_expectation.raw_body_used).lower()}`.",
        "- Constant-time comparison expectation documented: "
        f"`{str(report.signature_expectation.constant_time_compare).lower()}`.",
        "- Submitted signatures, shared secrets, and request headers are not included.",
        "",
    ]
    rendered = "\n".join(lines)
    validate_webhook_security_review_report_safe(rendered)
    return rendered


def render_webhook_replay_checklist_markdown(
    report: WebhookSecurityReviewReport,
) -> str:
    lines = [
        "# Webhook Replay Checklist",
        "",
        "- [ ] Keep replay local-only and privately authorized.",
        "- [ ] Define timestamp, nonce, or freshness-window policy.",
        "- [ ] Preserve event fingerprinting and deduplication.",
        "- [ ] Preserve bounded retries, locks, and redacted failures.",
        "- [ ] Do not replay against a live endpoint.",
        "- [ ] Do not register or change remote webhooks.",
        "",
    ]
    rendered = "\n".join(lines)
    validate_webhook_security_review_report_safe(rendered)
    return rendered


def _csv_cell(value: Any) -> str:
    text = sanitize_webhook_security_value(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_webhook_fixture_matrix_csv(report: WebhookSecurityReviewReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("fixture", "placeholder_only", "live_payload", "live_headers", "signature"))
    for item in report.fixture_matrix:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.fixture_name,
                    str(item.placeholder_only).lower(),
                    str(item.live_payload).lower(),
                    str(item.live_headers).lower(),
                    str(item.signature_included).lower(),
                )
            )
        )
    rendered = output.getvalue()
    validate_webhook_security_review_report_safe(rendered)
    return rendered


def _safe_output_root(output_root: Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-webhook-security-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if ".." in root.parts or (root.is_absolute() and not temporary):
        raise WebhookSecurityReviewBlockedError("Unsafe webhook review output root.")
    if not temporary and root.parts[:1] not in {(name,) for name in SAFE_ROOTS}:
        raise WebhookSecurityReviewBlockedError("Unapproved webhook review output root.")
    return root


def write_webhook_security_review_artifacts(
    report: WebhookSecurityReviewReport, output_root: Path
) -> WebhookSecurityArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "webhook-security-review-report.json": report.model_dump_json(indent=2),
        "webhook-security-review-report.md": render_webhook_security_review_markdown(report),
        "webhook-signature-boundary.md": render_webhook_signature_boundary_markdown(report),
        "webhook-replay-checklist.md": render_webhook_replay_checklist_markdown(report),
        "webhook-fixture-matrix.csv": render_webhook_fixture_matrix_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {"files": sorted(artifacts), "live_operations": False, "sanitized": True},
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        validate_webhook_security_review_report_safe(content)
        (root / name).write_text(content, encoding="utf-8")
    return WebhookSecurityArtifactResult(
        status=report.status,
        output_directory=root.name,
        files=sorted(artifacts),
    )
