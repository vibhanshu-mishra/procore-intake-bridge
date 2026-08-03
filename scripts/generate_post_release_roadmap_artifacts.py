import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.post_release_roadmap import (
    build_post_release_roadmap_report,
    write_post_release_roadmap_artifacts,
)

parser = argparse.ArgumentParser()
parser.add_argument("--output-root", type=Path)
parser.add_argument("--temporary", action="store_true")
args = parser.parse_args()
settings = get_settings()

if args.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-post-release-roadmap-", dir="/tmp"
    ) as directory:
        result = write_post_release_roadmap_artifacts(
            build_post_release_roadmap_report(settings), Path(directory)
        )
        print(result.model_dump_json(indent=2))
else:
    result = write_post_release_roadmap_artifacts(
        build_post_release_roadmap_report(settings),
        args.output_root or settings.post_release_roadmap_output_root,
    )
    print(result.model_dump_json(indent=2))
