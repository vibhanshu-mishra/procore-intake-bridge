from app.services.setup_experience import (
    build_setup_experience_report,
    render_setup_troubleshooting_guide_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_setup_experience_report(get_settings())
    print(render_setup_troubleshooting_guide_markdown(report), end="")
