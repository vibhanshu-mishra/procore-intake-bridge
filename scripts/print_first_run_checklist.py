from app.services.setup_experience import (
    build_setup_experience_report,
    render_first_run_checklist_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_setup_experience_report(get_settings())
    print(render_first_run_checklist_markdown(report), end="")
