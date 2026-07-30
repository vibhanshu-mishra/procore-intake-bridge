#!/usr/bin/env python3
from app.config import get_settings
from app.services.security_threat_model import (
    build_security_threat_model_report,
    render_security_boundary_map,
)


def main() -> int:
    print(render_security_boundary_map(build_security_threat_model_report(get_settings())), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
