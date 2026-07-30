from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings
from app.schemas.sandbox_read_validation import (
    SandboxReadValidationArtifactResult,
    SandboxReadValidationDecision,
    SandboxReadValidationEvidenceRef,
    SandboxReadValidationFinding,
    SandboxReadValidationProbe,
    SandboxReadValidationReport,
    SandboxReadValidationRequirement,
    SandboxReadValidationScope,
    SandboxReadValidationStatus,
    SandboxReadValidationTool,
    SandboxReadValidationToolResult,
)

CONFIRMATION_PHRASE = "I understand this will make read-only Procore sandbox API calls"
ARTIFACT_NAMES = (
    "sandbox-read-report.json",
    "sandbox-read-report.md",
    "sandbox-read-evidence.json",
    "sandbox-read-evidence.md",
)
MAX_PROJECTS = 3
MAX_ITEMS_PER_TOOL = 5
MAX_PAGES = 2
MAX_TIMEOUT_SECONDS = 20
SAFE_OUTPUT_NAMES = {
    "sandbox-read-output",
    "sandbox-validation-output",
    "read-validation-output",
}


class SandboxReadValidationError(RuntimeError):
    """A sanitized sandbox read-validation operation failed."""


class SandboxReadValidationBlockedError(SandboxReadValidationError):
    """A mandatory manual safety gate blocked live reads."""


class SandboxReadClient(Protocol):
    credential_refs_configured: bool
    sandbox_environment: bool
    allowed_scope_configured: bool

    def list_rfis(
        self, *, page: int, per_page: int, updated_since: str | None
    ) -> Sequence[Any]: ...

    def get_rfi(self, identifier: Any) -> Any: ...

    def list_submittals(
        self, *, page: int, per_page: int, updated_since: str | None
    ) -> Sequence[Any]: ...

    def get_submittal(self, identifier: Any) -> Any: ...


class PyProcoreSandboxReadClient:
    """Bounded read-only wrapper with no mutation, webhook, or attachment methods."""

    credential_refs_configured = True
    sandbox_environment = True
    allowed_scope_configured = True

    def __init__(self, client: Any, company_id: str, project_id: str):
        self._client = client
        self._company_id = company_id
        self._project_id = project_id

    @staticmethod
    def _items(response: Any) -> list[Any]:
        if isinstance(response, Mapping):
            values = response.get("data", response.get("items", []))
            return list(values) if isinstance(values, Sequence) else []
        if isinstance(response, Sequence) and not isinstance(response, (str, bytes)):
            return list(response)
        return []

    def _list(self, tool: str, page: int, per_page: int) -> list[Any]:
        response = self._client.get(
            f"/rest/v1.0/projects/{int(self._project_id)}/{tool}",
            params={
                "company_id": int(self._company_id),
                "page": page,
                "per_page": per_page,
            },
        )
        return self._items(response)

    def _detail(self, tool: str, identifier: Any) -> Any:
        return self._client.get(
            f"/rest/v1.0/projects/{int(self._project_id)}/{tool}/{int(identifier)}",
            params={"company_id": int(self._company_id)},
        )

    def list_rfis(
        self, *, page: int, per_page: int, updated_since: str | None
    ) -> Sequence[Any]:
        return self._list("rfis", page, per_page)

    def get_rfi(self, identifier: Any) -> Any:
        return self._detail("rfis", identifier)

    def list_submittals(
        self, *, page: int, per_page: int, updated_since: str | None
    ) -> Sequence[Any]:
        return self._list("submittals", page, per_page)

    def get_submittal(self, identifier: Any) -> Any:
        return self._detail("submittals", identifier)


