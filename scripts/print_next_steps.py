#!/usr/bin/env python3

import argparse

from app.schemas.command_ux import CommandMode
from app.services.command_ux import next_steps_for_mode


def main() -> int:
    parser = argparse.ArgumentParser(description="Print safe local next-step guidance.")
    parser.add_argument(
        "--mode",
        choices=("demo", "sandbox", "pilot"),
        default="demo",
    )
    args = parser.parse_args()
    print(f"{args.mode.title()} Mode — what to run next")
    print("=" * (23 + len(args.mode)))
    for line in next_steps_for_mode(CommandMode(args.mode)):
        print(line)
    print("Safety: this guide reads no private files and makes no external or Procore calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
