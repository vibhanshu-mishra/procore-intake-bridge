#!/usr/bin/env python3
from app.config import get_settings
from app.services.demo_product_walkthrough import (
    build_demo_product_walkthrough_report,
    render_demo_product_tour_markdown,
)


def main() -> int:
    report = build_demo_product_walkthrough_report(get_settings())
    print(render_demo_product_tour_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
