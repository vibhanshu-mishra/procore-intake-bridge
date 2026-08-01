.PHONY: help start commands next try-demo prepare-sandbox prepare-pilot walkthroughs walkthroughs-check demo-walkthrough sandbox-walkthrough pilot-walkthrough sandbox-smoke-explain sandbox-smoke-preflight sandbox-smoke-evidence-template sandbox-read-plan sandbox-read-preflight sandbox-read-evidence-template sandbox-read-validation sandbox-evidence-template sandbox-evidence-check sandbox-evidence-mapping sandbox-evidence-artifact-check release-checklist release-readiness release-notes-draft release-readiness-artifact-check docs-site-check docs-preview-instructions docs-map first-run public-usability-audit safety-check test lint compile pip-check safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check storage-provider-template storage-provider-check storage-refs-check local-storage-provider-check cloud-storage-template cloud-storage-check cloud-storage-explain migration-status migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check webhook-verification-check customer-template customer-profile-check customer-artifact-check diagnostics support-bundle support-bundle-check pilot-template pilot-readiness-check pilot-artifact-check evidence-template evidence-manifest-check evidence-workspace-check evidence-review-template evidence-review-check evidence-expiry-check evidence-review-artifact-check pilot-approval-template pilot-approval-check pilot-approval-safety-check pilot-approval-artifact-check modes doctor setup-demo check-local demo demo-sync sandbox-check pilot-check mode-report private-workspace-template init-private-workspace validate-private-workspace private-workspace-git-safety private-workspace-check secret-provider-template secret-provider-check secret-refs-check file-secret-provider-check cloud-secret-template cloud-secret-check cloud-secret-explain postgres-runtime-template postgres-runtime-check postgres-migration-plan postgres-backup-restore-plan postgres-connectivity-check postgres-migration-status-check hosted-deployment-template hosted-deployment-check hosted-deployment-matrix hosted-deployment-artifact-check https-webhook-template https-webhook-check https-webhook-matrix webhook-disable-plan https-webhook-artifact-check hosted-pilot-dry-run-template hosted-pilot-dry-run-check hosted-pilot-dry-run-matrix hosted-pilot-dry-run-artifact-check final-readiness final-readiness-checklist public-handoff-summary final-readiness-artifact-check quality

PYTHON ?= .venv/bin/python

.PHONY: final-security-review security-readiness-summary security-gap-register private-security-review-checklist final-security-artifact-check
.PHONY: security-gap-closeout privacy-review-template encryption-at-rest-guidance private-security-action-register known-limitations-closeout security-gap-artifact-check
.PHONY: setup-experience-review first-run-checklist local-installer-guide setup-troubleshooting-guide setup-experience-artifact-check
.PHONY: demo-seed-plan demo-seed demo-reset-plan demo-reset demo-data-check demo-data-artifact-check
.PHONY: api-docs-review api-route-reference api-usage-examples openapi-local-guide api-docs-artifact-check
.PHONY: hosted-ui-review hosted-ui-page-inventory hosted-ui-readiness-checklist hosted-ui-private-gates hosted-ui-artifact-check
.PHONY: docs-site-polish-review docs-reader-paths docs-navigation-map docs-site-checklist docs-site-polish-artifact-check

.PHONY: security-threat-model security-boundary-map security-review-checklist security-threat-model-artifact-check auth-boundary-audit auth-boundary-map permission-boundary-checklist auth-boundary-artifact-check webhook-security-review webhook-signature-boundary webhook-replay-checklist webhook-security-artifact-check data-policy-review data-retention-map redaction-boundary-map data-handling-checklist data-policy-artifact-check infra-security-review secret-boundary-map storage-boundary-map database-boundary-map infra-security-checklist infra-security-artifact-check supply-chain-review dependency-boundary-map package-surface-map supply-chain-checklist supply-chain-artifact-check incident-response-review incident-runbook audit-log-boundary-map forensics-evidence-checklist incident-response-artifact-check demo-product-tour demo-product-check demo-evaluation-checklist demo-product-artifact-check product-dashboard-overview product-dashboard-check review-workspace-summary review-workspace-check intake-lifecycle-summary intake-lifecycle-check operator-triage-summary operator-triage-check attachment-review-summary attachment-review-check operator-export-check operator-export-summary operator-export-artifact-check

