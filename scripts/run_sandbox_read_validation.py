#!/usr/bin/env python3
"""Manually run the separately gated, read-only Procore Sandbox validation."""

import argparse

from app.config import get_settings
from app.database import SessionLocal, create_db_and_tables
from app.models.connections import DMSAConnection, ProcoreEnvironment
from app.services.procore_client import build_pyprocore_client_for_connection
from app.services.sandbox_read_validation import (
    CONFIRMATION_PHRASE,
    PyProcoreSandboxReadClient,
    SandboxReadValidationBlockedError,
    SandboxReadValidationError,
    render_sandbox_read_report_markdown,
    run_sandbox_read_validation,
    write_sandbox_read_artifacts,
)


def _early_refusal(settings) -> str | None:
    if not settings.sandbox_read_validation_enabled:
        return "manual enablement is disabled"
    if settings.sandbox_read_validation_confirmation != CONFIRMATION_PHRASE:
        return "the exact read-only Sandbox confirmation phrase is missing or incorrect"
    if not settings.procore_live_mode_enabled:
        return "the existing live-mode gate is disabled"
    if settings.procore_environment != "sandbox":
        return "the Procore environment is not sandbox"
    if settings.sandbox_smoke_connection_id is None:
        return "the private DMSA connection profile is not configured"
    if not settings.sandbox_smoke_company_id or not settings.sandbox_smoke_project_id:
        return "the private allowed company/project scope is not configured"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run manually gated bounded read validation; never performs writes."
    )
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="Write sanitized files under the configured ignored output root.",
    )
    args = parser.parse_args()
    settings = get_settings()
    refusal = _early_refusal(settings)
    if refusal:
        print(
            f"Sandbox read validation blocked: {refusal}. No live call was attempted. "
            "This command is never run by quality or default workflows."
        )
        return 2

    create_db_and_tables()
    try:
        with SessionLocal() as session:
            connection = session.get(
                DMSAConnection, settings.sandbox_smoke_connection_id
            )
            if connection is None:
                raise SandboxReadValidationBlockedError(
                    "Sandbox read validation blocked: the local connection was not found."
                )
            if connection.environment != ProcoreEnvironment.SANDBOX:
                raise SandboxReadValidationBlockedError(
                    "Sandbox read validation blocked: the connection is not sandbox."
                )
            if not connection.client_id_ref or not connection.secret_name:
                raise SandboxReadValidationBlockedError(
                    "Sandbox read validation blocked: credential references are incomplete."
                )
            company_id = settings.sandbox_smoke_company_id
            project_id = settings.sandbox_smoke_project_id
            if company_id != connection.procore_company_id:
                raise SandboxReadValidationBlockedError(
                    "Sandbox read validation blocked: company scope does not match."
                )
            if project_id not in connection.permitted_project_ids:
                raise SandboxReadValidationBlockedError(
                    "Sandbox read validation blocked: project scope is not allowlisted."
                )
            raw_client = build_pyprocore_client_for_connection(connection, settings=settings)
            read_client = PyProcoreSandboxReadClient(raw_client, company_id, project_id)
            report = run_sandbox_read_validation(settings, read_client)
    except SandboxReadValidationBlockedError as exc:
        print(str(exc))
        return 2
    except Exception:
        print(
            "Sandbox read validation failed safely; sensitive error details were omitted. "
            "No report contents were written."
        )
        return 1

    print(render_sandbox_read_report_markdown(report))
    if args.write_artifacts:
        try:
            result = write_sandbox_read_artifacts(
                report, settings.sandbox_read_validation_output_root
            )
        except SandboxReadValidationError:
            print("Sanitized artifact writing was blocked by the output safety policy.")
            return 1
        print(
            f"Sanitized private artifacts written under ignored label: "
            f"{result.output_directory}"
        )
    return 0 if report.decision.value == "validation_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
