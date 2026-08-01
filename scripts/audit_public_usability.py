#!/usr/bin/env python3
"""Audit the public repository's first-run usability without exposing private data."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    level: str
    check: str
    message: str


REQUIRED_DOCS = {
    "QUICKSTART.md",
    "docs/index.md",
    "docs/usage-modes.md",
    "docs/quickstart-demo.md",
    "docs/sandbox-mode.md",
    "docs/pilot-mode.md",
    "docs/command-reference.md",
    "docs/first-run-checklist.md",
    "docs/troubleshooting.md",
    "docs/private-workspace-bootstrap.md",
    "docs/secret-providers.md",
    "docs/cloud-secret-providers.md",
    "docs/aws-secrets-manager.md",
    "docs/azure-key-vault-secrets.md",
    "docs/gcp-secret-manager.md",
    "docs/cloud-storage-providers.md",
    "docs/s3-storage.md",
    "docs/azure-blob-storage.md",
    "docs/gcs-storage.md",
    "docs/postgres-runtime-operations.md",
    "docs/postgres-connection-pooling.md",
    "docs/postgres-migration-runbook.md",
    "docs/postgres-backup-restore-drills.md",
    "docs/hosted-deployment-templates.md",
    "docs/docker-vps-hosting.md",
    "docs/managed-paas-hosting.md",
    "docs/container-platform-hosting.md",
    "docs/cloud-platform-hosting.md",
    "docs/https-webhook-production-planning.md",
    "docs/webhook-ingress-planning.md",
    "docs/tls-dns-planning.md",
    "docs/webhook-disable-rollback.md",
    "docs/hosted-pilot-dry-run.md",
    "docs/pilot-operations-rehearsal.md",
    "docs/hosted-pilot-evidence-map.md",
    "docs/final-public-readiness.md",
    "docs/public-repository-handoff.md",
    "docs/final-readiness-checklist.md",
    "docs/maintainer-review-fix-pack.md",
    "docs/intake-review-workspace.md",
    "docs/intake-lifecycle-status-flow.md",
    "docs/operator-triage-queue.md",
    "docs/attachment-review-manifest-ux.md",
    "docs/operator-export-pack.md",
    "docs/product-dashboard.md",
    "docs/demo-product-walkthrough.md",
    "docs/demo-evaluation-checklist.md",
    "docs/security-threat-model.md",
    "docs/security-boundary-map.md",
    "docs/security-review-checklist.md",
    "docs/auth-permission-boundary-audit.md",
    "docs/auth-boundary-map.md",
    "docs/permission-boundary-checklist.md",
    "docs/webhook-replay-signature-hardening.md",
    "docs/webhook-signature-boundary.md",
    "docs/webhook-replay-checklist.md",
    "docs/data-retention-redaction-policy.md",
    "docs/data-retention-map.md",
    "docs/redaction-boundary-map.md",
    "docs/data-handling-checklist.md",
    "docs/secrets-storage-db-security-review.md",
    "docs/secret-boundary-map.md",
    "docs/storage-boundary-map.md",
    "docs/database-boundary-map.md",
    "docs/infra-security-checklist.md",
    "docs/dependency-supply-chain-security.md",
    "docs/dependency-boundary-map.md",
    "docs/package-surface-map.md",
    "docs/supply-chain-checklist.md",
    "docs/incident-response-forensics.md",
    "docs/incident-runbook.md",
    "docs/audit-log-boundary-map.md",
    "docs/forensics-evidence-checklist.md",
    "docs/final-security-readiness-review.md",
    "docs/security-readiness-summary.md",
    "docs/security-gap-register.md",
    "docs/private-security-review-checklist.md",
    "docs/security-gap-closeout.md",
    "docs/privacy-review-template.md",
    "docs/encryption-at-rest-guidance.md",
    "docs/private-security-action-register.md",
    "docs/known-limitations-closeout.md",
    "docs/local-installer-guide.md",
    "docs/first-run-checklist.md",
    "docs/setup-troubleshooting-guide.md",
    "docs/setup-experience-review.md",
    "docs/demo-data-seed-reset.md",
    "docs/demo-seed-plan.md",
    "docs/demo-reset-guide.md",
    "docs/api-route-reference.md",
    "docs/api-usage-examples.md",
    "docs/openapi-local-guide.md",
    "docs/api-docs-review.md",
    "docs/hosted-ui-preparation.md",
    "docs/hosted-ui-page-inventory.md",
    "docs/hosted-ui-readiness-checklist.md",
    "docs/hosted-ui-private-gates.md",
    "docs/docs-site-polish.md",
    "docs/docs-reader-paths.md",
    "docs/docs-navigation-map.md",
    "docs/storage-providers.md",
    "docs/database-providers.md",
    "docs/deployment-recipes.md",
    "docs/walkthrough-index.md",
    "docs/walkthrough-demo.md",
    "docs/walkthrough-sandbox.md",
    "docs/walkthrough-pilot.md",
    "docs/sandbox-smoke-ux.md",
    "docs/sandbox-smoke-evidence.md",
    "docs/release-readiness.md",
    "docs/release-checklist.md",
    "docs/release-notes-template.md",
    "docs/docs-site.md",
    "docs/docs-navigation.md",
    "docs/quickstart-site.md",
    "docs/sandbox-read-validation.md",
    "docs/sandbox-read-evidence.md",
    "docs/sandbox-evidence-linkage.md",
    "docs/sandbox-evidence-to-pilot.md",
    "mkdocs.yml",
}
REQUIRED_SCRIPTS = {
    "scripts/check_intake_review_workspace.py",
    "scripts/print_intake_review_workspace_summary.py",
    "scripts/check_intake_lifecycle.py",
    "scripts/print_intake_lifecycle_summary.py",
    "scripts/check_operator_triage_queue.py",
    "scripts/print_operator_triage_summary.py",
    "scripts/check_attachment_review.py",
    "scripts/print_attachment_review_summary.py",
    "scripts/check_operator_export_pack.py",
    "scripts/print_operator_export_summary.py",
    "scripts/generate_operator_export_pack.py",
    "scripts/print_demo_product_tour.py",
    "scripts/check_demo_product_walkthrough.py",
    "scripts/print_demo_evaluation_checklist.py",
    "scripts/generate_demo_product_walkthrough_artifacts.py",
    "scripts/run_security_threat_model.py",
    "scripts/print_security_boundary_map.py",
    "scripts/print_security_review_checklist.py",
    "scripts/generate_security_threat_model_artifacts.py",
    "scripts/run_auth_boundary_audit.py",
    "scripts/print_auth_boundary_map.py",
    "scripts/print_permission_boundary_checklist.py",
    "scripts/generate_auth_boundary_audit_artifacts.py",
    "scripts/run_webhook_security_review.py",
    "scripts/print_webhook_signature_boundary.py",
    "scripts/print_webhook_replay_checklist.py",
    "scripts/generate_webhook_security_review_artifacts.py",
    "scripts/run_data_policy_review.py",
    "scripts/print_data_retention_map.py",
    "scripts/print_redaction_boundary_map.py",
    "scripts/print_data_handling_checklist.py",
    "scripts/generate_data_policy_review_artifacts.py",
    "scripts/run_infra_security_review.py",
    "scripts/print_secret_boundary_map.py",
    "scripts/print_storage_boundary_map.py",
    "scripts/print_database_boundary_map.py",
    "scripts/print_infra_security_checklist.py",
    "scripts/generate_infra_security_review_artifacts.py",
    "scripts/run_supply_chain_review.py",
    "scripts/print_dependency_boundary_map.py",
    "scripts/print_package_surface_map.py",
    "scripts/print_supply_chain_checklist.py",
    "scripts/generate_supply_chain_review_artifacts.py",
    "scripts/run_incident_response_review.py",
    "scripts/print_incident_runbook.py",
    "scripts/print_audit_log_boundary_map.py",
    "scripts/print_forensics_evidence_checklist.py",
    "scripts/generate_incident_response_review_artifacts.py",
    "scripts/run_final_security_review.py",
    "scripts/print_security_readiness_summary.py",
    "scripts/print_security_gap_register.py",
    "scripts/print_private_security_review_checklist.py",
    "scripts/generate_final_security_review_artifacts.py",
    "scripts/run_security_gap_closeout.py",
    "scripts/print_privacy_review_template.py",
    "scripts/print_encryption_at_rest_guidance.py",
    "scripts/print_private_security_action_register.py",
    "scripts/print_known_limitations_closeout.py",
    "scripts/generate_security_gap_closeout_artifacts.py",
    "scripts/run_setup_experience_review.py",
    "scripts/print_first_run_checklist.py",
    "scripts/print_local_installer_guide.py",
    "scripts/print_setup_troubleshooting_guide.py",
    "scripts/generate_setup_experience_artifacts.py",
    "scripts/plan_demo_seed.py",
    "scripts/seed_demo_data.py",
    "scripts/plan_demo_reset.py",
    "scripts/reset_demo_data.py",
    "scripts/check_demo_data.py",
    "scripts/generate_demo_data_experience_artifacts.py",
    "scripts/run_api_docs_review.py",
    "scripts/print_api_route_reference.py",
    "scripts/print_api_usage_examples.py",
    "scripts/print_openapi_local_guide.py",
    "scripts/generate_api_docs_artifacts.py",
    "scripts/run_hosted_ui_review.py",
    "scripts/print_hosted_ui_page_inventory.py",
    "scripts/print_hosted_ui_readiness_checklist.py",
    "scripts/print_hosted_ui_private_gates.py",
    "scripts/generate_hosted_ui_review_artifacts.py",
    "scripts/run_docs_site_polish_review.py",
    "scripts/print_docs_reader_paths.py",
    "scripts/print_docs_navigation_map.py",
    "scripts/print_docs_site_checklist.py",
    "scripts/generate_docs_site_polish_artifacts.py",
    "scripts/doctor.py",
    "scripts/setup_demo_mode.py",
    "scripts/print_usage_modes.py",
    "scripts/check_local_setup.py",
    "scripts/check_sandbox_onboarding.py",
    "scripts/check_pilot_preflight.py",
    "scripts/init_private_workspace.py",
    "scripts/print_command_guide.py",
    "scripts/print_next_steps.py",
    "scripts/onboarding_summary.py",
    "scripts/check_walkthroughs.py",
    "scripts/check_sandbox_smoke_preflight.py",
    "scripts/explain_sandbox_smoke.py",
    "scripts/print_sandbox_smoke_evidence_template.py",
    "scripts/check_release_readiness.py",
    "scripts/generate_release_readiness_artifacts.py",
    "scripts/print_release_checklist.py",
    "scripts/print_release_notes_draft.py",
    "scripts/check_docs_site.py",
    "scripts/print_docs_preview_instructions.py",
    "scripts/print_sandbox_read_plan.py",
    "scripts/check_sandbox_read_preflight.py",
    "scripts/print_sandbox_read_evidence_template.py",
    "scripts/run_sandbox_read_validation.py",
    "scripts/print_sandbox_evidence_linkage_template.py",
    "scripts/check_sandbox_evidence_linkage.py",
    "scripts/generate_sandbox_evidence_linkage_artifacts.py",
    "scripts/print_sandbox_evidence_mapping.py",
    "scripts/check_cloud_secret_provider.py",
    "scripts/print_cloud_secret_provider_template.py",
    "scripts/explain_cloud_secret_resolution.py",
    "scripts/check_cloud_storage_provider.py",
    "scripts/print_cloud_storage_provider_template.py",
    "scripts/explain_cloud_storage_operations.py",
    "scripts/check_postgres_runtime.py",
    "scripts/print_postgres_runtime_template.py",
    "scripts/plan_postgres_migration_run.py",
    "scripts/plan_postgres_backup_restore_drill.py",
    "scripts/run_postgres_connectivity_check.py",
    "scripts/run_postgres_migration_status_check.py",
    "scripts/print_hosted_deployment_template.py",
    "scripts/check_hosted_deployment_template.py",
    "scripts/generate_hosted_deployment_artifacts.py",
    "scripts/print_hosted_deployment_matrix.py",
    "scripts/print_https_webhook_template.py",
    "scripts/check_https_webhook_plan.py",
    "scripts/generate_https_webhook_artifacts.py",
    "scripts/print_webhook_ingress_matrix.py",
    "scripts/print_webhook_disable_plan.py",
    "scripts/run_final_public_readiness_audit.py",
    "scripts/print_final_public_readiness_checklist.py",
    "scripts/generate_final_public_readiness_artifacts.py",
    "scripts/print_public_repo_handoff_summary.py",
    "scripts/print_hosted_pilot_dry_run_template.py",
    "scripts/check_hosted_pilot_dry_run.py",
    "scripts/generate_hosted_pilot_dry_run_artifacts.py",
    "scripts/print_hosted_pilot_dry_run_matrix.py",
}
REQUIRED_EXAMPLES = {
    "examples/demo-flow.md",
    "examples/sandbox-pilot-flow/example_demo_flow.json",
    "examples/sandbox-pilot-flow/example_sandbox_flow.json",
    "examples/sandbox-pilot-flow/example_pilot_flow.json",
    "examples/private-workspace/example_workspace_manifest.json",
    "examples/walkthrough-output/README.md",
    "examples/walkthrough-output/demo_expected_output.md",
    "examples/walkthrough-output/sandbox_expected_output.md",
    "examples/walkthrough-output/pilot_expected_output.md",
    "examples/sandbox-evidence-linkage/example_sandbox_evidence_profile.json",
    "examples/sandbox-evidence-linkage/example_evidence_manifest_patch.md",
    "examples/cloud-secret-providers/README.md",
    "examples/cloud-secret-providers/aws_secret_refs.example.json",
    "examples/cloud-secret-providers/azure_secret_refs.example.json",
    "examples/cloud-secret-providers/gcp_secret_refs.example.json",
    "examples/cloud-storage-providers/README.md",
    "examples/cloud-storage-providers/s3_storage_refs.example.json",
    "examples/cloud-storage-providers/azure_blob_storage_refs.example.json",
    "examples/cloud-storage-providers/gcs_storage_refs.example.json",
    "examples/postgres-runtime/README.md",
    "examples/postgres-runtime/postgres_runtime_refs.example.json",
    "examples/postgres-runtime/postgres_migration_plan.example.md",
    "examples/postgres-runtime/postgres_backup_restore_plan.example.md",
    "examples/hosted-deployment-templates/README.md",
    "examples/hosted-deployment-templates/docker_vps.example.json",
    "examples/hosted-deployment-templates/managed_paas.example.json",
    "examples/hosted-deployment-templates/render_style.example.json",
    "examples/hosted-deployment-templates/railway_style.example.json",
    "examples/hosted-deployment-templates/fly_style.example.json",
    "examples/hosted-deployment-templates/generic_container_host.example.json",
    "examples/hosted-deployment-templates/aws_ecs_style.example.json",
    "examples/hosted-deployment-templates/azure_container_apps_style.example.json",
    "examples/hosted-deployment-templates/gcp_cloud_run_style.example.json",
    "examples/https-webhook-planning/README.md",
    "examples/https-webhook-planning/example_https_webhook_profile.json",
    "examples/https-webhook-planning/example_webhook_evidence_ref.md",
    "examples/https-webhook-planning/example_reverse_proxy_notes.md",
    "examples/hosted-pilot-dry-run/README.md",
    "examples/hosted-pilot-dry-run/example_hosted_pilot_dry_run_profile.json",
    "examples/hosted-pilot-dry-run/example_pilot_dry_run_evidence_map.md",
    "examples/final-public-readiness/README.md",
    "examples/final-public-readiness/example_final_readiness_summary.md",
    "examples/final-public-readiness/example_public_repo_checklist.md",
    "examples/demo-product-walkthrough/README.md",
    "examples/demo-product-walkthrough/demo_product_tour.example.md",
    "examples/demo-product-walkthrough/demo_evaluation_checklist.example.md",
    "examples/security-threat-model/README.md",
    "examples/security-threat-model/example_security_boundary_map.md",
    "examples/security-threat-model/example_security_review_checklist.md",
    "examples/auth-boundary-audit/README.md",
    "examples/auth-boundary-audit/example_auth_boundary_map.md",
    "examples/auth-boundary-audit/example_permission_boundary_checklist.md",
    "examples/auth-boundary-audit/example_route_permission_matrix.csv",
    "examples/webhook-security-review/README.md",
    "examples/webhook-security-review/example_webhook_signature_boundary.md",
    "examples/webhook-security-review/example_webhook_replay_checklist.md",
    "examples/webhook-security-review/example_webhook_fixture_matrix.csv",
    "examples/data-policy-review/README.md",
    "examples/data-policy-review/example_data_retention_map.md",
    "examples/data-policy-review/example_redaction_boundary_map.md",
    "examples/data-policy-review/example_data_handling_checklist.md",
    "examples/data-policy-review/example_generated_output_inventory.csv",
    "examples/infra-security-review/README.md",
    "examples/infra-security-review/example_secret_boundary_map.md",
    "examples/infra-security-review/example_storage_boundary_map.md",
    "examples/infra-security-review/example_database_boundary_map.md",
    "examples/infra-security-review/example_infra_security_checklist.md",
    "examples/infra-security-review/example_infra_provider_matrix.csv",
    "examples/supply-chain-review/README.md",
    "examples/supply-chain-review/example_dependency_boundary_map.md",
    "examples/supply-chain-review/example_package_surface_map.md",
    "examples/supply-chain-review/example_supply_chain_checklist.md",
    "examples/supply-chain-review/example_optional_extras_matrix.csv",
    "examples/incident-response-review/README.md",
    "examples/incident-response-review/example_incident_runbook.md",
    "examples/incident-response-review/example_audit_log_boundary_map.md",
    "examples/incident-response-review/example_forensics_evidence_checklist.md",
    "examples/incident-response-review/example_incident_scenario_matrix.csv",
    "examples/final-security-review/README.md",
    "examples/final-security-review/example_security_readiness_summary.md",
    "examples/final-security-review/example_security_gap_register.md",
    "examples/final-security-review/example_private_security_review_checklist.md",
    "examples/final-security-review/example_security_domain_matrix.csv",
    "examples/security-gap-closeout/README.md",
    "examples/security-gap-closeout/example_privacy_review_template.md",
    "examples/security-gap-closeout/example_encryption_at_rest_guidance.md",
    "examples/security-gap-closeout/example_private_security_action_register.md",
    "examples/security-gap-closeout/example_known_limitations_closeout.md",
    "examples/security-gap-closeout/example_policy_implementation_matrix.csv",
    "examples/setup-experience/README.md",
    "examples/setup-experience/example_first_run_checklist.md",
    "examples/setup-experience/example_local_installer_guide.md",
    "examples/setup-experience/example_setup_troubleshooting_guide.md",
    "examples/setup-experience/example_setup_command_map.csv",
    "examples/demo-data-experience/README.md",
    "examples/demo-data-experience/example_demo_seed_plan.md",
    "examples/demo-data-experience/example_demo_reset_plan.md",
    "examples/demo-data-experience/example_demo_data_inventory.csv",
    "examples/api-docs-review/README.md",
    "examples/api-docs-review/example_api_route_reference.md",
    "examples/api-docs-review/example_api_usage_examples.md",
    "examples/api-docs-review/example_openapi_local_guide.md",
    "examples/api-docs-review/example_api_route_matrix.csv",
    "examples/hosted-ui-review/README.md",
    "examples/hosted-ui-review/example_hosted_ui_page_inventory.md",
    "examples/hosted-ui-review/example_hosted_ui_readiness_checklist.md",
    "examples/hosted-ui-review/example_hosted_ui_private_gates.md",
    "examples/hosted-ui-review/example_hosted_ui_route_matrix.csv",
    "examples/docs-site-polish/README.md",
    "examples/docs-site-polish/example_docs_reader_paths.md",
    "examples/docs-site-polish/example_docs_navigation_map.md",
    "examples/docs-site-polish/example_docs_site_checklist.md",
    "examples/docs-site-polish/example_docs_link_inventory.csv",
}
REQUIRED_TARGETS = {
    "review-workspace-summary",
    "review-workspace-check",
    "intake-lifecycle-summary",
    "intake-lifecycle-check",
    "operator-triage-summary",
    "operator-triage-check",
    "attachment-review-summary",
    "attachment-review-check",
    "operator-export-check",
    "operator-export-summary",
    "operator-export-artifact-check",
    "product-dashboard-overview",
    "product-dashboard-check",
    "demo-product-tour",
    "demo-product-check",
    "demo-evaluation-checklist",
    "demo-product-artifact-check",
    "security-threat-model",
    "security-boundary-map",
    "security-review-checklist",
    "security-threat-model-artifact-check",
    "auth-boundary-audit",
    "auth-boundary-map",
    "permission-boundary-checklist",
    "auth-boundary-artifact-check",
    "webhook-security-review",
    "webhook-signature-boundary",
    "data-policy-review",
    "data-retention-map",
    "redaction-boundary-map",
    "data-handling-checklist",
    "data-policy-artifact-check",
    "infra-security-review",
    "secret-boundary-map",
    "storage-boundary-map",
    "database-boundary-map",
    "infra-security-checklist",
    "infra-security-artifact-check",
    "supply-chain-review",
    "dependency-boundary-map",
    "package-surface-map",
    "supply-chain-checklist",
    "supply-chain-artifact-check",
    "incident-response-review",
    "incident-runbook",
    "audit-log-boundary-map",
    "forensics-evidence-checklist",
    "incident-response-artifact-check",
    "final-security-review",
    "security-readiness-summary",
    "security-gap-register",
    "private-security-review-checklist",
    "final-security-artifact-check",
    "security-gap-closeout",
    "privacy-review-template",
    "encryption-at-rest-guidance",
    "private-security-action-register",
    "known-limitations-closeout",
    "security-gap-artifact-check",
    "setup-experience-review",
    "first-run-checklist",
    "local-installer-guide",
    "setup-troubleshooting-guide",
    "setup-experience-artifact-check",
    "demo-seed-plan",
    "demo-seed",
    "demo-reset-plan",
    "demo-reset",
    "demo-data-check",
    "demo-data-artifact-check",
    "api-docs-review",
    "api-route-reference",
    "api-usage-examples",
    "openapi-local-guide",
    "api-docs-artifact-check",
    "hosted-ui-review",
    "hosted-ui-page-inventory",
    "hosted-ui-readiness-checklist",
    "hosted-ui-private-gates",
    "hosted-ui-artifact-check",
    "docs-site-polish-review",
    "docs-reader-paths",
    "docs-navigation-map",
    "docs-site-checklist",
    "docs-site-polish-artifact-check",
    "webhook-replay-checklist",
    "webhook-security-artifact-check",
    "help",
    "start",
    "commands",
    "next",
    "try-demo",
    "prepare-sandbox",
    "prepare-pilot",
    "walkthroughs",
    "walkthroughs-check",
    "demo-walkthrough",
    "sandbox-walkthrough",
    "pilot-walkthrough",
    "sandbox-smoke-explain",
    "sandbox-smoke-preflight",
    "sandbox-smoke-evidence-template",
    "release-checklist",
    "release-readiness",
    "release-notes-draft",
    "release-readiness-artifact-check",
    "docs-site-check",
    "docs-preview-instructions",
    "docs-map",
    "sandbox-read-plan",
    "sandbox-read-preflight",
    "sandbox-read-evidence-template",
    "sandbox-read-validation",
    "sandbox-evidence-template",
    "sandbox-evidence-check",
    "sandbox-evidence-mapping",
    "sandbox-evidence-artifact-check",
    "first-run",
    "doctor",
    "setup-demo",
    "demo",
    "modes",
    "sandbox-check",
    "pilot-check",
    "init-private-workspace",
    "public-usability-audit",
    "safety-check",
    "quality",
    "cloud-secret-template",
    "cloud-secret-check",
    "cloud-secret-explain",
    "cloud-storage-template",
    "cloud-storage-check",
    "cloud-storage-explain",
    "postgres-runtime-template",
    "postgres-runtime-check",
    "postgres-migration-plan",
    "postgres-backup-restore-plan",
    "postgres-connectivity-check",
    "postgres-migration-status-check",
    "hosted-deployment-template",
    "hosted-deployment-check",
    "hosted-deployment-matrix",
    "hosted-deployment-artifact-check",
    "https-webhook-template",
    "https-webhook-check",
    "https-webhook-matrix",
    "webhook-disable-plan",
    "https-webhook-artifact-check",
    "hosted-pilot-dry-run-template",
    "hosted-pilot-dry-run-check",
    "hosted-pilot-dry-run-matrix",
    "hosted-pilot-dry-run-artifact-check",
    "final-readiness",
    "final-readiness-checklist",
    "public-handoff-summary",
    "final-readiness-artifact-check",
}
IGNORED_OUTPUTS = {
    "docs-site-polish-output/",
    "docs-site-review-output/",
    "docs-navigation-output/",
    "docs-reader-path-output/",
    "docs-link-check-output/",
    "*.docs-site-polish-report.json",
    "*.docs-site-polish-report.md",
    "*.docs-reader-paths.md",
    "*.docs-navigation-map.md",
    "*.docs-site-checklist.md",
    "*.docs-link-inventory.csv",
    "hosted-ui-review-output/",
    "hosted-ui-output/",
    "ui-readiness-output/",
    "hosted-page-review-output/",
    "*.hosted-ui-review-report.json",
    "*.hosted-ui-review-report.md",
    "*.hosted-ui-page-inventory.md",
    "*.hosted-ui-route-matrix.csv",
    "*.hosted-ui-readiness-checklist.md",
    "*.hosted-ui-private-gates.md",
    "api-docs-output/",
    "api-reference-output/",
    "route-reference-output/",
    "openapi-review-output/",
    "*.api-docs-report.json",
    "*.api-docs-report.md",
    "*.api-route-reference.md",
    "*.api-route-matrix.csv",
    "*.api-usage-examples.md",
    "*.openapi-local-guide.md",
    "demo-data-output/",
    "demo-seed-output/",
    "demo-reset-output/",
    "demo-db-output/",
    "*.demo-data-report.json",
    "*.demo-data-report.md",
    "*.demo-seed-plan.md",
    "*.demo-reset-plan.md",
    "*.demo-data-inventory.csv",
    "demo-walkthrough-output/",
    "demo-product-output/",
    "demo-tour-output/",
    "demo-evaluation-output/",
    "*.demo-walkthrough-report.json",
    "*.demo-walkthrough-report.md",
    "*.demo-product-tour.md",
    "*.demo-evaluation-checklist.md",
    "private-workspace/",
    "quickstart-output/",
    "first-run-output/",
    "usability-output/",
    "*.usability-report.json",
    "*.usability-report.md",
    "*.first-run-report.json",
    "*.first-run-report.md",
    "site/",
    "docs-site-output/",
    "mkdocs-site-output/",
    "*.docs-site-report.json",
    "*.docs-site-report.md",
    "sandbox-read-output/",
    "sandbox-validation-output/",
    "read-validation-output/",
    "*.sandbox-read-report.json",
    "*.sandbox-read-report.md",
    "*.sandbox-read-evidence.json",
    "*.sandbox-read-evidence.md",
    "*.read-validation-report.json",
    "*.read-validation-report.md",
    "sandbox-evidence-output/",
    "sandbox-evidence-linkage-output/",
    "evidence-linkage-output/",
    "*.sandbox-evidence-link.json",
    "*.sandbox-evidence-link.md",
    "*.sandbox-evidence-summary.json",
    "*.sandbox-evidence-summary.md",
    "*.sandbox-evidence-manifest.json",
    "*.sandbox-evidence-manifest.md",
    "postgres-ops-output/",
    "postgres-runtime-output/",
    "db-ops-output/",
    "migration-execution-output/",
    "backup-verification-output/",
    "restore-drill-output/",
    "*.postgres-runtime-report.json",
    "*.postgres-runtime-report.md",
    "*.postgres-ops-report.json",
    "*.postgres-ops-report.md",
    "*.migration-execution-report.json",
    "*.backup-verification-report.json",
    "*.restore-drill-report.json",
    "*.migration-log",
    "*.restore-log",
    "*.backup-log",
    "hosted-deployment-output/",
    "hosted-deploy-output/",
    "platform-deployment-output/",
    "container-deployment-output/",
    "*.hosted-deployment-report.json",
    "*.hosted-deployment-report.md",
    "*.hosted-deployment-plan.md",
    "*.platform-deployment-plan.md",
    "*.container-deployment-plan.md",
    "*.hosting-checklist.md",
    "*.hosting-runbook.md",
    "https-webhook-output/",
    "webhook-ingress-output/",
    "tls-planning-output/",
    "dns-planning-output/",
    "*.https-webhook-report.json",
    "*.https-webhook-report.md",
    "hosted-pilot-dry-run-output/",
    "pilot-dry-run-output/",
    "operations-dry-run-output/",
    "launch-rehearsal-output/",
    "*.hosted-pilot-dry-run-report.json",
    "*.hosted-pilot-dry-run-report.md",
    "*.pilot-dry-run-checklist.md",
    "*.pilot-dry-run-runbook.md",
    "*.pilot-dry-run-evidence-map.md",
    "*.pilot-dry-run-blockers.md",
    "final-readiness-output/",
    "public-readiness-output/",
    "repo-readiness-output/",
    "maintainer-handoff-output/",
    "*.final-readiness-report.json",
    "*.final-readiness-report.md",
    "*.public-readiness-report.json",
    "*.public-readiness-report.md",
    "*.maintainer-handoff.md",
    "*.public-repo-checklist.md",
    "*.final-audit-summary.md",
    "*.webhook-ingress-plan.md",
    "*.tls-plan.md",
    "*.dns-plan.md",
    "*.webhook-disable-plan.md",
    "*.webhook-rollback-plan.md",
    "*.webhook-evidence-ref.md",
    "security-threat-model-output/",
    "threat-model-output/",
    "security-review-output/",
    "security-assessment-output/",
    "*.security-threat-model-report.json",
    "*.security-threat-model-report.md",
    "*.threat-model.md",
    "*.security-boundary-map.md",
    "*.security-review-checklist.md",
    "auth-boundary-audit-output/",
    "permission-boundary-output/",
    "auth-review-output/",
    "permission-review-output/",
    "*.auth-boundary-audit-report.json",
    "*.auth-boundary-audit-report.md",
    "*.auth-boundary-map.md",
    "*.permission-boundary-checklist.md",
    "*.route-permission-matrix.csv",
    "webhook-security-review-output/",
    "webhook-hardening-output/",
    "webhook-replay-review-output/",
    "webhook-signature-review-output/",
    "*.webhook-security-review-report.json",
    "*.webhook-security-review-report.md",
    "*.webhook-signature-boundary.md",
    "*.webhook-replay-checklist.md",
    "*.webhook-fixture-matrix.csv",
    "data-policy-review-output/",
    "data-retention-redaction-output/",
    "retention-redaction-output/",
    "redaction-review-output/",
    "data-classification-output/",
    "*.data-policy-review-report.json",
    "*.data-policy-review-report.md",
    "*.data-retention-map.md",
    "*.redaction-boundary-map.md",
    "*.generated-output-inventory.csv",
    "*.data-handling-checklist.md",
    "infra-security-review-output/",
    "secrets-storage-db-review-output/",
    "secret-storage-review-output/",
    "database-security-review-output/",
    "storage-security-review-output/",
    "*.infra-security-review-report.json",
    "*.infra-security-review-report.md",
    "*.secret-boundary-map.md",
    "*.storage-boundary-map.md",
    "*.database-boundary-map.md",
    "*.infra-security-checklist.md",
    "*.infra-provider-matrix.csv",
    "supply-chain-review-output/",
    "dependency-security-output/",
    "dependency-review-output/",
    "package-security-output/",
    "sbom-review-output/",
    "*.supply-chain-review-report.json",
    "*.supply-chain-review-report.md",
    "*.dependency-boundary-map.md",
    "*.optional-extras-matrix.csv",
    "*.package-surface-map.md",
    "*.supply-chain-checklist.md",
    "incident-response-review-output/",
    "incident-review-output/",
    "forensics-review-output/",
    "audit-log-review-output/",
    "security-incident-output/",
    "*.incident-response-review-report.json",
    "*.incident-response-review-report.md",
    "*.incident-runbook.md",
    "*.audit-log-boundary-map.md",
    "*.forensics-evidence-checklist.md",
    "*.incident-scenario-matrix.csv",
    "final-security-review-output/",
    "security-readiness-output/",
    "final-security-output/",
    "private-security-review-output/",
    "security-gate-output/",
    "*.final-security-review-report.json",
    "*.final-security-review-report.md",
    "*.security-readiness-summary.md",
    "*.security-gap-register.md",
    "*.private-security-review-checklist.md",
    "*.security-domain-matrix.csv",
    "security-gap-closeout-output/",
    "security-closeout-output/",
    "privacy-review-output/",
    "encryption-guidance-output/",
    "private-security-action-output/",
    "*.security-gap-closeout-report.json",
    "*.security-gap-closeout-report.md",
    "*.privacy-review-template.md",
    "*.encryption-at-rest-guidance.md",
    "*.policy-implementation-matrix.csv",
    "*.private-security-action-register.md",
    "*.known-limitations-closeout.md",
    "setup-experience-output/",
    "installer-review-output/",
    "first-run-output/",
    "local-setup-output/",
    "setup-diagnostics-output/",
    "*.setup-experience-report.json",
    "*.setup-experience-report.md",
    "*.first-run-checklist.md",
    "*.local-installer-guide.md",
    "*.setup-troubleshooting-guide.md",
    "*.setup-command-map.csv",
}
GENERATED_PARTS = {
    "private-workspace",
    "quickstart-output",
    "first-run-output",
    "usability-output",
    "sandbox-output",
    "pilot-output",
    "smoke-output",
    "support-output",
    "site",
    "docs-site-output",
    "mkdocs-site-output",
    "sandbox-read-output",
    "sandbox-validation-output",
    "read-validation-output",
    "sandbox-evidence-output",
    "sandbox-evidence-linkage-output",
    "evidence-linkage-output",
    "postgres-ops-output",
    "postgres-runtime-output",
    "db-ops-output",
    "migration-execution-output",
    "backup-verification-output",
    "restore-drill-output",
    "hosted-deployment-output",
    "hosted-deploy-output",
    "platform-deployment-output",
    "container-deployment-output",
    "https-webhook-output",
    "hosted-pilot-dry-run-output",
    "pilot-dry-run-output",
    "operations-dry-run-output",
    "launch-rehearsal-output",
    "final-readiness-output",
    "public-readiness-output",
    "repo-readiness-output",
    "maintainer-handoff-output",
    "webhook-ingress-output",
    "tls-planning-output",
    "dns-planning-output",
    "security-threat-model-output",
    "threat-model-output",
    "security-review-output",
    "security-assessment-output",
    "auth-boundary-audit-output",
    "permission-boundary-output",
    "auth-review-output",
    "permission-review-output",
    "webhook-security-review-output",
    "webhook-hardening-output",
    "webhook-replay-review-output",
    "webhook-signature-review-output",
    "data-policy-review-output",
    "data-retention-redaction-output",
    "retention-redaction-output",
    "redaction-review-output",
    "data-classification-output",
    "infra-security-review-output",
    "secrets-storage-db-review-output",
    "secret-storage-review-output",
    "database-security-review-output",
    "storage-security-review-output",
    "supply-chain-review-output",
    "dependency-security-output",
    "dependency-review-output",
    "package-security-output",
    "sbom-review-output",
    "incident-response-review-output",
    "incident-review-output",
    "forensics-review-output",
    "audit-log-review-output",
    "security-incident-output",
    "final-security-review-output",
    "security-readiness-output",
    "final-security-output",
    "private-security-review-output",
    "security-gate-output",
    "security-gap-closeout-output",
    "security-closeout-output",
    "privacy-review-output",
    "encryption-guidance-output",
    "private-security-action-output",
    "setup-experience-output",
    "installer-review-output",
    "local-setup-output",
    "setup-diagnostics-output",
    "demo-data-output",
    "demo-seed-output",
    "demo-reset-output",
    "demo-db-output",
    "api-docs-output",
    "api-reference-output",
    "route-reference-output",
    "openapi-review-output",
    "hosted-ui-review-output",
    "hosted-ui-output",
    "ui-readiness-output",
    "hosted-page-review-output",
    "docs-site-polish-output",
    "docs-site-review-output",
    "docs-navigation-output",
    "docs-reader-path-output",
    "docs-link-check-output",
}
UNSAFE_SUFFIXES = {
    ".bak",
    ".backup",
    ".crt",
    ".csr",
    ".db",
    ".docx",
    ".dump",
    ".gif",
    ".jpeg",
    ".jpg",
    ".key",
    ".log",
    ".p12",
    ".pdf",
    ".pem",
    ".pfx",
    ".png",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".webp",
    ".xlsx",
    ".zip",
}
UNSAFE_TEXT = re.compile(
    r"(?i)(?:"
    r"(?:client_secret|admin_token|webhook_secret|app_version_key)\s*[:=]\s*['\"]?(?!"
    r"(?:replace|example|fake|placeholder|synthetic|test|\$\{))[^'\"\s]+|"
    r"(?:postgres(?:ql)?|mysql|mariadb)://[^/\s:]+:[^@\s]+@|"
    r"https?://[^\s\"']+[?&](?:signature|signed|token|expires)=|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"(?:/Users/|/home/[^/\s]+/|[A-Z]:\\Users\\)"
    r")"
)


def _read(root: Path, name: str) -> str:
    try:
        return (root / name).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _tracked_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        return []
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def audit_repository(root: Path, tracked_files: list[str] | None = None) -> list[Finding]:
    """Return sanitized findings; messages never contain file contents or absolute paths."""
    findings: list[Finding] = []

    def add(level: str, check: str, message: str) -> None:
        findings.append(Finding(level, check, message))

    readme = _read(root, "README.md").casefold()
    quickstart = _read(root, "QUICKSTART.md").casefold()
    makefile = _read(root, "Makefile")
    gitignore = _read(root, ".gitignore")

    readme_checks = {
        "three modes near the README top": all(
            term in readme[:5000] for term in ("demo mode", "sandbox mode", "pilot mode")
        ),
        "README quick-start path": "quickstart.md" in readme and "quick start" in readme,
        "Demo credential-free boundary": all(
            term in readme for term in ("no procore", "credentials")
        ),
        "Sandbox private DMSA boundary": "private dmsa" in readme,
        "Pilot private approval boundary": all(
            term in readme for term in ("private workspace", "evidence", "approval")
        ),
        "README mode documentation links": all(
            link in readme
            for link in (
                "docs/usage-modes.md",
                "docs/quickstart-demo.md",
                "docs/sandbox-mode.md",
                "docs/pilot-mode.md",
            )
        ),
        "README operations links": all(
            link in readme
            for link in (
                "docs/secret-providers.md",
                "docs/storage-providers.md",
                "docs/database-providers.md",
                "docs/deployment-recipes.md",
                "docs/private-workspace-bootstrap.md",
            )
        ),
        "README commit safety": "must not be" in readme and "committed" in readme,
        "README friendly commands": all(
            command in readme
            for command in (
                "make start",
                "make try-demo",
                "make prepare-sandbox",
                "make prepare-pilot",
            )
        ),
        "README walkthrough link": "docs/walkthrough-index.md" in readme,
        "README docs-site link": "docs/docs-site.md" in readme,
    }
    for name, passed in readme_checks.items():
        add(
            "PASS" if passed else "FAIL",
            name,
            "clear and discoverable" if passed else "required public guidance is missing",
        )

    for path in sorted(REQUIRED_DOCS | REQUIRED_SCRIPTS | REQUIRED_EXAMPLES):
        exists = (root / path).is_file()
        add(
            "PASS" if exists else "FAIL",
            f"required file: {path}",
            "present" if exists else "missing",
        )

    targets = set(re.findall(r"(?m)^([a-zA-Z0-9_.-]+):(?:\s|$)", makefile))
    for target in sorted(REQUIRED_TARGETS):
        present = target in targets
        add(
            "PASS" if present else "FAIL",
            f"Make target: {target}",
            "present" if present else "missing",
        )

    for pattern in sorted(IGNORED_OUTPUTS):
        ignored = pattern in gitignore
        add(
            "PASS" if ignored else "FAIL",
            f"ignored output: {pattern}",
            "covered" if ignored else "missing from .gitignore",
        )

    docs = "\n".join(
        _read(root, path).casefold() for path in REQUIRED_DOCS if (root / path).is_file()
    )
    quality_header = next(
        (line for line in makefile.splitlines() if line.startswith("quality:")),
        "",
    )
    quality_headers = " ".join(
        line for line in makefile.splitlines() if line.startswith("quality:")
    )
    setup_review = _read(root, "docs/setup-experience-review.md").casefold()
    prepare_sandbox_header = next(
        (line for line in makefile.splitlines() if line.startswith("prepare-sandbox:")),
        "",
    )
    guidance_checks = {
        "docs include next-command guidance": "what to run next" in docs,
        "doctor is documented": "make doctor" in docs,
        "Demo is the safe default": "default safe" in docs or "safe default" in docs,
        "Sandbox is operator-controlled": "operator-controlled" in docs,
        "Pilot is operator-controlled": (
            "pilot mode is private" in docs or "pilot is private" in docs
        ),
        "quickstart offers all three paths": all(
            term in quickstart for term in ("demo mode", "sandbox mode", "pilot mode")
        ),
        "quickstart uses friendly commands": all(
            command in quickstart
            for command in (
                "make start",
                "make try-demo",
                "make prepare-sandbox",
                "make prepare-pilot",
            )
        ),
        "command reference marks difficulty": all(
            term in _read(root, "docs/command-reference.md").casefold()
            for term in ("beginner", "intermediate", "advanced")
        ),
        "command reference marks safety": all(
            term in _read(root, "docs/command-reference.md").casefold()
            for term in ("procore", "external", "private config", "demo-safe")
        ),
        "cloud providers are optional and disabled": all(
            term in _read(root, "docs/cloud-secret-providers.md").casefold()
            for term in ("optional", "disabled by default")
        ),
        "cloud checks are offline by default": all(
            term in _read(root, "docs/cloud-secret-providers.md").casefold()
            for term in ("never contact cloud", "env", "file")
        ),
        "cloud readiness is not security approval": (
            "not production security approval"
            in _read(root, "docs/cloud-secret-providers.md").casefold()
        ),
        "cloud storage is optional and disabled": all(
            term in _read(root, "docs/cloud-storage-providers.md").casefold()
            for term in ("optional", "disabled by default", "local provider first")
        ),
        "cloud storage checks are offline": (
            "never contact cloud" in _read(root, "docs/cloud-storage-providers.md").casefold()
        ),
        "cloud storage excludes presigned URLs": (
            "no presigned url" in _read(root, "docs/cloud-storage-providers.md").casefold()
        ),
        "Postgres runtime checks are offline by default": all(
            phrase in _read(root, "docs/postgres-runtime-operations.md").casefold()
            for phrase in ("does not resolve", "connect", "disabled by")
        ),
        "Postgres live checks are manually gated": (
            "manually gated" in _read(root, "docs/postgres-runtime-operations.md").casefold()
        ),
        "Postgres migration plan executes nothing": (
            "does not resolve a database secret"
            in _read(root, "docs/postgres-migration-runbook.md").casefold()
            and "does not" in _read(root, "docs/postgres-migration-runbook.md").casefold()
            and "alembic upgrade or downgrade"
            in _read(root, "docs/postgres-migration-runbook.md").casefold()
        ),
        "Postgres recovery plan inspects no dumps": (
            "inspect dump or backup files"
            in _read(root, "docs/postgres-backup-restore-drills.md").casefold()
        ),
        "Postgres live targets excluded from quality": all(
            target not in quality_header
            for target in ("postgres-connectivity-check", "postgres-migration-status-check")
        ),
        "hosted templates are non-deploying placeholders": all(
            phrase in _read(root, "docs/hosted-deployment-templates.md").casefold()
            for phrase in (
                "placeholder-only",
                "not deployment automation",
                "no cloud",
                "outside git",
            )
        ),
        "hosted templates exclude active infrastructure automation": all(
            phrase in _read(root, "docs/hosted-deployment-templates.md").casefold()
            for phrase in ("no github actions", "terraform", "kubernetes", "helm")
        ),
        "hosted artifact generation excluded from quality": (
            "hosted-deployment-artifact-check" not in quality_header
        ),
        "HTTPS webhook planning makes no live calls": all(
            phrase in _read(root, "docs/https-webhook-production-planning.md").casefold()
            for phrase in (
                "no dns",
                "acme",
                "public url",
                "procore",
                "registration call",
                "generates no certificate",
            )
        ),
        "HTTPS webhook examples and evidence remain private": all(
            phrase in _read(root, "docs/https-webhook-production-planning.md").casefold()
            for phrase in ("outside git", "evidence", "private", "not proof")
        ),
        "HTTPS webhook disable and rollback are required": (
            "required before pilot" in _read(root, "docs/webhook-disable-rollback.md").casefold()
        ),
        "HTTPS webhook artifact generation excluded from quality": (
            "https-webhook-artifact-check" not in quality_header
        ),
        "hosted pilot dry run is not approval or launch": all(
            phrase in _read(root, "docs/hosted-pilot-dry-run.md").casefold()
            for phrase in ("not a launch", "not pilot approval", "human")
        ),
        "hosted pilot dry run performs no live operations": (
            "no live operation" in _read(root, "docs/hosted-pilot-dry-run.md").casefold()
        ),
        "hosted pilot dry run reads refs only": all(
            phrase in _read(root, "docs/hosted-pilot-dry-run.md").casefold()
            for phrase in ("placeholder reference", "does not read private reports")
        ),
        "hosted pilot artifact generation excluded from quality": (
            "hosted-pilot-dry-run-artifact-check" not in quality_header
        ),
        "final readiness is maintainer review only": all(
            phrase in _read(root, "docs/final-public-readiness.md").casefold()
            for phrase in (
                "maintainer-review aid",
                "not release approval",
                "not production approval",
                "not pilot approval",
            )
        ),
        "final readiness performs no live operations": (
            "no live operation" in _read(root, "docs/final-public-readiness.md").casefold()
        ),
        "final readiness keeps private values outside Git": all(
            phrase in _read(root, "docs/final-public-readiness.md").casefold()
            for phrase in ("private values", "real reports", "outside git")
        ),
        "final readiness artifact generation excluded from quality": (
            "final-readiness-artifact-check" not in quality_header
        ),
        "I1 threat model is offline review input": all(
            phrase in _read(root, "docs/security-threat-model.md").casefold()
            for phrase in ("offline", "no live", "does not provide", "certification")
        ),
        "I1 threat model keeps private material out": all(
            phrase in _read(root, "docs/security-threat-model.md").casefold()
            for phrase in ("private", "credentials", "public-safe")
        ),
        "I1 artifact generation excluded from quality": (
            "security-threat-model-artifact-check" not in quality_header
        ),
        "I2 auth audit is offline and adds no provider": all(
            phrase in _read(root, "docs/auth-permission-boundary-audit.md").casefold()
            for phrase in (
                "offline",
                "no live permission check",
                "no authentication provider",
                "sso",
                "oauth",
                "rbac",
            )
        ),
        "I2 auth audit disclaims certification and approval": all(
            phrase in _read(root, "docs/auth-permission-boundary-audit.md").casefold()
            for phrase in ("not production approval", "security certification", "pilot approval")
        ),
        "I2 artifact generation excluded from quality": (
            "auth-boundary-artifact-check" not in quality_header
        ),
        "I3 webhook review is offline and non-registering": all(
            phrase in _read(root, "docs/webhook-replay-signature-hardening.md").casefold()
            for phrase in (
                "offline webhook security review",
                "no live webhook replay",
                "no webhook registration",
                "no procore call",
                "no external call",
            )
        ),
        "I3 webhook review disclaims certification and approval": all(
            phrase in _read(root, "docs/webhook-replay-signature-hardening.md").casefold()
            for phrase in ("not production approval", "security certification", "pilot approval")
        ),
        "I3 artifact generation excluded from quality": (
            "webhook-security-artifact-check" not in quality_header
        ),
        "I4 data policy is offline and non-destructive": all(
            phrase in _read(root, "docs/data-retention-redaction-policy.md").casefold()
            for phrase in (
                "offline data policy/redaction review",
                "no live scan",
                "no destructive deletion",
                "no purge jobs",
                "no external call",
                "procore call",
            )
        ),
        "I4 disclaims legal certification and approval": all(
            phrase in _read(root, "docs/data-retention-redaction-policy.md").casefold()
            for phrase in (
                "not legal compliance certification",
                "no production",
                "hosted-pilot",
                "security approval",
            )
        ),
        "I4 checks are included and artifact generation is excluded": (
            "quality: data-policy-review data-retention-map redaction-boundary-map "
            "data-handling-checklist"
            in makefile
            and "quality: data-policy-artifact-check" not in makefile
        ),
        "I5 infrastructure review is offline and non-operational": all(
            phrase in _read(root, "docs/secrets-storage-db-security-review.md").casefold()
            for phrase in (
                "offline secrets/storage/db security review",
                "no secret retrieval",
                "no storage access",
                "no database connection",
                "no migration",
                "no backup",
                "no restore",
                "no db dump inspection",
                "no external call",
                "no procore call",
            )
        ),
        "I5 infrastructure review disclaims certification and approval": all(
            phrase in _read(root, "docs/secrets-storage-db-security-review.md").casefold()
            for phrase in (
                "not legal",
                "security",
                "compliance certification",
                "no production",
                "pilot approval",
            )
        ),
        "I5 checks are included and artifacts excluded": (
            "quality: infra-security-review secret-boundary-map storage-boundary-map "
            "database-boundary-map infra-security-checklist"
            in makefile
            and "quality: infra-security-artifact-check" not in makefile
        ),
        "I6 review is offline without automation": all(
            phrase in _read(root, "docs/dependency-supply-chain-security.md").casefold()
            for phrase in (
                "offline only",
                "no scanners",
                "package audit",
                "github api",
                "dependency bots",
                "workflow changes",
                "publishing",
                "docker builds",
                "releases",
                "deployment",
            )
        ),
        "I6 disclaims certification and approval": all(
            phrase in _read(root, "docs/dependency-supply-chain-security.md").casefold()
            for phrase in ("not slsa", "sbom", "certification", "no production", "pilot approval")
        ),
        "I6 checks included and artifacts excluded": (
            "quality: supply-chain-review dependency-boundary-map package-surface-map "
            "supply-chain-checklist"
            in makefile
            and "quality: supply-chain-artifact-check" not in makefile
        ),
        "I7 review is offline and non-operational": all(
            phrase in _read(root, "docs/incident-response-forensics.md").casefold()
            for phrase in (
                "offline incident-response/forensics readiness review",
                "no live incident response",
                "notification",
                "siem",
                "log collection",
                "evidence collection",
                "packet capture",
                "forensics tooling",
                "deletion",
                "purge",
                "no procore",
            )
        ),
        "I7 disclaims legal certification and approval": all(
            phrase in _read(root, "docs/incident-response-forensics.md").casefold()
            for phrase in (
                "not legal compliance",
                "breach readiness certification",
                "security certification",
                "production approval",
            )
        ),
        "I7 checks included and artifacts excluded": (
            "quality: incident-response-review incident-runbook audit-log-boundary-map "
            "forensics-evidence-checklist"
            in makefile
            and "quality: incident-response-artifact-check" not in makefile
        ),
        "I8 review is offline and aggregates I1-I7": all(
            phrase in _read(root, "docs/final-security-readiness-review.md").casefold()
            for phrase in (
                "offline",
                "i1",
                "i7",
                "live security scanner",
                "no external call",
                "procore call",
            )
        ),
        "I8 grants no approval or certification": all(
            phrase in _read(root, "docs/final-security-readiness-review.md").casefold()
            for phrase in (
                "grants no",
                "production",
                "pilot",
                "release",
                "claims no",
                "security",
                "certification",
                "private security review",
            )
        ),
        "I8 checks included and artifacts excluded": (
            "quality: final-security-review security-readiness-summary security-gap-register "
            "private-security-review-checklist"
            in makefile
            and "quality: final-security-artifact-check" not in makefile
        ),
        "I9 closeout is offline and non-operational": all(
            phrase in _read(root, "docs/security-gap-closeout.md").casefold()
            for phrase in (
                "offline",
                "no live scanner",
                "no external call",
                "no procore call",
                "no encryption implementation",
                "no retention enforcement",
                "no notifications",
            )
        ),
        "I9 disclaims compliance certification and approval": all(
            phrase in _read(root, "docs/security-gap-closeout.md").casefold()
            for phrase in (
                "no compliance claims",
                "no approval claims",
                "no certification claims",
                "maintainer/legal review aid",
                "private security",
            )
        ),
        "I9 checks included and artifacts excluded": (
            all(
                target
                in " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
                for target in (
                    "security-gap-closeout",
                    "privacy-review-template",
                    "encryption-at-rest-guidance",
                    "private-security-action-register",
                    "known-limitations-closeout",
                )
            )
            and "security-gap-artifact-check"
            not in " ".join(line for line in makefile.splitlines() if line.startswith("quality:"))
        ),
        "J1 setup guidance is local and Demo-safe": (
            all(phrase in setup_review for phrase in ("local", "demo mode", "secrets"))
            and any(
                phrase in setup_review
                for phrase in ("no secrets", "requires no", "does not require")
            )
            and any(phrase in setup_review for phrase in ("no deploy", "does not deploy"))
            and any(phrase in setup_review for phrase in ("no release", "does not release"))
            and "production approval" in setup_review
            and any(phrase in setup_review for phrase in ("no production", "not production"))
        ),
        "J1 separates gated setup paths": all(
            phrase in docs for phrase in ("sandbox", "pilot", "hosted", "gated")
        ),
        "J1 documents prerequisite troubleshooting": all(
            phrase in _read(root, "docs/setup-troubleshooting-guide.md").casefold()
            for phrase in ("path", "git", "python", "pip", "make")
        ),
        "J1 checks included and artifacts excluded": (
            all(
                target in quality_headers
                for target in (
                    "setup-experience-review",
                    "first-run-checklist",
                    "local-installer-guide",
                    "setup-troubleshooting-guide",
                )
            )
            and "setup-experience-artifact-check" not in quality_headers
        ),
        "J2 demo data is fake-only and local-only": all(
            phrase in _read(root, "docs/demo-data-seed-reset.md").casefold()
            for phrase in ("fake", "local", "sqlite", "procore", "cloud", "external database")
        ),
        "J2 reset is confirmed and demo-scoped": all(
            phrase in _read(root, "docs/demo-reset-guide.md").casefold()
            for phrase in (
                "reset demo data",
                "confirmation",
                "demo marker",
                "private workspace",
                "sandbox",
                "pilot",
                "hosted",
                "customer data",
            )
        ),
        "J2 friendly demo path is non-destructive": (
            "try-demo:" in makefile
            and "demo-reset"
            not in next(
                (line for line in makefile.splitlines() if line.startswith("try-demo:")), ""
            )
        ),
        "J2 quality excludes destructive reset": "demo-reset"
        not in quality_headers.replace("demo-reset-plan", ""),
        "J3 API docs are local-only and non-approving": all(
            phrase in _read(root, "docs/api-docs-review.md").casefold()
            for phrase in (
                "local-only",
                "no live api calls",
                "no external openapi tooling",
                "production approval",
            )
        ),
        "J3 documents route safety boundaries": all(
            phrase in _read(root, "docs/api-route-reference.md").casefold()
            for phrase in (
                "webhook",
                "signature",
                "lifecycle",
                "local-only",
                "export download",
                "file-serving",
                "procore write",
            )
        ),
        "J3 checks included and artifacts excluded": (
            all(
                target in quality_headers
                for target in (
                    "api-docs-review",
                    "api-route-reference",
                    "api-usage-examples",
                    "openapi-local-guide",
                )
            )
            and "api-docs-artifact-check" not in quality_headers
        ),
        "J4 hosted UI prep is offline and non-approving": all(
            phrase in _read(root, "docs/hosted-ui-preparation.md").casefold()
            for phrase in (
                "no hosted deployment",
                "no external",
                "no frontend",
                "production approval",
                "private",
            )
        ),
        "J4 preserves metadata and command-only boundaries": all(
            phrase in _read(root, "docs/hosted-ui-preparation.md").casefold()
            for phrase in ("metadata-only", "command-only", "no public", "download")
        ),
        "J4 checks included and artifacts excluded": (
            all(
                target in quality_headers
                for target in (
                    "hosted-ui-review",
                    "hosted-ui-page-inventory",
                    "hosted-ui-readiness-checklist",
                    "hosted-ui-private-gates",
                )
            )
            and "hosted-ui-artifact-check" not in quality_headers
        ),
        "J5 docs-site polish is local-only and non-approving": all(
            phrase in _read(root, "docs/docs-site-polish.md").casefold()
            for phrase in (
                "local-only",
                "no docs deployment",
                "no external",
                "production approval",
            )
        ),
        "J5 reader paths cover core audiences": all(
            phrase in _read(root, "docs/docs-reader-paths.md").casefold()
            for phrase in ("evaluator", "demo", "sandbox", "pilot", "hosted", "security")
        ),
        "J5 checks included and artifacts excluded": (
            all(
                target in quality_headers
                for target in (
                    "docs-site-polish-review",
                    "docs-reader-paths",
                    "docs-navigation-map",
                    "docs-site-checklist",
                )
            )
            and "docs-site-polish-artifact-check" not in quality_headers
        ),
        "H3 workspace is read-only and local": all(
            phrase in _read(root, "docs/intake-review-workspace.md").casefold()
            for phrase in ("read-only", "local intake records only", "no procore")
        ),
        "H3 workspace has no lifecycle transitions": (
            "does not add lifecycle transitions"
            in _read(root, "docs/intake-review-workspace.md").casefold()
        ),
        "H3 workspace excludes raw payloads and attachment contents": all(
            phrase in _read(root, "docs/intake-review-workspace.md").casefold()
            for phrase in ("raw procore payloads", "attachment contents")
        ),
        "H3 checks are included in quality": all(
            target in makefile
            for target in ("quality: review-workspace-check review-workspace-summary",)
        ),
        "H4 lifecycle is audited local-only state": all(
            phrase in _read(root, "docs/intake-lifecycle-status-flow.md").casefold()
            for phrase in ("local labels only", "audit event", "do not update procore")
        ),
        "H4 lifecycle disclaims approval compliance and communication": all(
            phrase in _read(root, "docs/intake-lifecycle-status-flow.md").casefold()
            for phrase in ("approval", "compliance determination", "communicate")
        ),
        "H4 lifecycle reasons and notes are bounded": all(
            phrase in _read(root, "docs/intake-lifecycle-status-flow.md").casefold()
            for phrase in ("reason codes are fixed", "bounded", "disabled by default")
        ),
        "H4 checks are included in quality": (
            "quality: intake-lifecycle-check intake-lifecycle-summary" in makefile
        ),
        "H5 triage is GET-only local sorting": all(
            phrase in _read(root, "docs/operator-triage-queue.md").casefold()
            for phrase in ("get-only", "sorting helper only", "no procore")
        ),
        "H5 triage excludes private source and attachment content": all(
            phrase in _read(root, "docs/operator-triage-queue.md").casefold()
            for phrase in ("raw payloads", "signed urls", "attachment content")
        ),
        "H5 checks are included in quality": (
            "quality: operator-triage-check operator-triage-summary" in makefile
        ),
        "H6 attachment review is metadata-only": all(
            phrase in _read(root, "docs/attachment-review-manifest-ux.md").casefold()
            for phrase in ("metadata-only", "no procore", "no file")
        ),
        "H6 attachment review excludes private file details": all(
            phrase in _read(root, "docs/attachment-review-manifest-ux.md").casefold()
            for phrase in (
                "signed urls",
                "private paths",
                "storage keys",
                "original live filenames",
                "contents",
            )
        ),
        "H6 checks are included in quality": (
            "quality: attachment-review-check attachment-review-summary" in makefile
        ),
        "H7 exports are local sanitized summaries": all(
            phrase in _read(root, "docs/operator-export-pack.md").casefold()
            for phrase in ("local sanitized", "no public export route", "outside version control")
        ),
        "H7 exports disclaim external report claims": all(
            phrase in _read(root, "docs/operator-export-pack.md").casefold()
            for phrase in ("not compliance reports", "approvals", "customer reports")
        ),
        "H7 export outputs are ignored": all(
            pattern in _read(root, ".gitignore")
            for pattern in (
                "operator-export-output/",
                "*.operator-export.json",
                "*.operator-export.md",
                "*.operator-export.csv",
                "*.attachment-summary-export.csv",
            )
        ),
        "H7 non-writing checks are included in quality": (
            "quality: operator-export-check operator-export-summary" in makefile
            and "operator-export-artifact-check" not in quality_header
        ),
        "H8 dashboard is local and read-oriented": all(
            phrase in _read(root, "docs/product-dashboard.md").casefold()
            for phrase in ("local", "read-oriented", "procore calls or writes")
        ),
        "H8 dashboard excludes downloads and private content": all(
            phrase in _read(root, "docs/product-dashboard.md").casefold()
            for phrase in ("export", "download", "attachment contents", "private paths")
        ),
        "H8 dashboard disclaims decisions": all(
            phrase in _read(root, "docs/product-dashboard.md").casefold()
            for phrase in (
                "release",
                "production",
                "pilot authorization",
                "compliance determination",
                "customer",
                "report",
            )
        ),
        "H8 non-writing checks are included in quality": (
            "quality: product-dashboard-check product-dashboard-overview" in makefile
        ),
        "H9 walkthrough is fake-data-only and offline": all(
            phrase in _read(root, "docs/demo-product-walkthrough.md").casefold()
            for phrase in ("fake data", "no procore call", "no live", "private report")
        ),
        "H9 walkthrough disclaims external decisions": all(
            phrase in _read(root, "docs/demo-product-walkthrough.md").casefold()
            for phrase in (
                "production readiness",
                "pilot authorization",
                "compliance",
                "customer reporting",
            )
        ),
        "H9 non-writing checks are included in quality": (
            "quality: demo-product-check demo-product-tour demo-evaluation-checklist" in makefile
            and "demo-product-artifact-check" not in quality_header
        ),
        "beginner docs steer to friendly targets": all(
            command in docs
            for command in (
                "make start",
                "make try-demo",
                "make prepare-sandbox",
                "make prepare-pilot",
            )
        ),
        "live smoke is not a beginner default": (
            "make start" in quickstart and "run_sandbox_dmsa_smoke.py" not in quickstart
        ),
        "deployment is not a beginner default": (
            "make start" in quickstart and "make deployment-check" not in quickstart
        ),
        "QUICKSTART walkthrough link": "docs/walkthrough-index.md" in quickstart,
        "docs index walkthrough link": (
            "walkthrough-index.md" in _read(root, "docs/index.md").casefold()
        ),
        "command reference walkthrough links": all(
            name in _read(root, "docs/command-reference.md").casefold()
            for name in (
                "walkthrough-demo.md",
                "walkthrough-sandbox.md",
                "walkthrough-pilot.md",
            )
        ),
        "walkthroughs use friendly commands": all(
            command
            in "\n".join(
                _read(root, path).casefold()
                for path in (
                    "docs/walkthrough-demo.md",
                    "docs/walkthrough-sandbox.md",
                    "docs/walkthrough-pilot.md",
                )
            )
            for command in (
                "make start",
                "make try-demo",
                "make prepare-sandbox",
                "make prepare-pilot",
            )
        ),
        "walkthroughs avoid live/deploy defaults": (
            "do not run it as part of this walkthrough"
            in _read(root, "docs/walkthrough-sandbox.md").casefold()
            and "launch hold" in _read(root, "docs/walkthrough-pilot.md").casefold()
        ),
        "prepare-sandbox remains offline": (
            "offline planning" in _read(root, "docs/sandbox-smoke-ux.md").casefold()
            and "never invokes the live command"
            in _read(root, "docs/sandbox-smoke-ux.md").casefold()
        ),
        "live smoke remains manually gated": (
            "manual live read-only execution" in _read(root, "docs/sandbox-smoke-ux.md").casefold()
        ),
        "smoke evidence refs remain private": (
            "outside git" in _read(root, "docs/sandbox-smoke-evidence.md").casefold()
            and "report nor its contents"
            in _read(root, "docs/sandbox-smoke-evidence.md").casefold()
        ),
        "live smoke absent from first-run defaults": (
            "run_sandbox_dmsa_smoke.py" not in quickstart
            and "run_sandbox_dmsa_smoke.py" not in _read(root, "docs/walkthrough-demo.md")
        ),
        "release readiness does not publish": all(
            phrase in _read(root, "docs/release-readiness.md").casefold()
            for phrase in ("does not publish", "create a release or tag", "build a package")
        ),
        "release readiness requires maintainer review": (
            all(
                term in _read(root, "docs/release-readiness.md").casefold()
                for term in ("not final", "release approval")
            )
            and "maintainer" in _read(root, "docs/release-checklist.md").casefold()
        ),
        "QUICKSTART docs-site link": "docs/docs-site.md" in quickstart,
        "docs index docs-site link": ("docs-site.md" in _read(root, "docs/index.md").casefold()),
        "docs site is local-only and unpublished": all(
            phrase in _read(root, "docs/docs-site.md").casefold()
            for phrase in ("local-only", "not published", "no github pages automation")
        ),
        "MkDocs is optional for Demo Mode": all(
            phrase in _read(root, "docs/docs-site.md").casefold()
            for phrase in ("mkdocs is optional", "not required for demo mode")
        ),
        "docs do not activate GitHub Pages": (
            "mkdocs gh-deploy" not in docs and "github pages is enabled" not in docs
        ),
        "Sandbox read validation is manually gated": all(
            phrase in _read(root, "docs/sandbox-read-validation.md").casefold()
            for phrase in (
                "separately gated",
                "exactly equals",
                "never automatic",
                "never part of quality",
            )
        ),
        "Sandbox read validation is read-only and private": all(
            phrase in _read(root, "docs/sandbox-read-validation.md").casefold()
            for phrase in (
                "does not write to procore",
                "register webhooks",
                "download attachments by default",
                "store raw payloads",
                "stay private",
            )
        ),
        "Sandbox read live target excluded from defaults": all(
            "sandbox-read-validation" not in section
            for section in (
                quality_header,
                prepare_sandbox_header,
            )
        ),
        "Sandbox evidence linkage is reference-only": all(
            phrase in _read(root, "docs/sandbox-evidence-linkage.md").casefold()
            for phrase in (
                "opaque references",
                "does not read source report contents by default",
                "does not prove",
                "human evidence review",
            )
        ),
        "Sandbox evidence linkage maps without approval": all(
            phrase in _read(root, "docs/sandbox-evidence-to-pilot.md").casefold()
            for phrase in (
                "c1 private evidence manifest",
                "c2 review and expiry",
                "b9 pilot readiness",
                "c3 pilot approval packet",
                "d5 sandbox-to-pilot flow",
                "does not mean a pilot is approved",
            )
        ),
    }
    for name, passed in guidance_checks.items():
        add("PASS" if passed else "FAIL", name, "documented" if passed else "guidance is missing")

    tracked = _tracked_files(root) if tracked_files is None else tracked_files
    for relative in tracked:
        path = Path(relative)
        lowered_parts = {part.casefold() for part in path.parts}
        generated = lowered_parts & GENERATED_PARTS
        public_fake_example = path.parts[:2] == ("examples", "private-workspace")
        if (generated and not public_fake_example) or path.name.endswith(
            (
                ".usability-report.json",
                ".usability-report.md",
                ".first-run-report.json",
                ".first-run-report.md",
                ".docs-site-report.json",
                ".docs-site-report.md",
                ".sandbox-read-report.json",
                ".sandbox-read-report.md",
                ".sandbox-read-evidence.json",
                ".sandbox-read-evidence.md",
                ".read-validation-report.json",
                ".read-validation-report.md",
                ".sandbox-evidence-link.json",
                ".sandbox-evidence-link.md",
                ".sandbox-evidence-summary.json",
                ".sandbox-evidence-summary.md",
                ".sandbox-evidence-manifest.json",
                ".sandbox-evidence-manifest.md",
                ".auth-boundary-audit-report.json",
                ".auth-boundary-audit-report.md",
                ".auth-boundary-map.md",
                ".permission-boundary-checklist.md",
                ".route-permission-matrix.csv",
                ".webhook-security-review-report.json",
                ".webhook-security-review-report.md",
                ".webhook-signature-boundary.md",
                ".webhook-replay-checklist.md",
                ".webhook-fixture-matrix.csv",
                ".data-policy-review-report.json",
                ".data-policy-review-report.md",
                ".data-retention-map.md",
                ".redaction-boundary-map.md",
                ".generated-output-inventory.csv",
                ".data-handling-checklist.md",
                ".infra-security-review-report.json",
                ".infra-security-review-report.md",
                ".secret-boundary-map.md",
                ".storage-boundary-map.md",
                ".database-boundary-map.md",
                ".infra-security-checklist.md",
                ".infra-provider-matrix.csv",
                ".supply-chain-review-report.json",
                ".supply-chain-review-report.md",
                ".dependency-boundary-map.md",
                ".optional-extras-matrix.csv",
                ".package-surface-map.md",
                ".supply-chain-checklist.md",
                ".incident-response-review-report.json",
                ".incident-response-review-report.md",
                ".incident-runbook.md",
                ".audit-log-boundary-map.md",
                ".forensics-evidence-checklist.md",
                ".incident-scenario-matrix.csv",
                ".final-security-review-report.json",
                ".final-security-review-report.md",
                ".security-readiness-summary.md",
                ".security-gap-register.md",
                ".private-security-review-checklist.md",
                ".security-domain-matrix.csv",
                ".security-gap-closeout-report.json",
                ".security-gap-closeout-report.md",
                ".privacy-review-template.md",
                ".encryption-at-rest-guidance.md",
                ".policy-implementation-matrix.csv",
                ".private-security-action-register.md",
                ".known-limitations-closeout.md",
                ".setup-experience-report.json",
                ".setup-experience-report.md",
                ".first-run-checklist.md",
                ".local-installer-guide.md",
                ".setup-troubleshooting-guide.md",
                ".setup-command-map.csv",
                ".demo-data-report.json",
                ".demo-data-report.md",
                ".demo-seed-plan.md",
                ".demo-reset-plan.md",
                ".demo-data-inventory.csv",
                ".api-docs-report.json",
                ".api-docs-report.md",
                ".api-route-reference.md",
                ".api-route-matrix.csv",
                ".api-usage-examples.md",
                ".openapi-local-guide.md",
                ".hosted-ui-review-report.json",
                ".hosted-ui-review-report.md",
                ".hosted-ui-page-inventory.md",
                ".hosted-ui-route-matrix.csv",
                ".hosted-ui-readiness-checklist.md",
                ".hosted-ui-private-gates.md",
                ".docs-site-polish-report.json",
                ".docs-site-polish-report.md",
                ".docs-reader-paths.md",
                ".docs-navigation-map.md",
                ".docs-site-checklist.md",
                ".docs-link-inventory.csv",
            )
        ):
            add(
                "FAIL",
                "tracked generated/private output",
                f"remove tracked output: {path.as_posix()}",
            )
        if path.suffix.casefold() in UNSAFE_SUFFIXES:
            add(
                "FAIL",
                "tracked unsafe artifact",
                f"remove or replace public artifact: {path.as_posix()}",
            )
        candidate = root / path
        public_content = path.parts[0] in {"docs", "examples"} or path.name in {
            ".env.example",
            "README.md",
            "QUICKSTART.md",
        }
        if (
            public_content
            and candidate.is_file()
            and candidate.suffix.casefold()
            in {
                "",
                ".cfg",
                ".env",
                ".example",
                ".ini",
                ".json",
                ".md",
                ".toml",
                ".txt",
                ".yaml",
                ".yml",
            }
        ):
            try:
                if UNSAFE_TEXT.search(candidate.read_text(encoding="utf-8")):
                    add(
                        "FAIL",
                        "unsafe public text pattern",
                        f"review public file: {path.as_posix()}",
                    )
            except (OSError, UnicodeError):
                add("WARN", "unreadable tracked text", f"could not inspect: {path.as_posix()}")

    if not tracked:
        add(
            "WARN",
            "tracked-file audit",
            "Git metadata unavailable; tracked-output checks were skipped",
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit public first-run usability and repository safety."
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = audit_repository(args.root.resolve())
    counts = {
        level: sum(item.level == level for item in findings) for level in ("PASS", "WARN", "FAIL")
    }
    print("Public usability audit")
    print("======================")
    for item in findings:
        if item.level != "PASS":
            print(f"[{item.level}] {item.check}: {item.message}")
    print(f"\nSummary: {counts['PASS']} passed, {counts['WARN']} warned, {counts['FAIL']} failed.")
    if counts["FAIL"]:
        print("Result: FAIL — fix the items above, then run `make public-usability-audit` again.")
        return 1
    print("Result: PASS — the public first-run paths and safety boundaries are discoverable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