help:
	@echo "START HERE"
	@echo "  make start                  Safe onboarding summary, doctor, and next step"
	@echo "  make commands               Grouped command guide"
	@echo "  make doctor                 Local readiness summary"
	@echo "MODES"
	@echo "  make try-demo               Fixture-only demo; no credentials"
	@echo "  make prepare-sandbox        Offline private Sandbox preparation"
	@echo "  make prepare-pilot          Offline private Pilot preparation"
	@echo "  make walkthroughs           Guided Demo, Sandbox, and Pilot docs"
	@echo "  make demo-product-tour      Fake-data-only product evaluation tour"
	@echo "  make demo-product-check     Validate the offline Demo walkthrough pack"
	@echo "  make demo-evaluation-checklist Print the Demo maintainer checklist"
	@echo "  make security-threat-model   Offline public-safe threat model"
	@echo "  make security-boundary-map   Print trust-boundary summary"
	@echo "  make security-review-checklist Print offline security checklist"
	@echo "  make auth-boundary-audit      Offline auth/permission boundary audit"
	@echo "  make auth-boundary-map        Print offline route protection map"
	@echo "  make permission-boundary-checklist Print offline permission checklist"
	@echo "  make webhook-security-review Offline webhook hardening review"
	@echo "  make webhook-signature-boundary Print signature expectations"
	@echo "  make webhook-replay-checklist Print replay/deduplication checklist"
	@echo "  make data-policy-review       Offline retention/redaction policy review"
	@echo "  make data-retention-map       Print sanitized retention map"
	@echo "  make redaction-boundary-map   Print sanitized redaction map"
	@echo "  make data-handling-checklist  Print offline data-handling checklist"
	@echo "  make infra-security-review    Offline secrets/storage/DB review"
	@echo "  make secret-boundary-map      Print secret-reference boundaries"
	@echo "  make storage-boundary-map     Print storage metadata boundaries"
	@echo "  make database-boundary-map    Print database operation boundaries"
	@echo "  make infra-security-checklist Print infrastructure security checklist"
	@echo "  make supply-chain-review      Offline dependency/supply-chain review"
	@echo "  make dependency-boundary-map  Print dependency and extras boundaries"
	@echo "  make package-surface-map      Print package surface boundaries"
	@echo "  make supply-chain-checklist   Print offline supply-chain checklist"
	@echo "  make incident-response-review Offline incident/forensics readiness review"
	@echo "  make incident-runbook         Print placeholder incident runbook"
	@echo "  make audit-log-boundary-map   Print audit-log metadata boundaries"
	@echo "  make forensics-evidence-checklist Print private-reference checklist"
	@echo "  make final-security-review  Offline I1-I7 security readiness review"
	@echo "  make security-readiness-summary Print final security summary"
	@echo "  make security-gap-register Print private-review security gaps"
	@echo "  make private-security-review-checklist Print private review checklist"
	@echo "  make security-gap-closeout Offline policy-versus-implementation closeout"
	@echo "  make privacy-review-template Print public-safe privacy review template"
	@echo "  make encryption-at-rest-guidance Print infrastructure guidance only"
	@echo "  make private-security-action-register Print private review actions"
	@echo "  make known-limitations-closeout Print explicit security limitations"
	@echo "  make setup-experience-review Review the local-only setup path"
	@echo "  make first-run-checklist Print the safe first-run sequence"
	@echo "  make local-installer-guide Print local dependency setup guidance"
	@echo "  make setup-troubleshooting-guide Print git/python/pip/make/PATH help"
	@echo "  make demo-seed-plan Print the deterministic fake-data seed plan"
	@echo "  make demo-seed Seed only demo-marked records in local SQLite"
	@echo "  make demo-reset-plan Print the non-destructive reset plan"
	@echo "  make demo-data-check Validate fake-only local Demo records"
	@echo "  make api-docs-review Review all local FastAPI route boundaries"
	@echo "  make api-route-reference Print the classified local route table"
	@echo "  make api-usage-examples Print fake/local-only API examples"
	@echo "  make openapi-local-guide Print local OpenAPI viewing guidance"
	@echo "  make hosted-ui-review Review UI surfaces for future hosted evaluation"
	@echo "  make hosted-ui-page-inventory Print the classified local UI page inventory"
	@echo "  make hosted-ui-readiness-checklist Print the offline hosted UI checklist"
	@echo "  make hosted-ui-private-gates Print private review gates for hosted evaluation"
	@echo "  make docs-site-polish-review Review the local docs handbook structure"
	@echo "  make docs-reader-paths Print local evaluator and maintainer reading paths"
	@echo "  make docs-navigation-map Print the classified MkDocs navigation map"
	@echo "  make docs-site-checklist Print the offline docs-site readiness checklist"
	@echo "  make product-dashboard-overview Sanitized local product cockpit summary"
	@echo "  make product-dashboard-check Validate the read-only product cockpit"
	@echo "  make review-workspace-summary Read-only local intake summary"
	@echo "  make review-workspace-check Validate the local review workspace"
	@echo "  make intake-lifecycle-summary Read-only local lifecycle summary"
	@echo "  make intake-lifecycle-check Validate local transition rules"
	@echo "  make operator-triage-summary Read-only local triage summary"
	@echo "  make operator-triage-check Validate the local triage projection"
	@echo "  make attachment-review-summary Metadata-only attachment summary"
	@echo "  make attachment-review-check Validate safe attachment metadata review"
	@echo "  make operator-export-summary Print sanitized local export summary"
	@echo "  make operator-export-check Validate safe export rendering"
	@echo "  make operator-export-artifact-check Generate and clean temporary exports"
	@echo "  make sandbox-smoke-explain  Explain the separate manual live check"
	@echo "  make sandbox-read-plan      Offline bounded read-validation plan"
	@echo "  make sandbox-evidence-check  Validate placeholder-only Sandbox evidence refs"
	@echo "  make cloud-secret-check      Offline optional cloud-provider posture"
	@echo "  make cloud-storage-check     Offline optional cloud-storage posture"
	@echo "  make postgres-runtime-check  Offline PostgreSQL runtime posture"
	@echo "  make postgres-migration-plan Offline migration checklist; runs nothing"
	@echo "  make hosted-deployment-template Placeholder-only hosted template"
	@echo "  make hosted-deployment-matrix Conceptual hosted platform comparison"
	@echo "  make https-webhook-check     Offline HTTPS/webhook planning check"
	@echo "  make webhook-disable-plan    Offline disable checklist"
	@echo "  make hosted-pilot-dry-run-check Offline refs-only launch rehearsal check"
	@echo "SAFETY AND DEVELOPMENT"
	@echo "  make safety-check           Public usability, data, and route audits"
	@echo "  make docs-site-check        Validate local docs navigation; publishes nothing"
	@echo "  make release-readiness      Local checklist; publishes nothing"
	@echo "  make final-readiness        Final offline public repository review"
	@echo "  make quality                Complete offline developer checks"
	@echo "ADVANCED — MANUALLY GATED LIVE READS"
	@echo "  make sandbox-read-validation Separate bounded Sandbox read validation"
	@echo "  make postgres-connectivity-check Separate PostgreSQL connectivity probe"
	@echo "  make postgres-migration-status-check Separate PostgreSQL status-only probe"
	@echo "These advanced commands refuse by default and are never part of quality or onboarding."
	@echo "All friendly commands are local-only. See docs/command-reference.md for advanced commands."

