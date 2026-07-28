.PHONY: test lint compile pip-check safety-audit route-audit migration-status migration-safety-check schema-drift-check quality

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

migration-status:
	$(PYTHON) scripts/check_migration_status.py

migration-safety-check:
	$(PYTHON) scripts/run_migration_safety_check.py

schema-drift-check:
	$(PYTHON) scripts/verify_schema_drift.py

quality: lint compile pip-check safety-audit route-audit migration-safety-check schema-drift-check test
