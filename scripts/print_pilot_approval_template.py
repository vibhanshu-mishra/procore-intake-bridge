#!/usr/bin/env python3
import json

from app.services.pilot_approval import build_fake_pilot_approval_template


def main() -> int:
    packet = build_fake_pilot_approval_template()
    print(json.dumps(packet.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
