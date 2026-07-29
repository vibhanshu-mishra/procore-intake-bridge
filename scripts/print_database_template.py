#!/usr/bin/env python3
import json


def main() -> int:
    print(json.dumps({
        "demo": {
            "provider": "sqlite",
            "database_ref": "SQLITE_LOCAL_REFERENCE",
            "external_connect": False,
        },
        "sandbox_pilot": {
            "provider": "postgres",
            "database_url_ref": "ENV_REF_PLACEHOLDER_DATABASE_URL",
            "ssl": "POSTGRES_SSL_MODE_PLACEHOLDER",
            "external_connect_enabled_by_default": False,
        },
        "database_url_exposed": False,
        "credentials_exposed": False,
        "hostnames_exposed": False,
        "external_calls": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
