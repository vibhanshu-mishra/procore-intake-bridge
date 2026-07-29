#!/usr/bin/env python3
import subprocess
from pathlib import Path

PRIVATE_PARTS = {
    "private-workspace",
    ".local-workspace",
    "sandbox-workspace",
    "pilot-workspace",
}
PRIVATE_SUFFIXES = (
    ".private.json",
    ".private.md",
    ".private.env",
    ".workspace-report.json",
    ".workspace-report.md",
    ".workspace-manifest.json",
)


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    unsafe = [
        item
        for item in tracked
        if any(part in PRIVATE_PARTS for part in Path(item).parts)
        and not item.startswith("examples/private-workspace/")
        or Path(item).name.endswith(PRIVATE_SUFFIXES)
    ]
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", "private-workspace/example.private.md"],
            check=False,
        ).returncode
        == 0
    )
    if unsafe or not ignored:
        print("Private workspace git safety check failed; paths were suppressed.")
        return 1
    print("Private workspace git safety check passed; generated workspace paths are ignored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
