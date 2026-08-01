from app.config import get_settings
from app.services.docs_site_polish import (
    build_docs_site_polish_report,
    render_docs_site_polish_markdown,
)

if __name__ == "__main__":
    report = build_docs_site_polish_report(get_settings())
    print(render_docs_site_polish_markdown(report), end="")