start:
	$(PYTHON) scripts/onboarding_summary.py
	$(PYTHON) scripts/doctor.py
	$(PYTHON) scripts/print_next_steps.py

commands:
	$(PYTHON) scripts/print_command_guide.py

next:
	$(PYTHON) scripts/print_next_steps.py

walkthroughs:
	@echo "GUIDED WALKTHROUGHS"
	@echo "  Demo:    docs/walkthrough-demo.md (start here)"
	@echo "  Sandbox: docs/walkthrough-sandbox.md (optional/private)"
	@echo "  Pilot:   docs/walkthrough-pilot.md (optional/private)"
	@echo "Index: docs/walkthrough-index.md"

walkthroughs-check:
	$(PYTHON) scripts/check_walkthroughs.py

demo-walkthrough:
	@echo "Demo walkthrough — local fixtures only"
	@echo "  make start"
	@echo "  make try-demo"
	@echo "  make doctor"
	@echo "  make commands"
	@echo "  make next"

sandbox-walkthrough:
	@echo "Sandbox walkthrough — offline planning; live smoke is not run"
	@echo "  make start"
	@echo "  make init-private-workspace"
	@echo "  make commands"
	@echo "  make prepare-sandbox"
	@echo "See docs/walkthrough-sandbox.md before any separately authorized live action."

pilot-walkthrough:
	@echo "Pilot walkthrough — planning only; no approval, connection, or deployment"
	@echo "  make start"
	@echo "  make init-private-workspace"
	@echo "  make prepare-pilot"
	@echo "  make safety-check"
	@echo "Keep launch on hold; see docs/walkthrough-pilot.md."

