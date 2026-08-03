import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.versioned_release_handoff import (
    build_versioned_release_handoff_report,
    write_versioned_release_handoff_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-versioned-release-handoff-", dir="/tmp"
    ) as directory:
        result = write_versioned_release_handoff_artifacts(
            build_versioned_release_handoff_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_versioned_release_handoff_artifacts(
        build_versioned_release_handoff_report(settings),
        args.output_root or settings.versioned_release_handoff_output_root,
    )
    print(result.model_dump_json(indent=2))
