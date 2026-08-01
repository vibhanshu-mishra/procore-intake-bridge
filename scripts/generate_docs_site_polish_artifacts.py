import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.docs_site_polish import (
    build_docs_site_polish_report,
    write_docs_site_polish_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-docs-site-polish-", dir="/tmp"
    ) as directory:
        result = write_docs_site_polish_artifacts(
            build_docs_site_polish_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_docs_site_polish_artifacts(
        build_docs_site_polish_report(settings),
        args.output_root or settings.docs_site_polish_output_root,
    )
    print(result.model_dump_json(indent=2))
