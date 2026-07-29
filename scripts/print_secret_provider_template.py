#!/usr/bin/env python3
import json


def main() -> int:
    template = {
        "env_provider": {
            "provider": "env",
            "refs": {
                "client_id_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_DMSA_CLIENT_ID",
                "client_secret_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_DMSA_CLIENT_SECRET",
                "admin_token_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_TOKEN",
                "webhook_secret_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_WEBHOOK_SECRET",
            },
        },
        "file_provider": {
            "provider": "file",
            "root": "private-workspace/environment/secrets",
            "refs": {
                "client_id_ref": "dmsa/client_id.secret",
                "client_secret_ref": "dmsa/client_secret.secret",
                "admin_token_ref": "admin/admin_token.secret",
                "webhook_secret_ref": "webhooks/procore_signature.secret",
            },
        },
        "cloud_providers": {
            "optional": True,
            "enabled_by_default": False,
            "external_calls": False,
        },
        "placeholder_values_only": True,
        "values_exposed": False,
    }
    print(json.dumps(template, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
