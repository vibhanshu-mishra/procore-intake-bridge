import argparse
import tempfile
from pathlib import Path

from app.services.setup_experience import (
    build_setup_experience_report,
    write_setup_experience_artifacts,
)

from app.config import get_settings

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-setup-experience-", dir="/tmp"
    ) as directory:
        result = write_setup_experience_artifacts(
            build_setup_experience_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_setup_experience_artifacts(
        build_setup_experience_report(settings),
        args.output_root or settings.setup_experience_output_root,
    )
    print(result.model_dump_json(indent=2))
