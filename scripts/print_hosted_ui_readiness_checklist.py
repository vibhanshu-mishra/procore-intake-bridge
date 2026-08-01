from app.config import get_settings
from app.services.hosted_ui_review import (
    build_hosted_ui_review_report,
    render_hosted_ui_readiness_checklist_markdown,
)

if __name__ == "__main__":
    report = build_hosted_ui_review_report(get_settings())
    print(render_hosted_ui_readiness_checklist_markdown(report), end="")
