import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.private_workspace import (
    PrivateWorkspaceArtifactResult,
    PrivateWorkspaceFileSpec,
    PrivateWorkspaceFinding,
    PrivateWorkspaceManifest,
    PrivateWorkspaceMode,
    PrivateWorkspaceSection,
    PrivateWorkspaceValidationReport,
)

PLACEHOLDER_MARKERS = ("placeholder", "example", "fake", "replace_me", "not_configured")
NUMERIC_ID = re.compile(r"(?<!\w)\d{6,}(?!\w)")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w)")
DOMAIN = re.compile(r"(?i)(?<![\w.-])(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|gov|edu)(?![\w.-])")
IDENTITY = re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b")
SECRET = re.compile(
    r"(?i)(authorization\s*:|bearer\s+|(?:token|secret|password|app_version_key)"
    r"\s*[:=]\s*[^\s\"']+)"
)
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\s\"'])(?:/Users/|/home/|/private/|/tmp/|/var/|[A-Z]:\\)")
ENV_VALUE = re.compile(r"\b[A-Z][A-Z0-9_]*=([^\s\"\\]+)")
DATABASE_URL = re.compile(r"(?i)\b(?:sqlite|postgres(?:ql)?|mysql|mariadb|mongodb)://")
STORAGE_URL = re.compile(r"(?i)\b(?:s3|gs|azure|az|https?)://")
RAW_CONTENT = re.compile(
    r"(?i)(raw\s+(?:payload|support bundle|smoke report|webhook report|evidence)"
    r"(?:\s+contents?)?|\"raw_payload\"\s*:)"
)
BINARY_REF = re.compile(r"(?i)\.(?:db|sqlite3?|pdf|docx|xlsx?|png|jpe?g|gif|webp|zip)(?:\b|$)")
SAFE_TEXT_SUFFIXES = {".md", ".json", ".env"}


class PrivateWorkspaceError(RuntimeError):
    """A sanitized private-workspace operation failed."""


class PrivateWorkspaceBlockedError(PrivateWorkspaceError):
    """A fail-closed private-workspace safety gate blocked execution."""


def _placeholder(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def sanitize_workspace_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): sanitize_workspace_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_workspace_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if SECRET.search(value):
            return "[redacted]"
        if ABSOLUTE_PATH.search(value) or Path(value).is_absolute():
            return "[redacted-path]"
        if SIGNED_URL.search(value):
            return "[redacted-url]"
    return value


def _spec(
    path: str,
    section: PrivateWorkspaceSection,
    purpose: str,
    modes: list[PrivateWorkspaceMode],
) -> PrivateWorkspaceFileSpec:
    suffix = Path(path).suffix
    kind = "json" if suffix == ".json" else "env" if suffix == ".env" else "markdown"
    return PrivateWorkspaceFileSpec(
        relative_path=path,
        section=section,
        purpose=purpose,
        required_for_modes=modes,
        template_kind=kind,
        notes=["Placeholder scaffold only; replace values privately and never commit."],
    )


