.PHONY: test lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-status migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check webhook-verification-check quality

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

quality: lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check test
