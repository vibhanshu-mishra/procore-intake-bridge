from app.services.final_security_review import (
    build_final_security_review_report,
    render_private_security_review_checklist_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_final_security_review_report(get_settings())
    print(render_private_security_review_checklist_markdown(report), end="")
