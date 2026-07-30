#!/usr/bin/env python3

from app.services.release_readiness import (
    build_release_readiness_report,
    render_release_notes_draft,
)


def main() -> int:
    print(render_release_notes_draft(build_release_readiness_report()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
