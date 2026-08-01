import argparse
import tempfile
from pathlib import Path

from app.config import get_settings
from app.services.incident_response_review import (
    build_incident_response_review_report,
    write_incident_response_review_artifacts,
)

p = argparse.ArgumentParser()
p.add_argument("--output-root", type=Path)
p.add_argument("--temporary", action="store_true")
a = p.parse_args()
s = get_settings()
if a.temporary:
    with tempfile.TemporaryDirectory(
        prefix="procore-intake-bridge-incident-response-", dir="/tmp"
    ) as d:
        print(
            write_incident_response_review_artifacts(
                build_incident_response_review_report(s), Path(d)
            ).model_dump_json(indent=2)
        )
else:
    print(
        write_incident_response_review_artifacts(
            build_incident_response_review_report(s),
            a.output_root or s.incident_response_review_output_root,
        ).model_dump_json(indent=2)
    )
