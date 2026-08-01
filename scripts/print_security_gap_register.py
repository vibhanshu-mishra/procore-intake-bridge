from app.services.final_security_review import (
    build_final_security_review_report,
    render_security_gap_register_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_final_security_review_report(get_settings())
    print(render_security_gap_register_markdown(report), end="")
