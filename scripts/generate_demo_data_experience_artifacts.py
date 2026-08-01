import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.demo_data_experience import (
    build_demo_data_experience_report,
    write_demo_data_experience_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-demo-data-", dir="/tmp"
    ) as directory:
        result = write_demo_data_experience_artifacts(
            build_demo_data_experience_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_demo_data_experience_artifacts(
        build_demo_data_experience_report(settings),
        args.output_root or settings.demo_data_output_root,
    )
    print(result.model_dump_json(indent=2))
