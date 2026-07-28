#!/usr/bin/env python3
import argparse
import json

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import make_engine
from app.services.attachment_storage_factory import build_attachment_storage_provider
from app.services.attachment_storage_inventory import check_manifest_storage_consistency
from app.services.attachment_storage_provider import AttachmentStorageProviderError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check attachment manifests without downloads or external calls."
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    settings = get_settings()
    engine = make_engine(settings.database_url)
    if not inspect(engine).has_table("attachment_objects"):
        result = {
            "consistent": True,
            "summary": {"total": 0, "missing_objects": 0},
            "findings": [],
        }
    else:
        try:
            provider = build_attachment_storage_provider(settings)
            with Session(engine) as session:
                result = check_manifest_storage_consistency(
                    session, provider, max(1, args.limit), settings
                )
        except (AttachmentStorageProviderError, ValueError):
            result = {
                "consistent": False,
                "summary": {"total": None, "missing_objects": None},
                "findings": [{"finding": "storage_provider_unavailable"}],
            }
    result.update(
        {"external_calls": False, "contents_inspected": False, "paths_exposed": False}
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.strict and not result["consistent"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
