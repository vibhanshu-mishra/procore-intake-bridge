#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.evidence_review import EvidenceReviewManifest
from app.services.evidence_review import (
    EvidenceReviewBlockedError,
    write_evidence_review_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized local evidence review metadata artifacts."
    )
    parser.add_argument("manifest")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        manifest = EvidenceReviewManifest.model_validate_json(
            Path(args.manifest).read_text()
        )
        result = write_evidence_review_artifacts(
            manifest,
            args.output_root or settings.evidence_review_output_root,
            settings,
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Evidence review generation blocked: manifest is unreadable or invalid.")
        return 2
    except EvidenceReviewBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
