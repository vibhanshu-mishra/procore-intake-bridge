#!/usr/bin/env python3
from app.config import get_settings
from app.database import SessionLocal
from app.services.product_dashboard import (
    build_product_dashboard_overview,
    render_product_dashboard_markdown,
)


def main() -> int:
    with SessionLocal() as session:
        overview = build_product_dashboard_overview(session, get_settings())
    print(render_product_dashboard_markdown(overview), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