def build_private_workspace_manifest(
    mode: PrivateWorkspaceMode | str, settings: Settings
) -> PrivateWorkspaceManifest:
    if not settings.private_workspace_enabled:
        raise PrivateWorkspaceBlockedError("Private workspace bootstrap is disabled.")
    try:
        selected = PrivateWorkspaceMode(mode)
    except ValueError as exc:
        raise PrivateWorkspaceBlockedError("Unsupported private workspace mode.") from exc
    both = [
        PrivateWorkspaceMode.SANDBOX,
        PrivateWorkspaceMode.PILOT,
        PrivateWorkspaceMode.SANDBOX_AND_PILOT,
    ]
    sandbox = [PrivateWorkspaceMode.SANDBOX, PrivateWorkspaceMode.SANDBOX_AND_PILOT]
    pilot = [PrivateWorkspaceMode.PILOT, PrivateWorkspaceMode.SANDBOX_AND_PILOT]
    specs = [
        _spec(
            "README.private.md",
            PrivateWorkspaceSection.README,
            "Private workspace boundaries.",
            both,
        ),
        _spec(
            "environment/env.refs.private.env",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Environment reference names only.",
            both,
        ),
        _spec(
            "environment/secrets-map.private.json",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Secret reference mapping without values.",
            both,
        ),
        _spec(
            "environment/secrets/README.private.md",
            PrivateWorkspaceSection.ENVIRONMENT,
            "File-provider secret directory instructions and safe relative refs.",
            both,
        ),
        _spec(
            "storage/README.private.md",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Private storage boundaries and no-public-serving guidance.",
            both,
        ),
        _spec(
            "storage/storage-map.private.json",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Storage provider and root reference placeholders only.",
            both,
        ),
        _spec(
            "storage/local-storage-root.private.md",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Local ignored storage root reference.",
            both,
        ),
        _spec(
            "storage/object-refs.private.json",
            PrivateWorkspaceSection.ENVIRONMENT,
            "Masked attachment object reference placeholders.",
            both,
        ),
        _spec("database/README.private.md", PrivateWorkspaceSection.DATABASE,
              "Private database boundaries and no-connect defaults.", both),
        _spec("database/database-refs.private.env", PrivateWorkspaceSection.DATABASE,
              "Database secret references without URL values.", both),
        _spec("database/postgres-plan.private.md", PrivateWorkspaceSection.DATABASE,
              "PostgreSQL SSL and version posture placeholders.", both),
        _spec("database/migration-execution-plan.private.md",
              PrivateWorkspaceSection.DATABASE,
              "Reviewed migration execution plan reference.", both),
        _spec("database/backup-plan.private.md", PrivateWorkspaceSection.DATABASE,
              "Private backup plan reference.", pilot),
        _spec("database/restore-plan.private.md", PrivateWorkspaceSection.DATABASE,
              "Private restore plan reference.", pilot),
        _spec("database/rollback-plan.private.md", PrivateWorkspaceSection.DATABASE,
              "Private rollback plan reference.", pilot),
        _spec("deployment/README.private.md", PrivateWorkspaceSection.DEPLOYMENT,
              "Private deployment recipe boundaries.", both),
        _spec("deployment/deployment-recipe.private.json",
              PrivateWorkspaceSection.DEPLOYMENT,
              "Deployment recipe placeholder references.", both),
        _spec("deployment/https-tls.private.md", PrivateWorkspaceSection.DEPLOYMENT,
              "HTTPS and certificate reference checklist.", both),
        _spec("deployment/webhook-ingress.private.md",
              PrivateWorkspaceSection.DEPLOYMENT,
              "Webhook ingress reference checklist.", both),
        _spec("deployment/cutover-checklist.private.md",
              PrivateWorkspaceSection.DEPLOYMENT, "Private cutover checklist.", pilot),
        _spec("deployment/backup-runbook.private.md",
              PrivateWorkspaceSection.DEPLOYMENT,
              "Private backup runbook reference.", pilot),
        _spec("deployment/rollback-runbook.private.md",
              PrivateWorkspaceSection.DEPLOYMENT,
              "Private rollback runbook reference.", pilot),
        _spec("deployment/operator-runbook.private.md",
              PrivateWorkspaceSection.DEPLOYMENT,
              "Private operator runbook reference.", pilot),
        _spec(
            "sandbox/sandbox-scope.private.json",
            PrivateWorkspaceSection.SANDBOX,
            "Allowed sandbox scope placeholders.",
            sandbox,
        ),
        _spec(
            "sandbox/sandbox-smoke-ref.private.md",
            PrivateWorkspaceSection.SANDBOX,
            "Manual smoke report reference.",
            sandbox,
        ),
        _spec(
            "dmsa/dmsa-setup-notes.private.md",
            PrivateWorkspaceSection.DMSA,
            "DMSA setup notes and reference placeholders.",
            sandbox,
        ),
        _spec(
            "permissions/gc-owner-permissions.private.md",
            PrivateWorkspaceSection.PERMISSIONS,
            "GC/Owner permission checklist.",
            both,
        ),
        _spec(
            "webhooks/webhook-docs-review.private.md",
            PrivateWorkspaceSection.WEBHOOKS,
            "Webhook documentation review notes.",
            both,
        ),
        _spec(
            "diagnostics/support-diagnostics-ref.private.md",
            PrivateWorkspaceSection.DIAGNOSTICS,
            "Sanitized diagnostics reference.",
            both,
        ),
        _spec(
            "customer-profile/customer-profile.private.json",
            PrivateWorkspaceSection.CUSTOMER_PROFILE,
            "Customer deployment placeholders.",
            pilot,
        ),
        _spec(
            "evidence/evidence-manifest.private.json",
            PrivateWorkspaceSection.EVIDENCE,
            "Evidence metadata references only.",
            pilot,
        ),
        _spec(
            "evidence-review/evidence-review.private.json",
            PrivateWorkspaceSection.EVIDENCE_REVIEW,
            "Review and expiry placeholders.",
            pilot,
        ),
        _spec(
            "pilot-readiness/pilot-readiness.private.json",
            PrivateWorkspaceSection.PILOT_READINESS,
            "Pilot readiness reference placeholders.",
            pilot,
        ),
        _spec(
            "pilot-approval/pilot-approval.private.json",
            PrivateWorkspaceSection.PILOT_APPROVAL,
            "Approval packet placeholders only.",
            pilot,
        ),
        _spec(
            "launch/launch-checklist.private.md",
            PrivateWorkspaceSection.LAUNCH,
            "Private launch checklist.",
            pilot,
        ),
        _spec(
            "rollback/rollback-checklist.private.md",
            PrivateWorkspaceSection.ROLLBACK,
            "Rollback and backup checklist.",
            pilot,
        ),
        _spec(
            "incident-response/incident-response.private.md",
            PrivateWorkspaceSection.INCIDENT_RESPONSE,
            "Incident response placeholders.",
            pilot,
        ),
    ]
    applicable = [spec for spec in specs if selected in spec.required_for_modes]
    return PrivateWorkspaceManifest(
        mode=selected,
        files=applicable,
        notes=[
            "Fake placeholder metadata only.",
            "Real workspace data remains ignored, local, and private.",
        ],
    )


