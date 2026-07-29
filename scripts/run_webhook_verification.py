#!/usr/bin/env python3
import argparse
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.webhook_verification import WebhookDocsVerificationRecord
from app.services.webhook_verification import (
    WebhookVerificationBlockedError,
    build_webhook_verification_report,
    validate_webhook_verification_gates,
    write_webhook_verification_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run gated synthetic local webhook verification without network calls."
    )
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--docs-record", required=True)
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    try:
        record = WebhookDocsVerificationRecord.model_validate_json(
            Path(args.docs_record).read_text()
        )
        validate_webhook_verification_gates(settings, args.confirm, record)
    except (OSError, ValidationError):
        print("Webhook verification blocked: local docs record is unreadable or invalid.")
        return 2
    except WebhookVerificationBlockedError as exc:
        print(str(exc))
        return 2
    report = build_webhook_verification_report(settings, record)
    print(report.model_dump_json(indent=2))
    if settings.webhook_verification_write_report and not args.no_write_report:
        path = write_webhook_verification_report(
            report, settings.webhook_verification_output_root
        )
        print(f"Sanitized report written: {path.name}")
    return int(report.overall_status != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
