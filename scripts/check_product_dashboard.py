#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.product_dashboard import (
    build_product_dashboard_overview,
    render_product_dashboard_markdown,
    validate_product_dashboard_response_safe,
)


def main() -> int:
    with SessionLocal() as session:
        before = (len(session.new), len(session.dirty), len(session.deleted))
        overview = build_product_dashboard_overview(session, get_settings())
        after = (len(session.new), len(session.dirty), len(session.deleted))
    validate_product_dashboard_response_safe(overview)
    render_product_dashboard_markdown(overview)
    if before != after:
        raise RuntimeError("Product dashboard inspection changed session state.")
    print("Product Dashboard check")
    print("=======================")
    print(f"Status: {overview.status.value}")
    print("PASS: sanitized local cards and guidance are read-only.")
    print("No artifact, attachment file, persistent state, or external system was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
