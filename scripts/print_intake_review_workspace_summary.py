#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.intake_review_workspace import (
    build_intake_review_workspace_summary,
    render_intake_review_workspace_markdown,
)


def main() -> int:
    with SessionLocal() as session:
        summary = build_intake_review_workspace_summary(session, get_settings())
    print(render_intake_review_workspace_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
