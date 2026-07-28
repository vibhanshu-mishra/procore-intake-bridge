import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings
from app.models.connections import DMSAConnection, ProcoreEnvironment
from app.schemas.sandbox_smoke import (
    SandboxSmokeConfigSummary,
    SandboxSmokeFinding,
    SandboxSmokePlan,
    SandboxSmokeReport,
    SandboxSmokeStepResult,
)
from app.services.deployment_readiness import build_deployment_readiness_report
from app.services.procore_client import (
    build_pyprocore_client_for_connection,
    check_project_access,
)

MAX_SANDBOX_SMOKE_RECORDS = 10


class SandboxSmokeError(RuntimeError):
    """A sanitized sandbox smoke operation failed."""


class SandboxSmokeBlockedError(SandboxSmokeError):
    """A required manual safety gate blocked execution."""


class SandboxProbe(Protocol):
    def authenticate(self) -> bool: ...

    def project_access(self) -> bool: ...

    def list_rfis(self, limit: int) -> Sequence[Any]: ...

    def list_submittals(self, limit: int) -> Sequence[Any]: ...


class PyProcoreSandboxProbe:
    """Minimal read-only adapter. It has no mutation or attachment-download methods."""

    def __init__(
        self,
        settings: Settings,
        connection: DMSAConnection,
        project_id: str,
        company_id: str,
    ):
        self.connection = connection
        self.project_id = project_id
        self.company_id = company_id
        self.client = build_pyprocore_client_for_connection(connection, settings=settings)
        self._project_verified = False

    def authenticate(self) -> bool:
        self._project_verified = check_project_access(
            self.client, self.connection, self.project_id
        )
        return self._project_verified

    def project_access(self) -> bool:
        return self._project_verified

    def list_rfis(self, limit: int) -> Sequence[Any]:
        return list(
            self.client.get_all(
                f"/rest/v1.0/projects/{int(self.project_id)}/rfis",
                params={"per_page": limit, "company_id": int(self.company_id)},
            )
        )[:limit]

    def list_submittals(self, limit: int) -> Sequence[Any]:
        return list(
            self.client.get_all(
                f"/rest/v1.0/projects/{int(self.project_id)}/submittals",
                params={"per_page": limit, "company_id": int(self.company_id)},
            )
        )[:limit]


ProbeFactory = Callable[
    [Settings, DMSAConnection, str, str],
    SandboxProbe,
]


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build_sandbox_smoke_plan(
    settings: Settings,
    connection_id: int | None = None,
    project_id: str | None = None,
    company_id: str | None = None,
) -> SandboxSmokePlan:
    return SandboxSmokePlan(
        enabled=settings.sandbox_smoke_enabled,
        environment=settings.environment,
        confirmation_required=settings.sandbox_smoke_require_confirmation,
        max_records=min(settings.sandbox_smoke_max_records, MAX_SANDBOX_SMOKE_RECORDS),
        connection_configured=bool(connection_id or settings.sandbox_smoke_connection_id),
        project_configured=bool(project_id or settings.sandbox_smoke_project_id),
        company_configured=bool(company_id or settings.sandbox_smoke_company_id),
        warning=(
            "Manual, read-only, sandbox-only plan. No Procore writes, attachment downloads, "
            "raw payload persistence, or automatic execution."
        ),
        steps=[
            "Validate every manual sandbox gate",
            "Summarize deployment readiness",
            "Check credential references without displaying or resolving them",
            "Construct the guarded PyProcore client and authenticate",
            "Probe only the explicitly allowed project",
            "Read bounded RFI and Submittal samples",
            "Count attachment metadata without downloading files",
            "Build an optional sanitized local JSON report",
        ],
    )


