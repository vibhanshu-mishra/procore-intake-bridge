#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.pilot_approval import PilotApprovalPacket
from app.services.pilot_approval import (
    PilotApprovalBlockedError,
    write_pilot_approval_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized local pilot approval packet artifacts."
    )
    parser.add_argument("packet")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    try:
        packet = PilotApprovalPacket.model_validate_json(Path(args.packet).read_text())
        result = write_pilot_approval_artifacts(
            packet,
            args.output_root or settings.pilot_approval_packet_output_root,
            settings,
        )
    except (OSError, ValidationError, json.JSONDecodeError):
        print("Pilot approval generation blocked: packet is unreadable or invalid.")
        return 2
    except PilotApprovalBlockedError as exc:
        print(str(exc))
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
