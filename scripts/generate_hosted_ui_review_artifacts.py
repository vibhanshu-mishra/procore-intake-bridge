import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.hosted_ui_review import (
    build_hosted_ui_review_report,
    write_hosted_ui_review_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-hosted-ui-", dir="/tmp"
    ) as directory:
        result = write_hosted_ui_review_artifacts(
            build_hosted_ui_review_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_hosted_ui_review_artifacts(
        build_hosted_ui_review_report(settings),
        args.output_root or settings.hosted_ui_output_root,
    )
    print(result.model_dump_json(indent=2))
