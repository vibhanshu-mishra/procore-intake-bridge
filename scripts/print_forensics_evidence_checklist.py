from app.config import get_settings
from app.services.incident_response_review import (
    build_incident_response_review_report,
    render_forensics_evidence_checklist_markdown,
)

if __name__ == "__main__":
    print(
        render_forensics_evidence_checklist_markdown(
            build_incident_response_review_report(get_settings())
        ),
        end="",
    )