def hash_sandbox_identifier(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def mask_sandbox_identifier(value: Any) -> str:
    return f"masked:{len(str(value))}"


def sanitize_sandbox_read_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(
                term in normalized
                for term in (
                    "authorization",
                    "secret",
                    "token",
                    "signature",
                    "payload",
                    "description",
                    "subject",
                    "title",
                    "vendor",
                    "email",
                    "phone",
                    "filename",
                    "url",
                )
            ):
                safe[str(key)] = "[omitted]"
            elif normalized.endswith("_id") or normalized == "id":
                safe[str(key)] = hash_sandbox_identifier(item)
            else:
                safe[str(key)] = sanitize_sandbox_read_value(item)
        return safe
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [sanitize_sandbox_read_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if re.search(r"(?i)https?://|(?:postgres(?:ql)?|mysql)://", value):
            return "[omitted url]"
        if re.search(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", value):
            return "[omitted contact]"
        if value.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:\\", value):
            return "[omitted path]"
        if re.search(
            r"(?i)(?:authorization|client_secret|access_token|webhook_secret)\s*[:=]",
            value,
        ):
            return "[omitted secret]"
    return value


def _tools(settings: Settings) -> tuple[SandboxReadValidationTool, ...]:
    selected: list[SandboxReadValidationTool] = []
    for value in settings.sandbox_read_validation_allowed_tools.split(","):
        normalized = value.strip().casefold()
        if normalized in {tool.value for tool in SandboxReadValidationTool}:
            tool = SandboxReadValidationTool(normalized)
            if tool not in selected:
                selected.append(tool)
    return tuple(selected)


def validate_sandbox_read_settings(
    settings: Settings,
) -> tuple[SandboxReadValidationFinding, ...]:
    findings: list[SandboxReadValidationFinding] = []

    def block(code: str, message: str) -> None:
        findings.append(
            SandboxReadValidationFinding(
                code=code,
                status=SandboxReadValidationStatus.BLOCKED,
                message=message,
                blocking=True,
            )
        )

    if settings.sandbox_read_validation_include_attachments:
        block("attachments_enabled", "Attachment inclusion must remain disabled.")
    if settings.sandbox_read_validation_store_raw:
        block("raw_storage_enabled", "Raw payload storage must remain disabled.")
    if not settings.sandbox_read_validation_fail_closed:
        block("fail_open", "Read validation must fail closed.")
    if not settings.sandbox_read_validation_mask_ids:
        block("id_masking_disabled", "Identifier masking must remain enabled.")
    if not settings.sandbox_read_validation_hash_ids:
        block("id_hashing_disabled", "Identifier hashing must remain enabled.")
    if settings.sandbox_read_validation_max_projects > MAX_PROJECTS:
        block("project_limit", "The project limit exceeds the hard safety cap.")
    if settings.sandbox_read_validation_max_items_per_tool > MAX_ITEMS_PER_TOOL:
        block("item_limit", "The item limit exceeds the hard safety cap.")
    if settings.sandbox_read_validation_max_pages > MAX_PAGES:
        block("page_limit", "The page limit exceeds the hard safety cap.")
    if settings.sandbox_read_validation_timeout_seconds > MAX_TIMEOUT_SECONDS:
        block("timeout_limit", "The timeout exceeds the hard safety cap.")
    if not _tools(settings):
        block("tools_missing", "At least one supported read-only tool is required.")
    return tuple(findings)


def _requirements(settings: Settings) -> tuple[SandboxReadValidationRequirement, ...]:
    configured_scope = bool(
        settings.sandbox_smoke_company_id and settings.sandbox_smoke_project_id
    )
    values = (
        (
            "manual_enablement",
            settings.sandbox_read_validation_enabled,
            "Enable only for a separately authorized manual live run.",
        ),
        (
            "exact_confirmation",
            settings.sandbox_read_validation_confirmation == CONFIRMATION_PHRASE,
            "Set the exact read-only sandbox confirmation privately.",
        ),
        (
            "sandbox_target",
            settings.procore_environment == "sandbox",
            "The Procore environment must be sandbox.",
        ),
        (
            "live_mode_gate",
            settings.procore_live_mode_enabled,
            "The existing live-mode gate is required only for manual execution.",
        ),
        (
            "dmsa_connection_profile",
            settings.sandbox_smoke_connection_id is not None,
            "Configure a private DMSA connection profile with credential references.",
        ),
        (
            "allowed_scope",
            configured_scope,
            "Configure an explicit private company and project allowlist.",
        ),
    )
    return tuple(
        SandboxReadValidationRequirement(
            name=name,
            status=(
                SandboxReadValidationStatus.READY
                if configured
                else SandboxReadValidationStatus.NEEDS_CONFIGURATION
            ),
            guidance=guidance,
        )
        for name, configured, guidance in values
    )


def build_sandbox_read_evidence_ref(
    report: SandboxReadValidationReport | None,
    settings: Settings,
) -> SandboxReadValidationEvidenceRef:
    return SandboxReadValidationEvidenceRef(
        validation_ref="SANDBOX_READ_VALIDATION_REF_PLACEHOLDER",
        run_label="SANDBOX_READ_RUN_LABEL_PLACEHOLDER",
        scope_ref="SANDBOX_SCOPE_REF_PLACEHOLDER",
        rfi_access_status="SANDBOX_RFI_ACCESS_STATUS_PLACEHOLDER",
        submittal_access_status="SANDBOX_SUBMITTAL_ACCESS_STATUS_PLACEHOLDER",
        pagination_status="SANDBOX_PAGINATION_STATUS_PLACEHOLDER",
        date_filter_status="SANDBOX_DATE_FILTER_STATUS_PLACEHOLDER",
        reviewer_placeholder="SANDBOX_REVIEWER_PLACEHOLDER",
        expiry_placeholder="SANDBOX_EXPIRY_PLACEHOLDER",
    )


def _base_report(
    settings: Settings,
    *,
    status: SandboxReadValidationStatus,
    decision: SandboxReadValidationDecision,
    validation_attempted: bool = False,
    live_calls_attempted: bool = False,
    findings: tuple[SandboxReadValidationFinding, ...] = (),
    tool_summaries: tuple[SandboxReadValidationToolResult, ...] = (),
) -> SandboxReadValidationReport:
    project_count = 1 if settings.sandbox_smoke_project_id else 0
    report = SandboxReadValidationReport(
        status=status,
        decision=decision,
        validation_attempted=validation_attempted,
        live_calls_attempted=live_calls_attempted,
        provider_mode=settings.secret_provider,
        selected_tools=_tools(settings),
        max_projects=settings.sandbox_read_validation_max_projects,
        max_items_per_tool=settings.sandbox_read_validation_max_items_per_tool,
        max_pages=settings.sandbox_read_validation_max_pages,
        timeout_seconds=settings.sandbox_read_validation_timeout_seconds,
        scope=SandboxReadValidationScope(
            company_scope_configured=bool(settings.sandbox_smoke_company_id),
            project_scope_configured=bool(settings.sandbox_smoke_project_id),
            configured_project_count=project_count,
            project_scope_hashes=(
                (hash_sandbox_identifier(settings.sandbox_smoke_project_id),)
                if settings.sandbox_smoke_project_id
                else ()
            ),
        ),
        requirements=_requirements(settings),
        findings=findings,
        tool_summaries=tool_summaries,
        evidence_ref=build_sandbox_read_evidence_ref(None, settings),
        recommended_next_steps=(
            "Keep live results and any report files private and outside Git.",
            "Record only the placeholder-shaped evidence reference for later private review.",
            "Treat permission or empty-result findings as review input, not production approval.",
        ),
        generated_at=datetime.now(UTC),
    )
    validate_sandbox_read_report_safe(report)
    return report


def build_sandbox_read_preflight(settings: Settings) -> SandboxReadValidationReport:
    unsafe = validate_sandbox_read_settings(settings)
    if unsafe:
        return _base_report(
            settings,
            status=SandboxReadValidationStatus.BLOCKED,
            decision=SandboxReadValidationDecision.VALIDATION_BLOCKED,
            findings=unsafe,
        )
    missing = any(
        item.status == SandboxReadValidationStatus.NEEDS_CONFIGURATION
        for item in _requirements(settings)
    )
    return _base_report(
        settings,
        status=(
            SandboxReadValidationStatus.NEEDS_CONFIGURATION
            if missing
            else SandboxReadValidationStatus.READY
        ),
        decision=SandboxReadValidationDecision.VALIDATION_NOT_RUN,
    )


def build_sandbox_read_validation_plan(
    settings: Settings,
) -> SandboxReadValidationReport:
    return build_sandbox_read_preflight(settings)


def _raw_id(item: Any) -> Any:
    if isinstance(item, Mapping):
        return item.get("id")
    return getattr(item, "id", None)


def classify_procore_read_error(error: Exception) -> SandboxReadValidationStatus:
    status_code = getattr(error, "status_code", None)
    safe_kind = str(error).casefold()
    if status_code == 403 or "403" in safe_kind or "permission" in safe_kind:
        return SandboxReadValidationStatus.PERMISSION_DENIED
    if status_code == 404 or "404" in safe_kind or "not found" in safe_kind:
        return SandboxReadValidationStatus.NOT_FOUND
    return SandboxReadValidationStatus.ERROR


def summarize_tool_result(
    tool: SandboxReadValidationTool,
    raw_items: Sequence[Any],
    settings: Settings,
) -> SandboxReadValidationToolResult:
    bounded = list(raw_items)[: settings.sandbox_read_validation_max_items_per_tool]
    status = (
        SandboxReadValidationStatus.EMPTY_RESULT
        if not bounded
        else SandboxReadValidationStatus.PASSED
    )
    hashes = tuple(
        hash_sandbox_identifier(identifier)
        for item in bounded
        if (identifier := _raw_id(item)) is not None
    )
    return SandboxReadValidationToolResult(
        tool=tool,
        status=status,
        list_status=status,
        detail_status=SandboxReadValidationStatus.SKIPPED,
        sanitized_item_count=len(bounded),
        identifier_hashes=hashes,
        filtering_represented=True,
        probes=(
            SandboxReadValidationProbe(
                name=f"{tool.value}_list",
                status=status,
                item_count=len(bounded),
                filtering_represented=True,
                summary=(
                    "The bounded list read returned no records; access may still be valid."
                    if not bounded
                    else "The bounded list read completed; record contents were omitted."
                ),
            ),
        ),
    )


def _run_tool(
    client: SandboxReadClient,
    tool: SandboxReadValidationTool,
    settings: Settings,
) -> SandboxReadValidationToolResult:
    list_method = getattr(client, f"list_{tool.value}")
    detail_method = getattr(client, f"get_{tool.value[:-1]}")
    items: list[Any] = []
    pages = 0
    page_size = max(
        1,
        (
            settings.sandbox_read_validation_max_items_per_tool
            + settings.sandbox_read_validation_max_pages
            - 1
        )
        // settings.sandbox_read_validation_max_pages,
    )
    try:
        for page in range(1, settings.sandbox_read_validation_max_pages + 1):
            remaining = settings.sandbox_read_validation_max_items_per_tool - len(items)
            if remaining <= 0:
                break
            requested = min(page_size, remaining)
            values = list(
                list_method(page=page, per_page=requested, updated_since=None)
            )[:requested]
            pages += 1
            items.extend(values)
            if len(values) < requested:
                break
    except Exception as exc:
        status = classify_procore_read_error(exc)
        return SandboxReadValidationToolResult(
            tool=tool,
            status=status,
            list_status=status,
            detail_status=SandboxReadValidationStatus.SKIPPED,
            pages_attempted=pages,
            probes=(
                SandboxReadValidationProbe(
                    name=f"{tool.value}_list",
                    status=status,
                    pages_attempted=pages,
                    filtering_represented=True,
                    summary="The list read failed; sensitive error details were omitted.",
                ),
            ),
        )
    result = summarize_tool_result(tool, items, settings)
    result.pages_attempted = pages
    result.probes[0].pages_attempted = pages
    if not items or not settings.sandbox_read_validation_include_details:
        return result
    identifier = _raw_id(items[0])
    if identifier is None:
        return result
    try:
        detail_method(identifier)
        result.detail_status = SandboxReadValidationStatus.PASSED
        result.probes += (
            SandboxReadValidationProbe(
                name=f"{tool.value}_detail",
                status=SandboxReadValidationStatus.PASSED,
                detail_attempted=True,
                summary="One bounded detail read completed; all record fields were omitted.",
            ),
        )
    except Exception as exc:
        status = classify_procore_read_error(exc)
        result.detail_status = status
        result.status = status
        result.probes += (
            SandboxReadValidationProbe(
                name=f"{tool.value}_detail",
                status=status,
                detail_attempted=True,
                summary="The detail read failed; sensitive error details were omitted.",
            ),
        )
    return result


def _live_blockers(settings: Settings, client: SandboxReadClient | None) -> list[str]:
    blockers = [item.message for item in validate_sandbox_read_settings(settings)]
    if not settings.sandbox_read_validation_enabled:
        blockers.append("manual enablement is disabled")
    if settings.sandbox_read_validation_confirmation != CONFIRMATION_PHRASE:
        blockers.append("the exact confirmation phrase is missing or incorrect")
    if settings.sandbox_read_validation_require_sandbox:
        if settings.procore_environment != "sandbox":
            blockers.append("the Procore environment is not sandbox")
        if not settings.procore_live_mode_enabled:
            blockers.append("the existing live-mode gate is disabled")
    if settings.sandbox_read_validation_require_allowed_scope and not (
        settings.sandbox_smoke_company_id and settings.sandbox_smoke_project_id
    ):
        blockers.append("allowed company/project scope is not configured")
    if settings.sandbox_smoke_connection_id is None:
        blockers.append("the private DMSA connection profile is not configured")
    if client is None:
        blockers.append("a guarded read-only client was not provided")
    elif not getattr(client, "credential_refs_configured", False):
        blockers.append("DMSA credential references are incomplete")
    elif not getattr(client, "sandbox_environment", False):
        blockers.append("the guarded connection is not sandbox")
    elif not getattr(client, "allowed_scope_configured", False):
        blockers.append("the guarded connection scope is incomplete")
    return blockers


def run_sandbox_read_validation(
    settings: Settings,
    procore_client: SandboxReadClient | None = None,
) -> SandboxReadValidationReport:
    blockers = _live_blockers(settings, procore_client)
    if blockers:
        raise SandboxReadValidationBlockedError(
            "Sandbox read validation blocked: " + "; ".join(blockers) + "."
        )
    assert procore_client is not None
    results = tuple(_run_tool(procore_client, tool, settings) for tool in _tools(settings))
    review_statuses = {
        SandboxReadValidationStatus.FAILED,
        SandboxReadValidationStatus.PERMISSION_DENIED,
        SandboxReadValidationStatus.NOT_FOUND,
        SandboxReadValidationStatus.ERROR,
    }
    needs_review = any(item.status in review_statuses for item in results)
    return _base_report(
        settings,
        status=(
            SandboxReadValidationStatus.NEEDS_CONFIGURATION
            if needs_review
            else SandboxReadValidationStatus.PASSED
        ),
        decision=(
            SandboxReadValidationDecision.VALIDATION_NEEDS_REVIEW
            if needs_review
            else SandboxReadValidationDecision.VALIDATION_PASSED
        ),
        validation_attempted=True,
        live_calls_attempted=True,
        tool_summaries=results,
    )


def render_sandbox_read_report_markdown(report: SandboxReadValidationReport) -> str:
    lines = [
        "# Sanitized sandbox read-validation summary",
        "",
        f"Status: **{report.status.value}**",
        f"Decision: **{report.decision.value}**",
        "",
        "This summary contains counts and one-way identifier hashes only.",
        "",
        "## Tool results",
    ]
    for result in report.tool_summaries:
        lines.append(
            f"- {result.tool.value}: {result.status.value}; "
            f"count={result.sanitized_item_count}; pages={result.pages_attempted}"
        )
    lines.extend(
        (
            "",
            "No raw payloads, identifiers, subjects, titles, descriptions, contacts, URLs, "
            "attachment filenames, secrets, or private paths are included.",
        )
    )
    return "\n".join(lines) + "\n"


def validate_sandbox_read_report_safe(report: SandboxReadValidationReport) -> None:
    if any(
        (
            report.output_policy.attachments_included,
            report.output_policy.attachment_downloads_attempted,
            report.output_policy.raw_payloads_stored,
            report.output_policy.secrets_exposed,
            report.output_policy.ids_exposed,
            report.output_policy.private_paths_exposed,
        )
    ):
        raise SandboxReadValidationError("Unsafe sandbox read output policy.")
    serialized = report.model_dump_json()
    if re.search(
        r"(?i)(?:https?://|/Users/|/home/|/private/|/tmp/|"
        r"authorization\s*:\s*bearer|client_secret\s*[:=])",
        serialized,
    ):
        raise SandboxReadValidationError("Unsafe sandbox read report content.")


def _safe_output_root(output_root: Path) -> Path:
    if output_root in {Path("."), Path(".."), Path("/")} or ".." in output_root.parts:
        raise SandboxReadValidationError("Unsafe output root.")
    if not output_root.is_absolute() and output_root.name not in SAFE_OUTPUT_NAMES:
        raise SandboxReadValidationError("Relative output root must use an ignored safe name.")
    return output_root


def write_sandbox_read_artifacts(
    report: SandboxReadValidationReport,
    output_root: Path,
) -> SandboxReadValidationArtifactResult:
    validate_sandbox_read_report_safe(report)
    root = _safe_output_root(output_root)
    root.mkdir(parents=True, exist_ok=True)
    evidence = report.evidence_ref.model_dump(mode="json")
    files = {
        "sandbox-read-report.json": report.model_dump_json(indent=2) + "\n",
        "sandbox-read-report.md": render_sandbox_read_report_markdown(report),
        "sandbox-read-evidence.json": json.dumps(evidence, indent=2) + "\n",
        "sandbox-read-evidence.md": (
            "# Private sandbox read evidence reference\n\n"
            "Record placeholder-shaped references only; keep report contents outside Git.\n"
        ),
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    return SandboxReadValidationArtifactResult(
        output_directory=root.name,
        files=ARTIFACT_NAMES,
        live_calls_attempted=report.live_calls_attempted,
    )