def validate_sandbox_smoke_gates(
    settings: Settings,
    confirmation_phrase: str,
    connection: DMSAConnection | None,
    project_id: str | None,
    company_id: str | None,
) -> None:
    blockers: list[str] = []
    if not settings.sandbox_smoke_enabled:
        blockers.append("sandbox smoke is disabled")
    if (
        settings.sandbox_smoke_require_confirmation
        and confirmation_phrase != settings.sandbox_smoke_confirmation_phrase
    ):
        blockers.append("manual confirmation is missing or incorrect")
    if settings.environment == "production" and not settings.sandbox_smoke_allow_production:
        blockers.append("the production deployment profile is blocked")
    if not settings.procore_live_mode_enabled:
        blockers.append("the explicit live-mode gate is disabled")
    if settings.procore_environment != "sandbox":
        blockers.append("the Procore API target is not sandbox")
    if settings.sandbox_smoke_attachment_downloads:
        blockers.append("attachment downloads must remain disabled")
    if settings.sandbox_smoke_max_records > MAX_SANDBOX_SMOKE_RECORDS:
        blockers.append("the record limit exceeds the hard safety cap")
    if connection is None:
        blockers.append("the local connection does not exist")
    if not project_id or not company_id:
        blockers.append("explicit project and company identifiers are required")
    if connection is not None:
        if connection.environment != ProcoreEnvironment.SANDBOX:
            blockers.append("the connection is not marked sandbox")
        if not connection.client_id_ref or not connection.secret_name:
            blockers.append("credential references are incomplete")
        if project_id and project_id not in connection.permitted_project_ids:
            blockers.append("the project is not in the connection allowlist")
        if company_id and company_id != connection.procore_company_id:
            blockers.append("the company does not match the connection")
    if blockers:
        raise SandboxSmokeBlockedError(
            "Sandbox smoke blocked: " + "; ".join(blockers) + "."
        )


def sanitize_smoke_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(
                term in normalized
                for term in (
                    "access_token",
                    "authorization",
                    "client_secret",
                    "refresh_token",
                    "secret",
                    "signature",
                )
            ):
                result[str(key)] = "[redacted]"
            elif normalized in {"payload", "raw_payload", "response_body"}:
                result[str(key)] = "[omitted]"
            else:
                result[str(key)] = sanitize_smoke_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_smoke_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if re.search(r"(?i)authorization\s*:\s*bearer", value):
            return "[redacted authorization]"
        if re.search(
            r"(?i)(access_token|client_secret|refresh_token|webhook_secret)\s*[:=]",
            value,
        ):
            return "[redacted secret]"
        if re.search(r"(?i)^https?://", value):
            return f"url_sha256:{_hash_identifier(value)}"
        if value.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:\\", value):
            return Path(value).name
    return value


def summarize_smoke_config(settings: Settings) -> SandboxSmokeConfigSummary:
    return SandboxSmokeConfigSummary(
        enabled=settings.sandbox_smoke_enabled,
        environment=settings.environment,
        production_allowed=settings.sandbox_smoke_allow_production,
        confirmation_required=settings.sandbox_smoke_require_confirmation,
        confirmation_phrase_configured=bool(
            settings.sandbox_smoke_confirmation_phrase
        ),
        live_mode_enabled=settings.procore_live_mode_enabled,
        max_records=min(settings.sandbox_smoke_max_records, MAX_SANDBOX_SMOKE_RECORDS),
        attachment_downloads=settings.sandbox_smoke_attachment_downloads,
        write_report=settings.sandbox_smoke_write_report,
        output_root_configured=bool(settings.sandbox_smoke_output_root),
        connection_configured=settings.sandbox_smoke_connection_id is not None,
        project_configured=bool(settings.sandbox_smoke_project_id),
        company_configured=bool(settings.sandbox_smoke_company_id),
    )