sandbox-smoke-explain:
	$(PYTHON) scripts/explain_sandbox_smoke.py

sandbox-smoke-preflight:
	$(PYTHON) scripts/check_sandbox_smoke_preflight.py

sandbox-smoke-evidence-template:
	$(PYTHON) scripts/print_sandbox_smoke_evidence_template.py

sandbox-read-plan:
	$(PYTHON) scripts/print_sandbox_read_plan.py

sandbox-read-preflight:
	$(PYTHON) scripts/check_sandbox_read_preflight.py

sandbox-read-evidence-template:
	$(PYTHON) scripts/print_sandbox_read_evidence_template.py

sandbox-read-validation:
	$(PYTHON) scripts/run_sandbox_read_validation.py

sandbox-evidence-template:
	$(PYTHON) scripts/print_sandbox_evidence_linkage_template.py

sandbox-evidence-check:
	$(PYTHON) scripts/check_sandbox_evidence_linkage.py examples/sandbox-evidence-linkage/example_sandbox_evidence_profile.json

sandbox-evidence-mapping:
	$(PYTHON) scripts/print_sandbox_evidence_mapping.py

sandbox-evidence-artifact-check:
	$(PYTHON) scripts/generate_sandbox_evidence_linkage_artifacts.py examples/sandbox-evidence-linkage/example_sandbox_evidence_profile.json --temporary

release-checklist:
	$(PYTHON) scripts/print_release_checklist.py

release-readiness:
	$(PYTHON) scripts/check_release_readiness.py

release-notes-draft:
	$(PYTHON) scripts/print_release_notes_draft.py

release-readiness-artifact-check:
	$(PYTHON) scripts/generate_release_readiness_artifacts.py --temporary

docs-site-check:
	$(PYTHON) scripts/check_docs_site.py

docs-preview-instructions:
	$(PYTHON) scripts/print_docs_preview_instructions.py

docs-map:
	@echo "Documentation map: docs/docs-navigation.md"
	@echo "Site foundation:  docs/docs-site.md"
	@echo "Local-only; no build, publication, deployment, or GitHub Pages automation."

try-demo: demo-seed-plan setup-demo check-local demo
	@echo "Demo complete. Best next command: make doctor"

prepare-sandbox: sandbox-check
	$(PYTHON) scripts/print_next_steps.py --mode sandbox

prepare-pilot: pilot-check
	$(PYTHON) scripts/print_next_steps.py --mode pilot

first-run: start
	@echo "Compatibility target complete. Best next command: make try-demo"

public-usability-audit:
	$(PYTHON) scripts/audit_public_usability.py

safety-check: public-usability-audit safety-audit route-audit

security-threat-model:
	$(PYTHON) scripts/run_security_threat_model.py

security-boundary-map:
	$(PYTHON) scripts/print_security_boundary_map.py

security-review-checklist:
	$(PYTHON) scripts/print_security_review_checklist.py

security-threat-model-artifact-check:
	$(PYTHON) scripts/generate_security_threat_model_artifacts.py --temporary

auth-boundary-audit:
	$(PYTHON) scripts/run_auth_boundary_audit.py

auth-boundary-map:
	$(PYTHON) scripts/print_auth_boundary_map.py

permission-boundary-checklist:
	$(PYTHON) scripts/print_permission_boundary_checklist.py

auth-boundary-artifact-check:
	$(PYTHON) scripts/generate_auth_boundary_audit_artifacts.py --temporary

webhook-security-review:
	$(PYTHON) scripts/run_webhook_security_review.py

webhook-signature-boundary:
	$(PYTHON) scripts/print_webhook_signature_boundary.py

webhook-replay-checklist:
	$(PYTHON) scripts/print_webhook_replay_checklist.py

webhook-security-artifact-check:
	$(PYTHON) scripts/generate_webhook_security_review_artifacts.py --temporary

data-policy-review:
	$(PYTHON) scripts/run_data_policy_review.py

data-retention-map:
	$(PYTHON) scripts/print_data_retention_map.py

redaction-boundary-map:
	$(PYTHON) scripts/print_redaction_boundary_map.py

data-handling-checklist:
	$(PYTHON) scripts/print_data_handling_checklist.py

data-policy-artifact-check:
	$(PYTHON) scripts/generate_data_policy_review_artifacts.py --temporary

