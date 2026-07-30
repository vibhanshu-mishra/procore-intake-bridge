#!/usr/bin/env python3
"""Print a placeholder-only private Sandbox read evidence reference."""

import json

from app.config import get_settings
from app.services.sandbox_read_validation import build_sandbox_read_evidence_ref


def main() -> int:
    template = build_sandbox_read_evidence_ref(None, get_settings())
    print(json.dumps(template.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
