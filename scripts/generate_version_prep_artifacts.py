import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.version_prep import build_version_prep_report, write_version_prep_artifacts

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-version-prep-", dir="/tmp"
    ) as directory:
        result = write_version_prep_artifacts(build_version_prep_report(settings), Path(directory))
        print(result.model_dump_json(indent=2))
else:
    result = write_version_prep_artifacts(
        build_version_prep_report(settings),
        args.output_root or settings.version_prep_output_root,
    )
    print(result.model_dump_json(indent=2))