infra-security-review:
	$(PYTHON) scripts/run_infra_security_review.py

secret-boundary-map:
	$(PYTHON) scripts/print_secret_boundary_map.py

storage-boundary-map:
	$(PYTHON) scripts/print_storage_boundary_map.py

database-boundary-map:
	$(PYTHON) scripts/print_database_boundary_map.py

infra-security-checklist:
	$(PYTHON) scripts/print_infra_security_checklist.py

infra-security-artifact-check:
	$(PYTHON) scripts/generate_infra_security_review_artifacts.py --temporary
supply-chain-review:
	$(PYTHON) scripts/run_supply_chain_review.py
dependency-boundary-map:
	$(PYTHON) scripts/print_dependency_boundary_map.py
package-surface-map:
	$(PYTHON) scripts/print_package_surface_map.py
supply-chain-checklist:
	$(PYTHON) scripts/print_supply_chain_checklist.py
supply-chain-artifact-check:
	$(PYTHON) scripts/generate_supply_chain_review_artifacts.py --temporary
incident-response-review:
	$(PYTHON) scripts/run_incident_response_review.py
incident-runbook:
	$(PYTHON) scripts/print_incident_runbook.py
audit-log-boundary-map:
	$(PYTHON) scripts/print_audit_log_boundary_map.py
forensics-evidence-checklist:
	$(PYTHON) scripts/print_forensics_evidence_checklist.py
incident-response-artifact-check:
	$(PYTHON) scripts/generate_incident_response_review_artifacts.py --temporary
final-security-review:
	$(PYTHON) scripts/run_final_security_review.py
security-readiness-summary:
	$(PYTHON) scripts/print_security_readiness_summary.py
security-gap-register:
	$(PYTHON) scripts/print_security_gap_register.py
private-security-review-checklist:
	$(PYTHON) scripts/print_private_security_review_checklist.py
final-security-artifact-check:
	$(PYTHON) scripts/generate_final_security_review_artifacts.py --temporary
security-gap-closeout:
	$(PYTHON) scripts/run_security_gap_closeout.py
privacy-review-template:
	$(PYTHON) scripts/print_privacy_review_template.py
encryption-at-rest-guidance:
	$(PYTHON) scripts/print_encryption_at_rest_guidance.py
private-security-action-register:
	$(PYTHON) scripts/print_private_security_action_register.py
known-limitations-closeout:
	$(PYTHON) scripts/print_known_limitations_closeout.py
security-gap-artifact-check:
	$(PYTHON) scripts/generate_security_gap_closeout_artifacts.py --temporary
setup-experience-review:
	$(PYTHON) scripts/run_setup_experience_review.py
first-run-checklist:
	$(PYTHON) scripts/print_first_run_checklist.py
local-installer-guide:
	$(PYTHON) scripts/print_local_installer_guide.py
setup-troubleshooting-guide:
	$(PYTHON) scripts/print_setup_troubleshooting_guide.py
setup-experience-artifact-check:
	$(PYTHON) scripts/generate_setup_experience_artifacts.py --temporary
demo-seed-plan:
	$(PYTHON) scripts/plan_demo_seed.py
demo-seed:
	$(PYTHON) scripts/seed_demo_data.py
demo-reset-plan:
	$(PYTHON) scripts/plan_demo_reset.py
demo-reset:
	$(PYTHON) scripts/reset_demo_data.py --confirm "$(CONFIRM)"
demo-data-check:
	$(PYTHON) scripts/check_demo_data.py
demo-data-artifact-check:
	$(PYTHON) scripts/generate_demo_data_experience_artifacts.py --temporary
api-docs-review:
	$(PYTHON) scripts/run_api_docs_review.py
api-route-reference:
	$(PYTHON) scripts/print_api_route_reference.py
api-usage-examples:
	$(PYTHON) scripts/print_api_usage_examples.py
openapi-local-guide:
	$(PYTHON) scripts/print_openapi_local_guide.py
api-docs-artifact-check:
	$(PYTHON) scripts/generate_api_docs_artifacts.py --temporary
hosted-ui-review:
	$(PYTHON) scripts/run_hosted_ui_review.py
hosted-ui-page-inventory:
	$(PYTHON) scripts/print_hosted_ui_page_inventory.py
hosted-ui-readiness-checklist:
	$(PYTHON) scripts/print_hosted_ui_readiness_checklist.py
hosted-ui-private-gates:
	$(PYTHON) scripts/print_hosted_ui_private_gates.py
