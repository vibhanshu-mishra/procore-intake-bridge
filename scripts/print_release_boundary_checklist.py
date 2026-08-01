from app.config import get_settings
from app.services.version_prep import (
    build_version_prep_report,
    render_release_boundary_checklist_markdown,
)

if __name__ == "__main__":
    report = build_version_prep_report(get_settings())
    print(render_release_boundary_checklist_markdown(report), end="")