def validate_private_workspace_path(path: Path, root: Path) -> Path:
    if root in {Path("."), Path("/")} or ".." in root.parts:
        raise PrivateWorkspaceBlockedError("Private workspace root is unsafe.")
    if not root.is_absolute() and root.parts[0] not in {
        "private-workspace",
        ".local-workspace",
        "sandbox-workspace",
        "pilot-workspace",
    }:
        raise PrivateWorkspaceBlockedError("Use a dedicated private workspace root.")
    resolved_root = root.resolve()
    resolved = (resolved_root / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise PrivateWorkspaceBlockedError("Private workspace path escaped its root.")
    return resolved


def _unsafe_codes(value: str, settings: Settings) -> set[str]:
    codes: set[str] = set()
    if NUMERIC_ID.search(value) and not settings.private_workspace_allow_real_ids:
        codes.add("real_id")
    if EMAIL.search(value):
        codes.add("email")
    if PHONE.search(value):
        codes.add("phone")
    if DOMAIN.search(value) and not _placeholder(value):
        codes.add("domain")
    if (
        IDENTITY.search(value)
        and not _placeholder(value)
        and not settings.private_workspace_allow_real_identities
    ):
        codes.add("identity")
    if SECRET.search(value):
        codes.add("secret")
    if SIGNED_URL.search(value):
        codes.add("signed_url")
    if (
        ABSOLUTE_PATH.search(value)
        and not settings.private_workspace_allow_absolute_paths
    ):
        codes.add("absolute_path")
    for match in ENV_VALUE.finditer(value):
        if not _placeholder(match.group(1)):
            codes.add("env_assignment")
    if DATABASE_URL.search(value):
        codes.add("database_url")
    if STORAGE_URL.search(value) and not _placeholder(value):
        codes.add("storage_url")
    if RAW_CONTENT.search(value) and not settings.private_workspace_allow_file_contents:
        codes.add("raw_content")
    if BINARY_REF.search(value):
        codes.add("binary_reference")
    return codes


def validate_private_workspace_manifest(
    manifest: PrivateWorkspaceManifest, settings: Settings
) -> list[PrivateWorkspaceFinding]:
    findings: list[PrivateWorkspaceFinding] = []
    if len(manifest.files) > settings.private_workspace_max_files:
        findings.append(
            PrivateWorkspaceFinding(
                code="max_files",
                severity="blocking",
                message="Workspace exceeds the configured file limit.",
            )
        )
    seen: set[str] = set()
    for spec in manifest.files:
        relative = Path(spec.relative_path)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            findings.append(
                PrivateWorkspaceFinding(
                    code="unsafe_path",
                    severity="blocking",
                    message="A workspace file path is unsafe.",
                )
            )
            continue
        if spec.relative_path in seen:
            findings.append(
                PrivateWorkspaceFinding(
                    code="duplicate_path",
                    severity="blocking",
                    message="A workspace file path is duplicated.",
                )
            )
        seen.add(spec.relative_path)
        unsafe_contents = (
            spec.contains_file_contents
            and not settings.private_workspace_allow_file_contents
        )
        missing_placeholders = (
            settings.private_workspace_require_placeholders and not spec.placeholder_only
        )
        if unsafe_contents or spec.contains_secret_values or missing_placeholders:
            findings.append(
                PrivateWorkspaceFinding(
                    code="unsafe_file_spec",
                    severity="blocking",
                    message="Workspace specs must remain placeholder-only.",
                )
            )
    unsafe = set()
    for value in _strings(manifest.model_dump(mode="json")):
        unsafe.update(_unsafe_codes(value, settings))
    for code in sorted(unsafe):
        findings.append(
            PrivateWorkspaceFinding(
                code=code,
                severity="blocking",
                message=f"Unsafe {code.replace('_', ' ')} pattern detected.",
            )
        )
    if not findings:
        findings.append(
            PrivateWorkspaceFinding(
                code="safe_manifest",
                severity="info",
                message="Manifest contains placeholder metadata only.",
            )
        )
    return findings


def build_private_workspace_validation_report(
    manifest: PrivateWorkspaceManifest, settings: Settings
) -> PrivateWorkspaceValidationReport:
    findings = validate_private_workspace_manifest(manifest, settings)
    blocking = sum(item.severity == "blocking" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    return PrivateWorkspaceValidationReport(
        generated_at=datetime.now(UTC),
        workspace_name=manifest.workspace_name,
        mode=manifest.mode,
        valid=blocking == 0,
        blocking_findings_count=blocking,
        warning_findings_count=warnings,
        file_count=len(manifest.files),
        findings=findings,
    )


def render_private_workspace_file(
    spec: PrivateWorkspaceFileSpec, manifest: PrivateWorkspaceManifest
) -> str:
    if spec.relative_path == "deployment/deployment-recipe.private.json":
        return json.dumps({
            "public_base_url": "PUBLIC_BASE_URL_PLACEHOLDER",
            "allowed_host": "ALLOWED_HOST_PLACEHOLDER",
            "database_url_ref": "DATABASE_URL_REF_PLACEHOLDER",
            "secret_provider_ref": "SECRET_PROVIDER_REF_PLACEHOLDER",
            "storage_provider_ref": "STORAGE_PROVIDER_REF_PLACEHOLDER",
            "tls_cert_ref": "TLS_CERT_REF_PLACEHOLDER",
            "webhook_ingress_ref": "WEBHOOK_INGRESS_REF_PLACEHOLDER",
            "external_provisioning": False,
        }, indent=2) + "\n"
    if spec.relative_path.startswith("deployment/") and spec.template_kind == "markdown":
        return (
            f"# {spec.purpose}\n\n"
            "- `PUBLIC_BASE_URL_PLACEHOLDER`\n"
            "- `TLS_CERT_REF_PLACEHOLDER`\n"
            "- `WEBHOOK_INGRESS_REF_PLACEHOLDER`\n"
            "- `BACKUP_PLAN_REF_PLACEHOLDER`\n"
            "- `ROLLBACK_PLAN_REF_PLACEHOLDER`\n"
            "- No deployment, DNS, certificate, webhook, or cloud operation is performed.\n"
        )
    if spec.relative_path == "database/database-refs.private.env":
        return (
            "DATABASE_URL_REF=ENV_REF_PLACEHOLDER_DATABASE_URL\n"
            "POSTGRES_SSL_MODE=POSTGRES_SSL_MODE_PLACEHOLDER\n"
            "BACKUP_PLAN_REF=BACKUP_PLAN_REF_PLACEHOLDER\n"
            "RESTORE_PLAN_REF=RESTORE_PLAN_REF_PLACEHOLDER\n"
            "MIGRATION_PLAN_REF=MIGRATION_PLAN_REF_PLACEHOLDER\n"
        )
    if spec.relative_path.startswith("database/") and spec.template_kind == "markdown":
        return (
            f"# {spec.purpose}\n\n"
            "- DATABASE_URL_REF: `ENV_REF_PLACEHOLDER_DATABASE_URL`\n"
            "- SSL posture: `POSTGRES_SSL_MODE_PLACEHOLDER`\n"
            "- Migration: `MIGRATION_PLAN_REF_PLACEHOLDER`\n"
            "- Backup: `BACKUP_PLAN_REF_PLACEHOLDER`\n"
            "- Restore: `RESTORE_PLAN_REF_PLACEHOLDER`\n"
            "- No database URL, hostname, credentials, dump, or contents are included.\n"
        )
    if spec.template_kind == "json":
        if spec.relative_path == "storage/storage-map.private.json":
            return (
                json.dumps(
                    {
                        "storage_provider_ref": "LOCAL_STORAGE_REF_PLACEHOLDER",
                        "attachment_storage_root_ref": (
                            "LOCAL_STORAGE_ROOT_REF_PLACEHOLDER"
                        ),
                        "bucket_or_endpoint_included": False,
                        "object_contents_included": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        if spec.relative_path == "storage/object-refs.private.json":
            return (
                json.dumps(
                    {
                        "attachment_manifest_ref": (
                            "OBJECT_REF_PLACEHOLDER_ATTACHMENT_MANIFEST"
                        ),
                        "raw_object_key_included": False,
                        "object_contents_included": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        if spec.relative_path == "environment/secrets-map.private.json":
            return (
                json.dumps(
                    {
                        "provider": "ENV_OR_FILE_PROVIDER_PLACEHOLDER",
                        "refs": {
                            "client_id_ref": "dmsa/client_id.secret",
                            "client_secret_ref": "dmsa/client_secret.secret",
                            "admin_token_ref": "admin/admin_token.secret",
                            "webhook_secret_ref": "webhooks/procore_signature.secret",
                        },
                        "secret_values_included": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        return (
            json.dumps(
                {
                    "section": spec.section.value,
                    "purpose": spec.purpose,
                    "status": "NOT_CONFIGURED_PLACEHOLDER",
                    "reference_placeholder": f"{spec.section.value.upper()}_REF_PLACEHOLDER",
                    "values_included": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    if spec.template_kind == "env":
        return (
            "# Reference names only. Never place secret values in this file.\n"
            "PROCORE_CLIENT_ID_REF=ENV_REF_PLACEHOLDER_PROCORE_CLIENT_ID\n"
            "PROCORE_CLIENT_SECRET_REF=ENV_REF_PLACEHOLDER_PROCORE_CLIENT_SECRET\n"
            "ADMIN_TOKEN_REF=ENV_REF_PLACEHOLDER_ADMIN_TOKEN\n"
            "WEBHOOK_SECRET_REF=ENV_REF_PLACEHOLDER_WEBHOOK_SECRET\n"
        )
    return (
        f"# {spec.section.value.replace('_', ' ').title()}\n\n"
        f"{spec.purpose}\n\n"
        "- [ ] PLACEHOLDER: complete this item in the ignored private workspace.\n"
        "- Values, evidence contents, identities, and absolute paths are excluded.\n"
    )


def render_private_workspace_readme(
    manifest: PrivateWorkspaceManifest, report: PrivateWorkspaceValidationReport
) -> str:
    return (
        "# Private workspace\n\n"
        f"Mode: `{manifest.mode.value}`\n\n"
        "This ignored local scaffold contains placeholders only. Keep all real customer data, "
        "credentials, IDs, evidence, identities, reports, and approvals outside public GitHub.\n\n"
        f"Template validation: `{'valid' if report.valid else 'blocked'}`.\n"
    )


def render_private_workspace_checklist(
    manifest: PrivateWorkspaceManifest, report: PrivateWorkspaceValidationReport
) -> str:
    lines = ["# Private workspace checklist", ""]
    lines.extend(f"- [ ] Review `{spec.relative_path}` privately." for spec in manifest.files)
    lines.extend(["", f"Manifest blockers: {report.blocking_findings_count}.", ""])
    return "\n".join(lines)


def write_private_workspace(
    mode: PrivateWorkspaceMode | str, output_root: Path, overwrite: bool = False
) -> PrivateWorkspaceArtifactResult:
    settings = Settings()
    manifest = build_private_workspace_manifest(mode, settings)
    report = build_private_workspace_validation_report(manifest, settings)
    if settings.private_workspace_fail_closed and not report.valid:
        raise PrivateWorkspaceBlockedError("Private workspace manifest failed safety validation.")
    root = validate_private_workspace_path(Path("."), Path(output_root))
    planned = [*manifest.files]
    manifest_path = root / "workspace-manifest.json"
    checklist_path = root / "workspace-checklist.private.md"
    destinations = [
        validate_private_workspace_path(Path(spec.relative_path), root) for spec in planned
    ]
    all_destinations = [*destinations, manifest_path, checklist_path]
    if not overwrite and any(path.exists() for path in all_destinations):
        raise PrivateWorkspaceBlockedError(
            "Private workspace file already exists; overwrite was not enabled."
        )
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for spec, destination in zip(planned, destinations, strict=True):
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = (
            render_private_workspace_readme(manifest, report)
            if spec.section == PrivateWorkspaceSection.README
            else render_private_workspace_file(spec, manifest)
        )
        if _unsafe_codes(content, settings):
            raise PrivateWorkspaceBlockedError(
                "Generated workspace content failed safety validation."
            )
        destination.write_text(content, encoding="utf-8")
        written.append(spec.relative_path)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    checklist_path.write_text(
        render_private_workspace_checklist(manifest, report), encoding="utf-8"
    )
    written.extend(["workspace-manifest.json", "workspace-checklist.private.md"])
    return PrivateWorkspaceArtifactResult(
        mode=manifest.mode,
        output_directory=Path(output_root).name,
        files=written,
        overwritten=overwrite,
    )


def validate_existing_private_workspace(
    output_root: Path, settings: Settings
) -> PrivateWorkspaceValidationReport:
    target = Path(output_root)
    if target.is_file():
        try:
            manifest = PrivateWorkspaceManifest.model_validate_json(target.read_text())
        except (OSError, ValueError) as exc:
            raise PrivateWorkspaceBlockedError(
                "Workspace manifest is unreadable or invalid."
            ) from exc
        return build_private_workspace_validation_report(manifest, settings)
    root = validate_private_workspace_path(Path("."), target)
    manifest_path = validate_private_workspace_path(Path("workspace-manifest.json"), root)
    try:
        manifest = PrivateWorkspaceManifest.model_validate_json(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise PrivateWorkspaceBlockedError("Workspace manifest is unreadable or invalid.") from exc
    findings = validate_private_workspace_manifest(manifest, settings)
    files = [path for path in root.rglob("*") if path.is_file()]
    if len(files) > settings.private_workspace_max_files:
        findings.append(
            PrivateWorkspaceFinding(
                code="max_files",
                severity="blocking",
                message="Workspace exceeds the configured file limit.",
            )
        )
    for path in files:
        validate_private_workspace_path(path, root)
        if path.suffix.casefold() not in SAFE_TEXT_SUFFIXES:
            findings.append(
                PrivateWorkspaceFinding(
                    code="binary_reference",
                    severity="blocking",
                    message="Unsupported or binary workspace file detected.",
                )
            )
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(
                PrivateWorkspaceFinding(
                    code="unreadable_file",
                    severity="blocking",
                    message="Workspace text file could not be read.",
                )
            )
            continue
        for code in sorted(_unsafe_codes(content, settings)):
            findings.append(
                PrivateWorkspaceFinding(
                    code=code,
                    severity="blocking",
                    message=f"Unsafe {code.replace('_', ' ')} pattern detected.",
                )
            )
    blocking = sum(item.severity == "blocking" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    return PrivateWorkspaceValidationReport(
        generated_at=datetime.now(UTC),
        workspace_name=manifest.workspace_name,
        mode=manifest.mode,
        valid=blocking == 0,
        blocking_findings_count=blocking,
        warning_findings_count=warnings,
        file_count=len(files),
        findings=findings,
    )