hosted-ui-artifact-check:
	$(PYTHON) scripts/generate_hosted_ui_review_artifacts.py --temporary
docs-site-polish-review:
	$(PYTHON) scripts/run_docs_site_polish_review.py
docs-reader-paths:
	$(PYTHON) scripts/print_docs_reader_paths.py
docs-navigation-map:
	$(PYTHON) scripts/print_docs_navigation_map.py
docs-site-checklist:
	$(PYTHON) scripts/print_docs_site_checklist.py
docs-site-polish-artifact-check:
	$(PYTHON) scripts/generate_docs_site_polish_artifacts.py --temporary

demo-product-tour:
	$(PYTHON) scripts/print_demo_product_tour.py

demo-product-check:
	$(PYTHON) scripts/check_demo_product_walkthrough.py

demo-evaluation-checklist:
	$(PYTHON) scripts/print_demo_evaluation_checklist.py

demo-product-artifact-check:
	$(PYTHON) scripts/generate_demo_product_walkthrough_artifacts.py --temporary

product-dashboard-overview:
	$(PYTHON) scripts/print_product_dashboard_overview.py

product-dashboard-check:
	$(PYTHON) scripts/check_product_dashboard.py

review-workspace-summary:
	$(PYTHON) scripts/print_intake_review_workspace_summary.py

review-workspace-check:
	$(PYTHON) scripts/check_intake_review_workspace.py

intake-lifecycle-summary:
	$(PYTHON) scripts/print_intake_lifecycle_summary.py

intake-lifecycle-check:
	$(PYTHON) scripts/check_intake_lifecycle.py

operator-triage-summary:
	$(PYTHON) scripts/print_operator_triage_summary.py

operator-triage-check:
	$(PYTHON) scripts/check_operator_triage_queue.py

attachment-review-summary:
	$(PYTHON) scripts/print_attachment_review_summary.py

attachment-review-check:
	$(PYTHON) scripts/check_attachment_review.py

operator-export-summary:
	$(PYTHON) scripts/print_operator_export_summary.py

operator-export-check:
	$(PYTHON) scripts/check_operator_export_pack.py

operator-export-artifact-check:
	$(PYTHON) scripts/generate_operator_export_pack.py --temporary

.PHONY: database-template database-check migration-plan backup-restore-plan database-connectivity-check
.PHONY: deployment-template deployment-check deployment-safety-check deployment-artifact-check https-webhook-checklist
.PHONY: sandbox-pilot-template sandbox-onboarding-check pilot-preflight sandbox-to-pilot-plan sandbox-pilot-artifact-check

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

storage-provider-template:
	$(PYTHON) scripts/print_storage_provider_template.py

storage-provider-check:
	$(PYTHON) scripts/check_attachment_storage.py

storage-refs-check:
	$(PYTHON) scripts/check_storage_refs.py

local-storage-provider-check:
	$(PYTHON) scripts/test_local_storage_provider.py

cloud-storage-template:
	$(PYTHON) scripts/print_cloud_storage_provider_template.py

cloud-storage-check:
	$(PYTHON) scripts/check_cloud_storage_provider.py

cloud-storage-explain:
	$(PYTHON) scripts/explain_cloud_storage_operations.py

migration-status:
	$(PYTHON) scripts/check_migration_status.py

database-template:
	$(PYTHON) scripts/print_database_template.py

database-check:
	$(PYTHON) scripts/check_database_readiness.py

migration-plan:
	$(PYTHON) scripts/plan_migration_execution.py

backup-restore-plan:
	$(PYTHON) scripts/plan_backup_restore.py

database-connectivity-check:
	$(PYTHON) scripts/check_database_connectivity.py

deployment-template:
	$(PYTHON) scripts/print_deployment_recipe_template.py --target docker_local

deployment-check:
	$(PYTHON) scripts/check_deployment_recipe.py examples/deployment-recipes/example_docker_local_recipe.json
	$(PYTHON) scripts/check_deployment_recipe.py examples/deployment-recipes/example_managed_paas_recipe.json

deployment-safety-check:
	$(PYTHON) scripts/check_deployment_safety.py examples/deployment-recipes/example_docker_local_recipe.json

deployment-artifact-check:
	$(PYTHON) scripts/generate_deployment_recipe_artifacts.py --help

https-webhook-checklist:
	$(PYTHON) scripts/print_https_webhook_checklist.py

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
	$(PYTHON) scripts/check_sandbox_onboarding.py examples/sandbox-pilot-flow/example_sandbox_flow.json

