#!/usr/bin/env python3
import json

from app.services.evidence_review import build_fake_evidence_review_template


def main() -> int:
    template = build_fake_evidence_review_template()
    print(json.dumps(template.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
