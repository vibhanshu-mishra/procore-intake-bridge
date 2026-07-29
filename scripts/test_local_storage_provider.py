#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Settings
from app.services.storage import LocalStorageProvider


def main() -> int:
    with TemporaryDirectory(prefix="procore-intake-bridge-") as temporary:
        root = Path(temporary) / "private-storage"
        settings = Settings(
            _env_file=None,
            storage_provider="local",
            local_storage_root=root,
            local_storage_allow_absolute_root=True,
        )
        provider = LocalStorageProvider(settings)
        value = b"fake temporary storage value"
        written = provider.write("checks/example.txt", value)
        if provider.read("checks/example.txt") != value:
            print("Local storage provider check failed; contents were suppressed.")
            return 1
        listed = provider.list()
        deleted = provider.delete("checks/example.txt")
        if not listed.items or not deleted.deleted:
            print("Local storage provider check failed; details were suppressed.")
            return 1
        print(
            f"Local storage provider check passed for {written.masked_ref}; "
            "contents and paths were not displayed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
