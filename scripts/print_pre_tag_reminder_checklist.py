from app.config import get_settings
from app.services.post_release_roadmap import (
    build_post_release_roadmap_report,
    render_pre_tag_reminder_checklist_markdown,
)

if __name__ == "__main__":
    report = build_post_release_roadmap_report(get_settings())
    print(render_pre_tag_reminder_checklist_markdown(report), end="")
