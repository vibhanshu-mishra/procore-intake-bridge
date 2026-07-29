#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.webhook_verification import WebhookDocsVerificationRecord
from app.services.webhook_verification import validate_webhook_docs_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a local webhook docs record offline.")
    parser.add_argument(
        "record",
        nargs="?",
        default="examples/webhook-verification/example_docs_record.json",
    )
    args = parser.parse_args()
    try:
        record = WebhookDocsVerificationRecord.model_validate_json(
            Path(args.record).read_text()
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Webhook docs record invalid: unreadable or malformed local JSON.")
        return 2
    findings = validate_webhook_docs_record(record, get_settings())
    print(json.dumps({
        "status": record.status,
        "ready": record.status == "verified" and not any(f.severity == "error" for f in findings),
        "findings": [f.model_dump() for f in findings],
    }, indent=2))
    return 0 if record.status in {"unverified", "needs_review"} else int(
        any(f.severity == "error" for f in findings)
    )


if __name__ == "__main__":
    raise SystemExit(main())
