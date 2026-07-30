#!/usr/bin/env python3
"""Generate ignored HTTPS/webhook planning artifacts; perform no live operation."""

import argparse
import tempfile
from pathlib import Path

from app.schemas.https_webhook_planning import HttpsWebhookPlanningProfile
from app.services.https_webhook_planning import write_https_webhook_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=Path("https-webhook-output")
    )
    parser.add_argument("--temporary", action="store_true")
    args = parser.parse_args()
    try:
        profile = HttpsWebhookPlanningProfile.model_validate_json(
            args.profile.read_text(encoding="utf-8")
        )
        if args.temporary:
            with tempfile.TemporaryDirectory(
                prefix="procore-intake-bridge-https-webhook-",
                dir="/tmp",
            ) as directory:
                result = write_https_webhook_artifacts(profile, Path(directory))
                print(result.model_dump_json(indent=2))
        else:
            result = write_https_webhook_artifacts(profile, args.output_root)
            print(result.model_dump_json(indent=2))
    except Exception:
        print("HTTPS/webhook artifact generation blocked; details were suppressed.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
