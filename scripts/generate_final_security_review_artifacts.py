import argparse
import tempfile
from pathlib import Path

from app.services.final_security_review import (
    build_final_security_review_report,
    write_final_security_review_artifacts,
)

from app.config import get_settings

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-final-security-", dir="/tmp"
    ) as directory:
        result = write_final_security_review_artifacts(
            build_final_security_review_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_final_security_review_artifacts(
        build_final_security_review_report(settings),
        args.output_root or settings.final_security_review_output_root,
    )
    print(result.model_dump_json(indent=2))
