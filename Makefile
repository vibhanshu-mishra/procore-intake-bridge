.PHONY: test lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-status migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check webhook-verification-check customer-template customer-profile-check customer-artifact-check diagnostics support-bundle support-bundle-check pilot-template pilot-readiness-check pilot-artifact-check quality

PYTHON ?= .venv/bin/python

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

compile:
	$(PYTHON) -m compileall app

pip-check:
	$(PYTHON) -m pip check

safety-audit:
	$(PYTHON) scripts/audit_public_safety.py

route-audit:
	$(PYTHON) scripts/audit_routes_read_only.py

admin-auth-check:
	$(PYTHON) scripts/check_admin_auth.py

attachment-storage-check:
	$(PYTHON) scripts/check_attachment_storage.py

attachment-manifest-check:
	$(PYTHON) scripts/check_attachment_manifest_consistency.py

migration-status:
	$(PYTHON) scripts/check_migration_status.py

migration-safety-check:
	$(PYTHON) scripts/run_migration_safety_check.py

schema-drift-check:
	$(PYTHON) scripts/verify_schema_drift.py

webhook-verification-plan:
	$(PYTHON) scripts/print_webhook_verification_plan.py

webhook-docs-check:
	$(PYTHON) scripts/check_webhook_docs_record.py examples/webhook-verification/example_docs_record.json

webhook-verification-check:
	$(PYTHON) scripts/run_webhook_verification.py --help

customer-template:
	$(PYTHON) scripts/print_customer_deployment_template.py

customer-profile-check:
	$(PYTHON) scripts/validate_customer_deployment_profile.py examples/customer-deployments/example_customer_profile.json

customer-artifact-check:
	$(PYTHON) scripts/generate_customer_deployment_artifacts.py --help

diagnostics:
	$(PYTHON) scripts/print_operator_diagnostics.py

support-bundle:
	$(PYTHON) scripts/generate_support_bundle.py

support-bundle-check:
	$(PYTHON) scripts/check_support_bundle_redaction.py support-output

pilot-template:
	$(PYTHON) scripts/print_pilot_readiness_template.py

pilot-readiness-check:
	$(PYTHON) scripts/validate_pilot_readiness.py examples/pilot-readiness/example_pilot_profile.json

pilot-artifact-check:
	$(PYTHON) scripts/generate_pilot_readiness_artifacts.py --help

quality: lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check customer-template customer-profile-check diagnostics pilot-template pilot-readiness-check test
