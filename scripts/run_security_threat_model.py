#!/usr/bin/env python3
from app.config import get_settings
from app.services.security_threat_model import (
    build_security_threat_model_report,
    render_security_threat_model_markdown,
)


def main() -> int:
    report = build_security_threat_model_report(get_settings())
    print(render_security_threat_model_markdown(report), end="")
    return 0 if report.status.value == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
