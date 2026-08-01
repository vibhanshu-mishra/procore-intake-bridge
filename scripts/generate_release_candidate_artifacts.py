import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.release_candidate_review import (
    build_release_candidate_report,
    write_release_candidate_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-release-candidate-", dir="/tmp"
    ) as directory:
        result = write_release_candidate_artifacts(
            build_release_candidate_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_release_candidate_artifacts(
        build_release_candidate_report(settings),
        args.output_root or settings.release_candidate_output_root,
    )
    print(result.model_dump_json(indent=2))
