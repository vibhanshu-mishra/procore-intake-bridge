#!/usr/bin/env python3
import json

from app.schemas.customer_deployment import CustomerDeploymentProfile


def build_template() -> CustomerDeploymentProfile:
    return CustomerDeploymentProfile.model_validate({
        "profile_name": "example-customer-local",
        "customer_label": "Example Customer",
        "environment": "local",
        "public_base_url": "http://example-customer.local",
        "allowed_hosts": ["example-customer.local"],
        "requested_project_scopes": [{
            "company_id": "COMPANY_ID_PLACEHOLDER",
            "project_id": "PROJECT_ID_PLACEHOLDER_001",
            "project_label": "PROJECT_NAME_PLACEHOLDER_001",
        }],
        "dmsa_connection_ref": "PROCORE_INTAKE_CONNECTION_EXAMPLE",
        "dmsa_client_id_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_DMSA_CLIENT_ID",
        "dmsa_client_secret_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_DMSA_CLIENT_SECRET",
        "admin_token_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_TOKEN",
        "admin_rotation_token_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_ADMIN_ROTATION_TOKEN",
        "webhook_secret_ref": "PROCORE_INTAKE_SECRET_EXAMPLE_WEBHOOK_SECRET",
        "storage_bucket_ref": "STORAGE_BUCKET_REF_PLACEHOLDER",
        "notes": ["Fake placeholder template only; no external calls or deployment."],
    })


def main() -> int:
    print(json.dumps(build_template().model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
