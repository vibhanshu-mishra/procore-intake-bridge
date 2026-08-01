from app.services.api_docs_review import (
    build_api_docs_report,
    render_openapi_local_guide_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_api_docs_report(get_settings())
    print(render_openapi_local_guide_markdown(report), end="")
