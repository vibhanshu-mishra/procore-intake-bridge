#!/usr/bin/env python3

from app.services.command_ux import render_command_guide


def main() -> int:
    print(render_command_guide(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
