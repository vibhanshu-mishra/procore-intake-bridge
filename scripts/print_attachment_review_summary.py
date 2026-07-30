#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.attachment_review import (
    build_attachment_review_workspace_summary,
    render_attachment_review_markdown,
)


def main() -> int:
    with SessionLocal() as session:
        summary = build_attachment_review_workspace_summary(session, get_settings())
    print(render_attachment_review_markdown(summary))
    print("No file, storage provider, Procore, or external operation was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