def _record_value(record: Any, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def _summarize_records(records: Sequence[Any]) -> dict[str, Any]:
    return {
        "count": len(records),
        "identifier_hashes": [
            _hash_identifier(str(identifier))
            for record in records
            if (identifier := _record_value(record, "id")) is not None
        ],
        "statuses": sorted(
            {
                str(status)[:80]
                for record in records
                if (status := _record_value(record, "status")) is not None
            }
        ),
    }


def _attachment_summary(records: Sequence[Any]) -> dict[str, Any]:
    visible = 0
    url_hashes: list[str] = []
    for record in records:
        attachments = _record_value(record, "attachments") or []
        if not isinstance(attachments, Sequence) or isinstance(attachments, (str, bytes)):
            continue
        visible += len(attachments)
        for attachment in attachments:
            for key in ("url", "download_url", "signed_url"):
                url = _record_value(attachment, key)
                if isinstance(url, str) and url:
                    url_hashes.append(_hash_identifier(url))
    return {
        "visible_attachment_count": visible,
        "source_url_hashes": url_hashes,
        "downloads_attempted": False,
    }


def _passed(name: str, summary: str, **details: Any) -> SandboxSmokeStepResult:
    return SandboxSmokeStepResult(
        name=name,
        status="passed",
        summary=summary,
        details=sanitize_smoke_value(details),
    )


def run_sandbox_dmsa_smoke(
    settings: Settings,
    connection: DMSAConnection | None,
    confirmation_phrase: str,
    project_id: str | None,
    company_id: str | None,
    probe_factory: ProbeFactory | None = None,
) -> SandboxSmokeReport:
    validate_sandbox_smoke_gates(
        settings, confirmation_phrase, connection, project_id, company_id
    )
    assert connection is not None and project_id is not None and company_id is not None
    steps = [
        _passed("gate_validation", "All explicit manual sandbox gates passed."),
    ]
    readiness = build_deployment_readiness_report(settings)
    if settings.environment == "production" and not readiness.ready_for_production:
        raise SandboxSmokeBlockedError(
            "Sandbox smoke blocked: the production deployment profile has "
            "sanitized readiness blockers."
        )
    steps.append(
        _passed(
            "deployment_readiness",
            "Deployment readiness was summarized without treating local blockers as approval.",
            ready_for_local=readiness.ready_for_local,
            ready_for_production=readiness.ready_for_production,
            blocking_findings_count=readiness.blocking_findings_count,
        )
    )
    steps.append(
        _passed(
            "credential_references",
            "Required credential references are configured; values are not reported.",
            client_id_reference_configured=bool(connection.client_id_ref),
            client_secret_reference_configured=bool(connection.secret_name),
        )
    )
    factory = probe_factory or PyProcoreSandboxProbe
    records: list[Any] = []
    findings: list[SandboxSmokeFinding] = []
    try:
        probe = factory(settings, connection, project_id, company_id)
        authenticated = probe.authenticate()
        steps.append(
            SandboxSmokeStepResult(
                name="auth_probe",
                status="passed" if authenticated else "failed",
                summary=(
                    "Guarded PyProcore authentication succeeded."
                    if authenticated
                    else "Guarded PyProcore authentication did not succeed."
                ),
            )
        )
        if not authenticated:
            raise SandboxSmokeError("Authentication did not pass.")
        project_ok = probe.project_access()
        steps.append(
            SandboxSmokeStepResult(
                name="project_access",
                status="passed" if project_ok else "failed",
                summary=(
                    "The explicitly allowed sandbox project was readable."
                    if project_ok
                    else "The explicitly allowed sandbox project was not readable."
                ),
            )
        )
        if not project_ok:
            raise SandboxSmokeError("Project access did not pass.")
        for name, enabled_tool, operation in (
            ("rfi_read_probe", "rfis", probe.list_rfis),
            ("submittal_read_probe", "submittals", probe.list_submittals),
        ):
            if enabled_tool not in connection.enabled_tools:
                steps.append(
                    SandboxSmokeStepResult(
                        name=name,
                        status="skipped",
                        summary="The tool is not enabled on this local connection.",
                    )
                )
                continue
            values = list(operation(settings.sandbox_smoke_max_records))[
                : settings.sandbox_smoke_max_records
            ]
            records.extend(values)
            steps.append(
                _passed(
                    name,
                    f"Read-only {enabled_tool} probe completed within the configured limit.",
                    **_summarize_records(values),
                )
            )
        steps.append(
            _passed(
                "attachment_metadata",
                "Visible attachment metadata was counted without downloading files.",
                **_attachment_summary(records),
            )
        )
    except Exception as exc:
        steps.append(
            SandboxSmokeStepResult(
                name="live_probe",
                status="failed",
                summary=f"Live read probe failed safely ({type(exc).__name__}).",
            )
        )
        findings.append(
            SandboxSmokeFinding(
                code="live_probe_failed",
                severity="error",
                message="A live read-only probe failed; sensitive exception details were omitted.",
            )
        )
    return SandboxSmokeReport(
        environment=settings.environment,
        live_mode_explicitly_enabled=settings.procore_live_mode_enabled,
        max_records=settings.sandbox_smoke_max_records,
        connection_id=connection.id,
        company_id_hash=_hash_identifier(company_id),
        project_id_hash=_hash_identifier(project_id),
        steps=steps,
        findings=findings,
        generated_at=datetime.now(UTC),
    )


def write_sandbox_smoke_report(
    report: SandboxSmokeReport, output_root: Path
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.strftime("%Y%m%dT%H%M%SZ")
    path = output_root / f"sandbox-smoke-{timestamp}.smoke.json"
    path.write_text(
        json.dumps(sanitize_smoke_value(report.model_dump(mode="json")), indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path