pilot-check:
	$(PYTHON) scripts/validate_customer_deployment_profile.py examples/customer-deployments/example_customer_profile.json
	$(PYTHON) scripts/validate_private_evidence_manifest.py examples/private-evidence/example_evidence_manifest.json
	$(PYTHON) scripts/validate_evidence_review.py examples/evidence-review/example_evidence_review_manifest.json
	$(PYTHON) scripts/check_evidence_expiry.py examples/evidence-review/example_evidence_review_manifest.json
	$(PYTHON) scripts/validate_pilot_readiness.py examples/pilot-readiness/example_pilot_profile.json
	$(PYTHON) scripts/validate_pilot_approval_packet.py examples/pilot-approval/example_pilot_approval_packet.json
	$(PYTHON) scripts/check_pilot_approval_safety.py examples/pilot-approval/example_pilot_approval_packet.json
	PROCORE_INTAKE_USAGE_MODE=pilot $(PYTHON) scripts/doctor.py
	$(PYTHON) scripts/check_pilot_preflight.py examples/sandbox-pilot-flow/example_pilot_flow.json

sandbox-pilot-template:
	$(PYTHON) scripts/print_sandbox_pilot_flow_template.py --path demo
	$(PYTHON) scripts/print_sandbox_pilot_flow_template.py --path sandbox
	$(PYTHON) scripts/print_sandbox_pilot_flow_template.py --path pilot

sandbox-onboarding-check:
	$(PYTHON) scripts/check_sandbox_onboarding.py examples/sandbox-pilot-flow/example_sandbox_flow.json

pilot-preflight:
	$(PYTHON) scripts/check_pilot_preflight.py examples/sandbox-pilot-flow/example_pilot_flow.json

sandbox-to-pilot-plan:
	$(PYTHON) scripts/print_sandbox_to_pilot_plan.py

sandbox-pilot-artifact-check:
	$(PYTHON) scripts/generate_sandbox_pilot_flow_artifacts.py --help

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

secret-provider-template:
	$(PYTHON) scripts/print_secret_provider_template.py

secret-provider-check:
	$(PYTHON) scripts/check_secret_provider.py

secret-refs-check:
	$(PYTHON) scripts/check_secret_refs.py

file-secret-provider-check:
	$(PYTHON) scripts/test_file_secret_provider.py

cloud-secret-template:
	$(PYTHON) scripts/print_cloud_secret_provider_template.py

cloud-secret-check:
	$(PYTHON) scripts/check_cloud_secret_provider.py

cloud-secret-explain:
	$(PYTHON) scripts/explain_cloud_secret_resolution.py

postgres-runtime-template:
	$(PYTHON) scripts/print_postgres_runtime_template.py

postgres-runtime-check:
	$(PYTHON) scripts/check_postgres_runtime.py

postgres-migration-plan:
	$(PYTHON) scripts/plan_postgres_migration_run.py

postgres-backup-restore-plan:
	$(PYTHON) scripts/plan_postgres_backup_restore_drill.py

postgres-connectivity-check:
	$(PYTHON) scripts/run_postgres_connectivity_check.py

postgres-migration-status-check:
	$(PYTHON) scripts/run_postgres_migration_status_check.py

hosted-deployment-template:
	$(PYTHON) scripts/print_hosted_deployment_template.py --platform docker_vps

hosted-deployment-check:
	$(PYTHON) scripts/check_hosted_deployment_template.py examples/hosted-deployment-templates/docker_vps.example.json

hosted-deployment-matrix:
	$(PYTHON) scripts/print_hosted_deployment_matrix.py

hosted-deployment-artifact-check:
	$(PYTHON) scripts/generate_hosted_deployment_artifacts.py examples/hosted-deployment-templates/docker_vps.example.json --temporary

https-webhook-template:
	$(PYTHON) scripts/print_https_webhook_template.py

https-webhook-check:
	$(PYTHON) scripts/check_https_webhook_plan.py examples/https-webhook-planning/example_https_webhook_profile.json

https-webhook-matrix:
	$(PYTHON) scripts/print_webhook_ingress_matrix.py

webhook-disable-plan:
	$(PYTHON) scripts/print_webhook_disable_plan.py

https-webhook-artifact-check:
	$(PYTHON) scripts/generate_https_webhook_artifacts.py examples/https-webhook-planning/example_https_webhook_profile.json --temporary

