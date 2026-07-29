#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Settings
from app.security.secrets import FileSecretProvider


def main() -> int:
    with TemporaryDirectory(prefix="procore-intake-bridge-") as temporary:
        root = Path(temporary) / "private-secrets"
        target = root / "dmsa" / "client_secret.secret"
        target.parent.mkdir(parents=True)
        target.write_text("fake-temporary-secret-value\n", encoding="utf-8")
        settings = Settings(
            _env_file=None,
            secret_provider="file",
            file_secret_root=root,
        )
        provider = FileSecretProvider(settings)
        resolved = provider.get_secret("dmsa/client_secret.secret")
        if resolved != "fake-temporary-secret-value":
            print("File secret provider check failed; values were suppressed.")
            return 1
        masked = provider.describe_ref("dmsa/client_secret.secret")["masked_ref"]
        print(f"File secret provider check passed for {masked}; value was not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
