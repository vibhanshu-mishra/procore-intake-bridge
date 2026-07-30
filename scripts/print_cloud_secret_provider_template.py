#!/usr/bin/env python3
"""Print placeholder-only cloud secret-provider setup templates."""

import json


def main() -> int:
    template = {
        "aws_secrets_manager": {
            "enabled": False,
            "region_ref": "AWS_REGION_REF_PLACEHOLDER",
            "secret_refs": ["AWS_SECRET_NAME_PLACEHOLDER"],
            "allow_resource_identifiers": False,
        },
        "azure_key_vault": {
            "enabled": False,
            "vault_name_ref": "AZURE_KEY_VAULT_NAME_REF_PLACEHOLDER",
            "secret_refs": ["AZURE_SECRET_NAME_PLACEHOLDER"],
            "allow_vault_url": False,
        },
        "gcp_secret_manager": {
            "enabled": False,
            "project_id_ref": "GCP_PROJECT_ID_REF_PLACEHOLDER",
            "secret_refs": ["GCP_SECRET_NAME_PLACEHOLDER"],
            "allow_resource_names": False,
        },
        "cloud_network_enabled": False,
        "secret_resolution_attempted": False,
        "external_calls": False,
        "values_exposed": False,
    }
    print(json.dumps(template, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
