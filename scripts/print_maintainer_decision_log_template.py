from app.config import get_settings
from app.services.maintainer_handoff import (
    build_maintainer_handoff_report,
    render_maintainer_decision_log_template_markdown,
)

if __name__ == "__main__":
    report = build_maintainer_handoff_report(get_settings())
    print(render_maintainer_decision_log_template_markdown(report), end="")
