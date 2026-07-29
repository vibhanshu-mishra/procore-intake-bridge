#!/usr/bin/env python3
from app.config import get_settings
from app.main import app
from app.services.operator_diagnostics import (
    OperatorDiagnosticsBlockedError,
    build_operator_diagnostics_report,
)


def main() -> int:
    try:
        report = build_operator_diagnostics_report(get_settings(), app=app)
    except OperatorDiagnosticsBlockedError as exc:
        print(str(exc))
        return 2
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
