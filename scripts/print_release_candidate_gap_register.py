from app.config import get_settings
from app.services.release_candidate_review import (
    build_release_candidate_report,
    render_release_candidate_gap_register_markdown,
)

if __name__ == "__main__":
    report = build_release_candidate_report(get_settings())
    print(render_release_candidate_gap_register_markdown(report), end="")
