import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.schemas.webhook_verification import (
    WebhookDocsFinding,
    WebhookDocsVerificationRecord,
    WebhookFixtureValidationResult,
    WebhookReceiverProbeResult,
    WebhookVerificationPlan,
    WebhookVerificationReport,
    WebhookVerificationStepResult,
)
from app.security.webhook_signature import WebhookSignatureResult
from app.services.event_queue import enqueue_webhook_event
from app.services.webhook_normalizer import (
    build_event_fingerprint,
    normalize_procore_webhook_event,
    sanitize_payload,
)

MAX_WEBHOOK_VERIFICATION_EVENTS = 10
FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "webhooks"
FIXTURE_NAMES = (
    "procore_rfi_created_v2_like.json",
    "procore_rfi_updated_v2_like.json",
    "procore_submittal_created_v2_like.json",
    "procore_submittal_updated_v2_like.json",
    "procore_unknown_event_v2_like.json",
    "procore_malformed_missing_resource.json",
)
_SIGNATURE = WebhookSignatureResult(
    verified=False, status="synthetic", message="Synthetic probe."
)


class WebhookVerificationError(RuntimeError):
    """A sanitized local webhook verification operation failed."""


class WebhookVerificationBlockedError(WebhookVerificationError):
    """A manual safety gate blocked webhook verification."""


def sanitize_webhook_verification_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(term in normalized for term in (
                "authorization", "signature", "secret", "token", "password", "credential"
            )):
                result[str(key)] = "[redacted]"
            elif normalized in {"payload", "raw_payload", "body", "headers"}:
                result[str(key)] = "[omitted]"
            else:
                result[str(key)] = sanitize_webhook_verification_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_webhook_verification_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if re.search(r"(?i)(authorization\s*:|bearer\s+|signature\s*[:=]|secret\s*[:=])", value):
            return "[redacted]"
        if re.search(r"(?i)^https?://", value):
            return "url_sha256:" + hashlib.sha256(value.encode()).hexdigest()
    return value


def build_webhook_verification_plan(settings: Settings) -> WebhookVerificationPlan:
    return WebhookVerificationPlan(
        enabled=settings.webhook_verification_enabled,
        environment=settings.environment,
        confirmation_required=settings.webhook_verification_require_confirmation,
        production_allowed=settings.webhook_verification_allow_production,
        docs_check_required=settings.webhook_verification_require_docs_check,
        configured_docs_status=settings.webhook_verification_docs_status,
        expected_payload_version=settings.webhook_verification_expected_payload_version,
        expected_scope=settings.webhook_verification_expected_scope,
        max_events=min(settings.webhook_verification_max_events, MAX_WEBHOOK_VERIFICATION_EVENTS),
        write_report=settings.webhook_verification_write_report,
        steps=[
            "Validate manual, production, and documentation gates",
            "Load only committed v2-like synthetic fixtures",
            "Probe local receiver and normalization behavior in memory",
            "Probe fingerprint deduplication and queue outcomes in memory",
            "Build an optional sanitized JSON report",
        ],
        warning=(
            "This verifies local assumptions only. It performs no network or Procore calls, "
            "does not register hooks, and does not expose a receiver."
        ),
    )


def validate_webhook_docs_record(
    docs_record: WebhookDocsVerificationRecord, settings: Settings
) -> list[WebhookDocsFinding]:
    findings: list[WebhookDocsFinding] = []
    serialized = json.dumps(docs_record.model_dump(mode="json"))
    dumped = docs_record.model_dump(mode="json")
    raw_url_present = any(
        isinstance(value, str) and re.search(r"(?i)^https?://", value)
        for value in _walk_values(dumped)
    )
    if raw_url_present:
        findings.append(WebhookDocsFinding(
            code="sensitive_content", severity="error",
            message="The record contains sensitive or raw URL-like content.",
        ))
    if docs_record.status != "verified":
        findings.append(WebhookDocsFinding(
            code="docs_status", severity="warning",
            message="Manual documentation verification is not complete.",
        ))
    if not docs_record.docs_checked_at or not docs_record.verified_by_operator.strip():
        findings.append(WebhookDocsFinding(
            code="operator_record", severity="error",
            message="A check timestamp and operator placeholder are required for verified status.",
        ))
    if docs_record.observed_api_version.casefold().startswith("v1"):
        findings.append(WebhookDocsFinding(
            code="deprecated_v1_only", severity="error",
            message="A v1-only webhook assumption is deprecated and cannot authorize production.",
        ))
    if docs_record.observed_scope_model != settings.webhook_verification_expected_scope:
        findings.append(WebhookDocsFinding(
            code="scope_mismatch", severity="error",
            message="Observed scope does not match the configured expected scope.",
        ))
    if docs_record.signature_assumption_status != "verified":
        findings.append(WebhookDocsFinding(
            code="signature_assumption", severity="error",
            message="Signature assumptions require manual verification.",
        ))
    if docs_record.payload_shape_assumption_status != "verified":
        findings.append(WebhookDocsFinding(
            code="payload_assumption", severity="error",
            message="Payload shape assumptions require manual verification.",
        ))
    if re.search(r"(?i)(authorization|bearer|webhook[_ -]?secret|signature\s*[:=])", serialized):
        findings.append(WebhookDocsFinding(
            code="secret_material", severity="error",
            message="The record must not contain authorization, signature, or secret material.",
        ))
    return findings


