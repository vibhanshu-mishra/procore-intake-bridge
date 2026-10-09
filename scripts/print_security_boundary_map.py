#!/usr/bin/env python3
from app.config import get_settings
from app.services.security_threat_model import (
    build_security_threat_model_report,
    render_security_boundary_map,
)


def main() -> int:
    print(
    "[INFO] Secret boundary map generated successfully "
    f"(length={len(rendered_boundary_map)} chars)."
    )


if __name__ == "__main__":
    raise SystemExit(main())
