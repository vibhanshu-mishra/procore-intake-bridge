import argparse
import tempfile
from pathlib import Path

from app.services.api_docs_review import build_api_docs_report, write_api_docs_artifacts

from app.config import get_settings

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-api-docs-", dir="/tmp"
    ) as directory:
        result = write_api_docs_artifacts(build_api_docs_report(settings), Path(directory))
        print(result.model_dump_json(indent=2))
else:
    result = write_api_docs_artifacts(
        build_api_docs_report(settings), args.output_root or settings.api_docs_output_root
    )
    print(result.model_dump_json(indent=2))