def validate_webhook_verification_gates(
    settings: Settings,
    confirmation_phrase: str,
    docs_record: WebhookDocsVerificationRecord | None = None,
) -> None:
    blockers = []
    if not settings.webhook_verification_enabled:
        blockers.append("webhook verification is disabled")
    if (
        settings.webhook_verification_require_confirmation
        and confirmation_phrase != settings.webhook_verification_confirmation_phrase
    ):
        blockers.append("manual confirmation is missing or incorrect")
    if settings.environment == "production" and not settings.webhook_verification_allow_production:
        blockers.append("the production deployment profile is blocked")
    if settings.webhook_verification_max_events > MAX_WEBHOOK_VERIFICATION_EVENTS:
        blockers.append("the event limit exceeds the hard safety cap")
    if settings.webhook_verification_require_docs_check:
        if docs_record is None:
            blockers.append("a local documentation verification record is required")
        elif docs_record.status != "verified" or any(
            f.severity == "error" for f in validate_webhook_docs_record(docs_record, settings)
        ):
            blockers.append("the documentation record is not verified and ready")
    if blockers:
        raise WebhookVerificationBlockedError(
            "Webhook verification blocked: " + "; ".join(blockers) + "."
        )


def validate_webhook_fixture_payload(
    payload: dict[str, Any], fixture_label: str = "synthetic"
) -> WebhookFixtureValidationResult:
    marker = payload.get("_fixture_notice")
    normalized = normalize_procore_webhook_event(payload, {})
    findings = []
    if marker != "v2-like synthetic fixture, not official sample payload":
        findings.append("missing synthetic fixture notice")
    if any(key.casefold() == "authorization" for key in _walk_keys(payload)):
        findings.append("authorization field is forbidden")
    serialized = json.dumps(payload)
    if re.search(r"(?i)https?://|bearer\s+|signature\s*[:=]", serialized):
        findings.append("URL, authorization, or signature-like content is forbidden")
    sanitized = sanitize_payload(payload)
    return WebhookFixtureValidationResult(
        fixture_label=fixture_label,
        status="failed" if findings else "passed",
        resource_type=normalized["resource_type"],
        action=normalized["action"],
        event_fingerprint=build_event_fingerprint(payload),
        sensitive_fields_redacted=json.dumps(sanitized).find("[REDACTED]") >= 0
        or not any(_is_sensitive_key(key) for key in _walk_keys(payload)),
        findings=findings,
    )


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _walk_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _is_sensitive_key(key: str) -> bool:
    return any(term in key.casefold() for term in ("authorization", "signature", "secret", "token"))


def _session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def run_webhook_receiver_probe(payloads: list[dict[str, Any]]) -> WebhookReceiverProbeResult:
    accepted = skipped = 0
    with _session() as session:
        for payload in payloads:
            event, _ = enqueue_webhook_event(session, payload, {}, _SIGNATURE, persist=False)
            if event.processing_status == "queued":
                accepted += 1
            else:
                skipped += 1
    return WebhookReceiverProbeResult(
        status="passed", accepted_count=accepted, skipped_count=skipped,
        summary="Synthetic payloads traversed the local receiver queue path without persistence.",
    )


