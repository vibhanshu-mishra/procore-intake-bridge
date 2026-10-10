from app.config import get_settings
from app.services.setup_experience import (
    build_setup_experience_report,
    render_local_installer_guide_markdown,
)

if __name__ == "__main__":
    report = build_setup_experience_report(get_settings())
    print(render_local_installer_guide_markdown(report), end="")
