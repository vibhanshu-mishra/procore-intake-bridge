from app.config import get_settings
from app.services.post_release_roadmap import (
    build_post_release_roadmap_report,
    render_private_review_backlog_markdown,
)

if __name__ == "__main__":
    report = build_post_release_roadmap_report(get_settings())
    print(render_private_review_backlog_markdown(report), end="")
