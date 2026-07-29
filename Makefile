.PHONY: test lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-status migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check webhook-verification-check customer-template customer-profile-check customer-artifact-check diagnostics support-bundle support-bundle-check pilot-template pilot-readiness-check pilot-artifact-check evidence-template evidence-manifest-check evidence-workspace-check evidence-review-template evidence-review-check evidence-expiry-check evidence-review-artifact-check pilot-approval-template pilot-approval-check pilot-approval-safety-check pilot-approval-artifact-check modes doctor setup-demo check-local demo demo-sync sandbox-check pilot-check mode-report private-workspace-template init-private-workspace validate-private-workspace private-workspace-git-safety private-workspace-check quality

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

evidence-template:
	$(PYTHON) scripts/print_private_evidence_template.py

evidence-manifest-check:
	$(PYTHON) scripts/validate_private_evidence_manifest.py examples/private-evidence/example_evidence_manifest.json

evidence-workspace-check:
	$(PYTHON) scripts/generate_private_evidence_workspace.py --help

evidence-review-template:
	$(PYTHON) scripts/print_evidence_review_template.py

evidence-review-check:
	$(PYTHON) scripts/validate_evidence_review.py examples/evidence-review/example_evidence_review_manifest.json

evidence-expiry-check:
	$(PYTHON) scripts/check_evidence_expiry.py examples/evidence-review/example_evidence_review_manifest.json

evidence-review-artifact-check:
	$(PYTHON) scripts/generate_evidence_review_artifacts.py --help

pilot-approval-template:
	$(PYTHON) scripts/print_pilot_approval_template.py

pilot-approval-check:
	$(PYTHON) scripts/validate_pilot_approval_packet.py examples/pilot-approval/example_pilot_approval_packet.json

pilot-approval-safety-check:
	$(PYTHON) scripts/check_pilot_approval_safety.py examples/pilot-approval/example_pilot_approval_packet.json

pilot-approval-artifact-check:
	$(PYTHON) scripts/generate_pilot_approval_packet.py --help

modes:
	$(PYTHON) scripts/print_usage_modes.py

doctor:
	$(PYTHON) scripts/doctor.py

setup-demo:
	$(PYTHON) scripts/setup_demo_mode.py

check-local:
	$(PYTHON) scripts/check_local_setup.py

demo: check-local
	$(PYTHON) scripts/run_poll_once.py

demo-sync:
	$(PYTHON) scripts/run_poll_once.py

sandbox-check:
	PROCORE_INTAKE_USAGE_MODE=sandbox $(PYTHON) scripts/doctor.py

pilot-check:
	$(PYTHON) scripts/validate_customer_deployment_profile.py examples/customer-deployments/example_customer_profile.json
	$(PYTHON) scripts/validate_private_evidence_manifest.py examples/private-evidence/example_evidence_manifest.json
	$(PYTHON) scripts/validate_evidence_review.py examples/evidence-review/example_evidence_review_manifest.json
	$(PYTHON) scripts/check_evidence_expiry.py examples/evidence-review/example_evidence_review_manifest.json
	$(PYTHON) scripts/validate_pilot_readiness.py examples/pilot-readiness/example_pilot_profile.json
	$(PYTHON) scripts/validate_pilot_approval_packet.py examples/pilot-approval/example_pilot_approval_packet.json
	$(PYTHON) scripts/check_pilot_approval_safety.py examples/pilot-approval/example_pilot_approval_packet.json
	PROCORE_INTAKE_USAGE_MODE=pilot $(PYTHON) scripts/doctor.py

mode-report:
	$(PYTHON) scripts/generate_mode_report.py

private-workspace-template:
	$(PYTHON) scripts/print_private_workspace_template.py

init-private-workspace:
	$(PYTHON) scripts/init_private_workspace.py

validate-private-workspace:
	$(PYTHON) scripts/validate_private_workspace.py private-workspace --strict

private-workspace-git-safety:
	$(PYTHON) scripts/check_private_workspace_git_safety.py

private-workspace-check: validate-private-workspace private-workspace-git-safety

quality: lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check customer-template customer-profile-check diagnostics pilot-template pilot-readiness-check evidence-template evidence-manifest-check evidence-review-template evidence-review-check evidence-expiry-check pilot-approval-template pilot-approval-check pilot-approval-safety-check modes doctor check-local private-workspace-template private-workspace-git-safety test
	$(PYTHON) scripts/validate_private_workspace.py examples/private-workspace/example_workspace_manifest.json --strict
