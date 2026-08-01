import argparse
import tempfile
from pathlib import Path

from app.services.security_gap_closeout import (
    build_security_gap_closeout_report,
    write_security_gap_closeout_artifacts,
)

from app.config import get_settings

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-security-gap-closeout-", dir="/tmp"
    ) as directory:
        result = write_security_gap_closeout_artifacts(
            build_security_gap_closeout_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_security_gap_closeout_artifacts(
        build_security_gap_closeout_report(settings),
        args.output_root or settings.security_gap_closeout_output_root,
    )
    print(result.model_dump_json(indent=2))
