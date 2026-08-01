from app.config import get_settings
from app.services.version_prep import (
    build_version_prep_report,
    render_package_metadata_summary_markdown,
)

if __name__ == "__main__":
    report = build_version_prep_report(get_settings())
    print(render_package_metadata_summary_markdown(report), end="")
