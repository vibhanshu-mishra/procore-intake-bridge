from app.config import get_settings
from app.services.versioned_release_handoff import (
    build_versioned_release_handoff_report,
    render_release_scope_summary_markdown,
)

if __name__ == "__main__":
    report = build_versioned_release_handoff_report(get_settings())
    print(render_release_scope_summary_markdown(report), end="")