def run_webhook_normalizer_probe(
    payloads: list[dict[str, Any]],
) -> WebhookVerificationStepResult:
    results = [
        validate_webhook_fixture_payload(payload, f"fixture-{index + 1}")
        for index, payload in enumerate(payloads)
    ]
    known = sum(
        result.resource_type in {"rfi", "submittal"}
        and result.action in {"created", "updated"}
        for result in results
    )
    unknown = sum(r.resource_type == "unknown" for r in results)
    passed = all(r.status == "passed" for r in results) and known >= 4 and unknown >= 1
    return WebhookVerificationStepResult(
        name="normalizer", status="passed" if passed else "failed",
        summary=(
            "Validated synthetic RFI/Submittal created/updated, unknown, and malformed handling."
        ),
        details={
            "fixture_count": len(results),
            "known_event_count": known,
            "safe_unknown_count": unknown,
        },
    )


def run_webhook_deduplication_probe(payload: dict[str, Any]) -> WebhookReceiverProbeResult:
    with _session() as session:
        _, first_duplicate = enqueue_webhook_event(session, payload, {}, _SIGNATURE)
        _, second_duplicate = enqueue_webhook_event(session, payload, {}, _SIGNATURE)
    duplicate_count = int(first_duplicate) + int(second_duplicate)
    return WebhookReceiverProbeResult(
        status="passed" if duplicate_count == 1 else "failed",
        accepted_count=1, skipped_count=0, duplicate_count=duplicate_count,
        summary="A repeated synthetic fingerprint was detected without real identifiers.",
    )


def run_webhook_event_queue_probe(payload: dict[str, Any]) -> WebhookReceiverProbeResult:
    with _session() as session:
        event, duplicate = enqueue_webhook_event(session, payload, {}, _SIGNATURE)
        queued = event.processing_status == "queued" and not duplicate
    return WebhookReceiverProbeResult(
        status="passed" if queued else "failed",
        accepted_count=int(queued), skipped_count=int(not queued),
        summary="A synthetic event entered the isolated local queue; no worker or live sync ran.",
    )


def load_synthetic_webhook_fixtures(
    limit: int = MAX_WEBHOOK_VERIFICATION_EVENTS,
) -> list[dict[str, Any]]:
    return [json.loads((FIXTURE_ROOT / name).read_text()) for name in FIXTURE_NAMES[:limit]]


def build_webhook_verification_report(
    settings: Settings, docs_record: WebhookDocsVerificationRecord
) -> WebhookVerificationReport:
    payloads = load_synthetic_webhook_fixtures(settings.webhook_verification_max_events)
    receiver = run_webhook_receiver_probe(payloads)
    normalizer = run_webhook_normalizer_probe(payloads)
    dedup = run_webhook_deduplication_probe(payloads[0])
    queue = run_webhook_event_queue_probe(payloads[0])
    steps = [
        WebhookVerificationStepResult(
            name="receiver", status=receiver.status, summary=receiver.summary,
            details={
                "accepted_count": receiver.accepted_count,
                "skipped_count": receiver.skipped_count,
            },
        ),
        normalizer,
        WebhookVerificationStepResult(
            name="deduplication", status=dedup.status, summary=dedup.summary,
            details={"duplicate_count": dedup.duplicate_count},
        ),
        WebhookVerificationStepResult(
            name="event_queue", status=queue.status, summary=queue.summary,
            details={"queued_count": queue.accepted_count},
        ),
    ]
    overall = "passed" if all(step.status == "passed" for step in steps) else "failed"
    return WebhookVerificationReport(
        generated_at=datetime.now(UTC), environment=settings.environment,
        fixture_count=len(payloads), docs_status=docs_record.status,
        steps=steps, overall_status=overall,
    )


def write_webhook_verification_report(
    report: WebhookVerificationReport, output_root: Path
) -> Path:
    root = output_root.resolve()
    cwd = Path.cwd().resolve()
    path_traversal = ".." in output_root.parts
    if output_root in {Path("."), Path("/")} or root == cwd or path_traversal:
        raise WebhookVerificationError("Unsafe webhook verification output path.")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"webhook-{report.generated_at:%Y%m%dT%H%M%SZ}.webhook-verification.json"
    safe = sanitize_webhook_verification_value(report.model_dump(mode="json"))
    path.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n")
    return path
