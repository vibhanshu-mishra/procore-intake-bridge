from app.config import get_settings
from app.services.incident_response_review import (
    build_incident_response_review_report,
    render_audit_log_boundary_map_markdown,
)

if __name__ == "__main__":
    print(
        render_audit_log_boundary_map_markdown(
            build_incident_response_review_report(get_settings())
        ),
        end="",
    )
