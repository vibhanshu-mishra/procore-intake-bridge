from app.config import get_settings
from app.services.post_release_roadmap import (
    build_post_release_roadmap_report,
    render_known_limitations_register_markdown,
)

if __name__ == "__main__":
    report = build_post_release_roadmap_report(get_settings())
    print(render_known_limitations_register_markdown(report), end="")