hosted-pilot-dry-run-template:
	$(PYTHON) scripts/print_hosted_pilot_dry_run_template.py

hosted-pilot-dry-run-check:
	$(PYTHON) scripts/check_hosted_pilot_dry_run.py examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json

hosted-pilot-dry-run-matrix:
	$(PYTHON) scripts/print_hosted_pilot_dry_run_matrix.py

hosted-pilot-dry-run-artifact-check:
	$(PYTHON) scripts/generate_hosted_pilot_dry_run_artifacts.py examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json --temporary

final-readiness:
	$(PYTHON) scripts/run_final_public_readiness_audit.py

final-readiness-checklist:
	$(PYTHON) scripts/print_final_public_readiness_checklist.py

public-handoff-summary:
	$(PYTHON) scripts/print_public_repo_handoff_summary.py

final-readiness-artifact-check:
	$(PYTHON) scripts/generate_final_public_readiness_artifacts.py --temporary

quality: lint compile pip-check public-usability-audit docs-site-check docs-preview-instructions walkthroughs-check sandbox-smoke-preflight sandbox-smoke-explain sandbox-smoke-evidence-template sandbox-read-plan sandbox-read-preflight sandbox-read-evidence-template sandbox-evidence-template sandbox-evidence-check sandbox-evidence-mapping release-readiness release-checklist release-notes-draft safety-audit route-audit admin-auth-check attachment-storage-check attachment-manifest-check storage-provider-template storage-provider-check storage-refs-check cloud-storage-check cloud-storage-template cloud-storage-explain database-template database-check migration-plan backup-restore-plan postgres-runtime-template postgres-runtime-check postgres-migration-plan postgres-backup-restore-plan hosted-deployment-template hosted-deployment-check hosted-deployment-matrix https-webhook-template https-webhook-check https-webhook-matrix webhook-disable-plan hosted-pilot-dry-run-template hosted-pilot-dry-run-check hosted-pilot-dry-run-matrix final-readiness final-readiness-checklist public-handoff-summary deployment-template deployment-check deployment-safety-check https-webhook-checklist migration-safety-check schema-drift-check webhook-verification-plan webhook-docs-check customer-template customer-profile-check diagnostics pilot-template pilot-readiness-check evidence-template evidence-manifest-check evidence-review-template evidence-review-check evidence-expiry-check pilot-approval-template pilot-approval-check pilot-approval-safety-check modes doctor check-local private-workspace-template private-workspace-git-safety secret-provider-check secret-provider-template secret-refs-check cloud-secret-check cloud-secret-template cloud-secret-explain sandbox-to-pilot-plan sandbox-pilot-template sandbox-onboarding-check pilot-preflight test
quality: review-workspace-check review-workspace-summary
quality: intake-lifecycle-check intake-lifecycle-summary
quality: operator-triage-check operator-triage-summary
quality: attachment-review-check attachment-review-summary
quality: operator-export-check operator-export-summary
quality: product-dashboard-check product-dashboard-overview
quality: demo-product-check demo-product-tour demo-evaluation-checklist
quality: security-threat-model security-boundary-map security-review-checklist
quality: auth-boundary-audit auth-boundary-map permission-boundary-checklist
quality: webhook-security-review webhook-signature-boundary webhook-replay-checklist
quality: data-policy-review data-retention-map redaction-boundary-map data-handling-checklist
quality: infra-security-review secret-boundary-map storage-boundary-map database-boundary-map infra-security-checklist
quality: supply-chain-review dependency-boundary-map package-surface-map supply-chain-checklist
quality: incident-response-review incident-runbook audit-log-boundary-map forensics-evidence-checklist
quality: final-security-review security-readiness-summary security-gap-register private-security-review-checklist
quality: security-gap-closeout privacy-review-template encryption-at-rest-guidance private-security-action-register known-limitations-closeout
quality: setup-experience-review first-run-checklist local-installer-guide setup-troubleshooting-guide
quality: demo-seed-plan demo-data-check demo-reset-plan
quality: api-docs-review api-route-reference api-usage-examples openapi-local-guide
quality: hosted-ui-review hosted-ui-page-inventory hosted-ui-readiness-checklist hosted-ui-private-gates
quality: docs-site-polish-review docs-reader-paths docs-navigation-map docs-site-checklist
	$(PYTHON) scripts/validate_private_workspace.py examples/private-workspace/example_workspace_manifest.json --strict
