#!/usr/bin/env python3
import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".example",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_NAMES = {"audit_public_safety.py"}
SAFE_MARKERS = {
    "demo",
    "example",
    "fake",
    "must-not-appear",
    "placeholder",
    "raw-token-value",
    "replace_me",
    "secret-value",
    "synthetic",
    "test",
    "token-value",
}
PRIVATE_PATH_PARTS = {
    ".local-workspace",
    "doctor-output",
    "downloads",
    "customer-deployment-output",
    "customer-output",
    "diagnostics-output",
    "logs",
    "mode-output",
    "onboarding-output",
    "packet-output",
    "pilot-output",
    "pilot-workspace",
    "pilot-readiness-output",
    "private-evidence-output",
    "private-secrets",
    "private-workspace",
    "migration-output",
    "database-output",
    "db-output",
    "backup-output",
    "restore-output",
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
    "webhook-ingress-output",
    "tls-planning-output",
    "dns-planning-output",
    "hosted-pilot-dry-run-output",
    "pilot-dry-run-output",
    "operations-dry-run-output",
    "launch-rehearsal-output",
    "final-readiness-output",
    "public-readiness-output",
    "repo-readiness-output",
    "maintainer-handoff-output",
    "deployment-output",
    "deploy-output",
    "release-output",
    "release-readiness-output",
    "package-output",
    "dist-output",
    "build-output",
    "site",
    "docs-site-output",
    "mkdocs-site-output",
    "tls-output",
    "cert-output",
    "dns-output",
    "infra-output",
    "pilot-evidence-output",
    "evidence-output",
    "private-pilot-evidence",
    "pilot-evidence",
    "evidence-review-output",
    "evidence-expiry-output",
    "evidence-renewal-output",
    "private-evidence-review",
    "quickstart-output",
    "first-run-output",
    "usability-output",
    "pilot-approval-output",
    "approval-packet-output",
    "private-pilot-approval",
    "pilot-approval-packets",
    "storage",
    "smoke-output",
    "sandbox-read-output",
    "sandbox-validation-output",
    "read-validation-output",
    "sandbox-evidence-output",
    "sandbox-evidence-linkage-output",
    "evidence-linkage-output",
    "support-output",
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
    "sandbox-output",
    "sandbox-pilot-output",
    "pilot-flow-output",
    "flow-output",
    "sandbox-workspace",
    "secrets.local",
    ".local-secrets",
    "sync-output",
    "tokens",
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
    "version-prep-output",
    "package-metadata-output",
    "release-prep-output",
    "version-review-output",
    "package-review-output",
    "release-candidate-output",
    "release-candidate-review-output",
    "rc-checklist-output",
    "rc-readiness-output",
    "candidate-release-output",
}


@dataclass(frozen=True)
class SafetyIssue:
    path: Path
    issue_type: str


SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    ["']?(access_token|refresh_token|client_secret|webhook_secret|admin_token|
    app_version_key|session_secret|cookie_secret|oauth_client_secret|
    sso_provider_secret)["']?\s*[:=]\s*["']([^"'\r\n]+)["']
    """
)
BEARER = re.compile(r"(?i)authorization\s*:\s*bearer\s+([^\s'\"}]+)")
SIGNED_PROCORE_URL = re.compile(
    r"(?i)https?://[^\s\"']*procore[^\s\"']*[?&](signature|token|expires)="
)
DATABASE_CREDENTIAL_URL = re.compile(
    r"(?i)(?:postgresql|postgres|mysql|mariadb)://[^:\s/]+:([^@\s/]+)@"
)
CUSTOMER_EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
CUSTOMER_URL = re.compile(r"(?i)https?://([a-z0-9.-]+)")
GENERIC_SIGNED_URL = re.compile(r"(?i)https?://[^\s\"']+[?&](signature|signed|token|expires)=")
OBSERVABILITY_CREDENTIAL = re.compile(
    r"(?i)(?:sentry_dsn|datadog_api_key|new_relic_license_key|honeycomb_api_key)"
    r"\s*[:=]\s*[^\s\"']+"
)
REVIEWER_IDENTITY = re.compile(
    r"""(?ix)["']?(?:reviewer|approver|operator)(?:_placeholder)?["']?\s*:\s*
    ["']([^"'\r\n]+)["']"""
)
RAW_PRIVATE_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:payload|support bundle|smoke report|webhook report)|"
    r"(?:support bundle|smoke report|webhook report)[_ -]?contents?)"
)
ABSOLUTE_LOCAL_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
BINARY_EVIDENCE_REFERENCE = re.compile(
    r"(?i)\.(?:db|sqlite3?|pdf|docx|xlsx?|png|jpe?g|gif|webp|zip)(?:\b|$)"
)
WALKTHROUGH_UNSAFE = re.compile(
    r"(?i)(?:https?://|(?:postgres(?:ql)?|mysql|mariadb|mongodb|sqlite)://|"
    r"(?:/Users/|/home/[^/\s]+/|[A-Z]:\\Users\\)|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)-----)"
)
CLOUD_RESOURCE_ID = re.compile(
    r"(?i)(?:"
    r"\barn:aws[a-z-]*:[^\s\"']+|"
    r"\b\d{12}\b|"
    r"https://[a-z0-9-]+\.vault\.azure\.net(?:/|\b)|"
    r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b|"
    r"\bprojects/[^/\s]+/secrets/[^/\s]+|"
    r'"(?:private_key|private_key_id|client_email|client_x509_cert_url)"\s*:'
    r")"
)
CLOUD_CREDENTIAL_PATH = re.compile(
    r"(?i)(?:/Users/|/home/|[A-Z]:\\)[^\r\n]*(?:\.aws|\.azure|gcloud|credentials)"
)
CLOUD_STORAGE_RESOURCE = re.compile(
    r"(?i)(?:"
    r"\bs3://[^\s\"']+|"
    r"\bgs://[^\s\"']+|"
    r"\barn:aws[a-z-]*:s3:[^\s\"']+|"
    r"https://[a-z0-9-]+\.blob\.core\.windows\.net(?:/|\b)|"
    r"\bprojects/[^/\s]+/(?:buckets|locations)/[^/\s]+"
    r")"
)
CLOUD_STORAGE_CONTENT = re.compile(
    r"""(?ix)["']?(?:object_contents?|file_contents?|attachment_contents?|
    object_key|blob_name)["']?\s*:\s*["']([^"' \r\n][^"'\r\n]*)["']"""
)
HOSTED_REGISTRY_REF = re.compile(
    r"(?i)(?:\b[a-z0-9.-]+/[a-z0-9._/-]+:[a-z0-9._-]+\b|"
    r"\b[a-z0-9._-]+:(?:latest|v?\d[\w.-]*)\b)"
)
HOSTED_PLATFORM_ID = re.compile(
    r"(?i)(?:\barn:aws[a-z-]*:\S+|\b\d{12}\b|/subscriptions/[0-9a-f-]{20,}|"
    r"\bprojects/[a-z0-9-]{6,}\b|"
    r"\b(?:account|subscription|tenant|project|resource|service|cluster|task|app)"
    r"[_-]?id\s*[:=]\s*[a-z0-9-]{6,})"
)
PRODUCTION_APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|approved for production|pilot approved|"
    r"production approved|security complete)\b"
)
DNS_RECORD_VALUE = re.compile(
    r"(?i)(?:\b(?:A|AAAA|CNAME|TXT|MX|CAA|NS)\s+[a-z0-9.-]+\s+\S+|"
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b)"
)
CSR_OR_ACME = re.compile(
    r"(?i)(?:-----BEGIN CERTIFICATE REQUEST-----|"
    r"acme[-_ ]challenge\s*[:=]\s*\S+|_acme-challenge\.[a-z0-9.-]+)"
)
WEBHOOK_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:webhook[_ -]?id\s*[:=]\s*\d{4,}|"
    r"(?:raw[_ -]?)?(?:payload|headers|response_body)\s*[:=]|"
    r"webhook[_ -]?report[_ -]?contents?\s*[:=])"
)
WEBHOOK_SETUP_CLAIM = re.compile(
    r"(?i)\b(?:webhook|production) setup (?:is )?complete\b|"
    r"\bwebhook (?:was )?registered\b"
)
DRY_RUN_PRIVATE_CONTENT = re.compile(
    r"(?i)(?:raw[_ -]?(?:private )?(?:report|evidence|result|payload)|"
    r"(?:report|evidence|support bundle)[_ -]?contents?\s*[:=]|"
    r'"(?:status_code|response_body|deployment_id|live_results?)"\s*:|'
    r"(?:deployment|migration|restore|backup) (?:log|result|output)\s*[:=])"
)
DRY_RUN_APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:approved for (?:launch|pilot|production)|pilot (?:is )?approved|"
    r"launch (?:is )?approved|production[- ]ready|ready for production)\b"
)
FINAL_READINESS_APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:approved for (?:release|production|launch|pilot)|"
    r"(?:release|production|launch|pilot) (?:is )?approved|production[- ]ready)\b"
)
SECURITY_REVIEW_CLAIM = re.compile(
    r"(?i)\b(?:security certified|compliance certified|security complete|"
    r"approved for production|production[- ]ready|(?:soc ?2|iso ?27001|hipaa) certified)\b"
)
WEBHOOK_LIVE_MATERIAL = re.compile(
    r"(?i)(?:live[_ -]?(?:webhook[_ -]?)?(?:headers?|payloads?|signatures?)|"
    r"shared[_ -]?webhook[_ -]?secret|raw[_ -]?request[_ -]?body|replay[_ -]?log|"
    r"webhook[_ -]?registration[_ -]?(?:output|result))\s*[:=]\s*[\"']?"
    r"(?!false\b|none\b|placeholder\b|fake\b|synthetic\b)[^\"'\s]+"
)
DATA_POLICY_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:raw[_ -]?(?:payload|headers?)|source_url|signed_url|storage_key|"
    r"original_filename|attachment_content|deletion_log|private_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!false\b|none\b|placeholder\b|fake\b|synthetic\b)[^\"'\s]+"
)
DATA_POLICY_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|\b(?:soc ?2|iso ?27001) certified\b|"
    r"\b(?:compliance|security) certified\b|\bproduction[- ]ready\b|"
    r"\b(?:launch|pilot) approved\b|\bprocore (?:endorsed|partner|certified)\b|"
    r"\bpurge job (?:implemented|enabled|active)\b"
)
INFRA_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:secret_value|password|api_key|admin_token|webhook_secret|"
    r"dmsa_client_(?:id|secret)|database_url|presigned_url|signed_url|"
    r"storage_key|object_key|db_dump_content|backup_archive_content|migration_log)"
    r"\s*[:=]\s*[\"']?(?!false\b|none\b|placeholder\b|fake\b|synthetic\b)[^\"'\s]+"
)
INFRA_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|\b(?:soc ?2|iso ?27001) certified\b|"
    r"\b(?:compliance|security) certified\b|\bproduction[- ]ready\b|"
    r"\b(?:launch|pilot) approved\b|\bprocore (?:endorsed|partner|certified)\b"
)
SUPPLY_CHAIN_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|publish_token|ci_secret|signing_key|"
    r"registry_password)\s*[:=]\s*[\"']?(?!placeholder\b|fake\b)[^\"'\s]+"
)
SUPPLY_CHAIN_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:slsa|sbom|gdpr|ccpa|hipaa) compliant\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance) certified\b|"
    r"\bproduction[- ]ready\b|\b(?:launch|pilot) approved\b|"
    r"\bprocore (?:endorsed|partner|certified)\b"
)
INCIDENT_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:raw_log|packet_capture|har_file|memory_dump|core_dump|forensic_image|"
    r"legal_notice_content|regulator_notice_content|law_enforcement_report_content|"
    r"breach_notification_content|incident_timeline|secret_rotation_log|rollback_log)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b)[^\"'\s]+"
)
INCIDENT_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance|breach readiness) certified\b|"
    r"\bproduction[- ]ready\b|\b(?:launch|pilot) approved\b|"
    r"\bbreach notification completed\b|\bprocore (?:endorsed|partner|certified)\b"
)
FINAL_SECURITY_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:raw_log|raw_payload|live_webhook_headers?|webhook_signature|webhook_secret|"
    r"authorization|bearer|github_token|registry_token|ci_secret|signing_key|admin_token|"
    r"dmsa_client_(?:id|secret)|database_url|source_url|signed_url|presigned_url|"
    r"storage_key|object_key|packet_capture|har_file|memory_dump|core_dump|forensic_image|"
    r"legal_notice_content|regulator_notice_content|law_enforcement_report_content|"
    r"breach_notification_content|private_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
FINAL_SECURITY_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa|slsa|sbom|privacy|legal) compliant\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance|breach readiness) certified\b|"
    r"\bproduction[- ]ready\b|\bapproved for (?:production|launch|pilot|release)\b|"
    r"\b(?:production|launch|pilot|release) (?:is )?approved\b|"
    r"\bbreach notification completed\b|\bprocore (?:endorsed|partner|certified)\b"
)
SECURITY_GAP_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa|slsa|sbom|privacy|legal) compliant\b|"
    r"\b(?:soc ?2|iso ?27001|security|privacy|legal|compliance|breach readiness) "
    r"certified\b|\bproduction[- ]ready\b|"
    r"\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:production|launch|pilot|release|deployment) (?:is )?approved\b|"
    r"\bbreach notification completed\b|\bprocore (?:endorsed|partner|certified)\b"
)
SECURITY_GAP_IMPLEMENTATION_CLAIM = re.compile(
    r"(?i)\b(?:encryption(?: at rest)?|retention enforcement|notifications?) "
    r"(?:is |are )?(?:implemented|enabled|operational|complete)\b"
)
SECURITY_GAP_QUALIFIER = re.compile(
    r"(?i)\b(?:no|not|never|does not|is not|are not|must not|guidance(?: only)?|"
    r"future work|future product work|private infrastructure|privately implemented|"
    r"intentionally not implemented)\b"
)
SETUP_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|approved for (?:production|release|pilot|launch)|"
    r"(?:production|release|pilot|launch) (?:is )?approved|"
    r"(?:soc ?2|iso ?27001|hipaa|gdpr|ccpa|slsa|sbom|security|compliance) certified|"
    r"(?:gdpr|ccpa|hipaa|privacy|legal) compliant)\b"
)
SETUP_DEMO_SECRET_REQUIREMENT = re.compile(
    r"(?i)\bdemo(?: mode)?\b.*\b(?:requires?|must (?:provide|set|use)|needs?)\b.*"
    r"\b(?:real )?(?:secrets?|credentials?|tokens?|dmsa|webhook secret|admin token)\b|"
    r"\b(?:secrets?|credentials?|tokens?|dmsa|webhook secret|admin token)\b.*"
    r"\b(?:required|needed|mandatory)\b.*\bdemo(?: mode)?\b"
)
SETUP_SAFETY_QUALIFIER = re.compile(
    r"(?i)\b(?:no|not|never|does not|do not|is not|are not|must not|without|"
    r"doesn't|isn't|aren't|requires no|not required|not needed|not implied)\b"
)
DEMO_DATA_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:reset|remove|delete|purge)\b.*\b(?:customer data|private workspace|"
    r"sandbox|pilot|hosted)\b|\b(?:production[- ]ready|approved for (?:production|"
    r"release|pilot|launch)|(?:production|release|pilot|launch) (?:is )?approved|"
    r"(?:soc ?2|iso ?27001|hipaa|gdpr|ccpa|slsa|sbom|security|compliance) certified|"
    r"(?:gdpr|ccpa|hipaa|privacy|legal) compliant)\b"
)
API_DOCS_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|package_registry_token|ci_secret|database_url|"
    r"authorization|bearer|source_url|signed_url|presigned_url|storage_key|object_key|"
    r"private_path|private_report_contents?|raw_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
API_DOCS_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|approved for (?:production|release|pilot|launch|"
    r"deployment)|(?:production|release|pilot|launch|deployment) (?:is )?approved|"
    r"(?:soc ?2|iso ?27001|hipaa|gdpr|ccpa|security|compliance) certified|"
    r"(?:gdpr|ccpa|hipaa|privacy|legal) compliant)\b"
)
HOSTED_UI_EXTERNAL_ASSET = re.compile(
    r"(?i)(?:<(?:script|link)\b[^>]*(?:src|href)\s*=\s*[\"'](?:https?:)?//|"
    r"@import\s+(?:url\()?\s*[\"']?(?:https?:)?//|"
    r"\b(?:google-analytics|googletagmanager|segment|mixpanel|amplitude|hotjar|"
    r"telemetry|tracking[_ -]?script)\b)"
)
HOSTED_UI_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|package_registry_token|ci_secret|database_url|"
    r"authorization|bearer|source_url|signed_url|presigned_url|storage_key|object_key|"
    r"private_path|private_report_contents?|raw_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
HOSTED_UI_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:hosted (?:ui )?(?:is )?deployed|production[- ]ready|approved for "
    r"(?:production|release|pilot|launch|deployment)|(?:production|release|pilot|launch|"
    r"deployment) (?:is )?approved|(?:soc ?2|iso ?27001|hipaa|gdpr|ccpa|security|"
    r"compliance) certified|(?:gdpr|ccpa|hipaa|privacy|legal) compliant)\b"
)
DOCS_SITE_EXTERNAL_SERVICE = re.compile(
    r"(?i)(?:<(?:script|link)\b[^>]*(?:src|href)\s*=\s*[\"'](?:https?:)?//|"
    r"@import\s+(?:url\()?\s*[\"']?(?:https?:)?//|\b(?:google-analytics|"
    r"googletagmanager|algolia|docsearch|segment|mixpanel|amplitude|hotjar|"
    r"tracking[_ -]?script|external search|cdn asset)\b)"
)
DOCS_SITE_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|package_registry_token|ci_secret|database_url|"
    r"authorization|bearer|source_url|signed_url|presigned_url|storage_key|object_key|"
    r"private_path|private_report_contents?|raw_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
DOCS_SITE_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:docs (?:site )?(?:is )?(?:deployed|hosted)|github pages (?:is )?"
    r"(?:enabled|deployed)|production[- ]ready|approved for (?:production|release|pilot|"
    r"launch|deployment|docs hosting)|(?:production|release|pilot|launch|deployment) "
    r"(?:is )?approved|(?:soc ?2|iso ?27001|hipaa|gdpr|ccpa|security|compliance) "
    r"certified|(?:gdpr|ccpa|hipaa|privacy|legal) compliant)\b"
)
VERSION_PREP_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|package_registry_token|publish_token|ci_secret|"
    r"release_signing_key|signing_key|registry_password|database_url|authorization|"
    r"bearer|signed_url|storage_key|private_path|private_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
VERSION_PREP_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:package (?:was |is )?(?:built|published|uploaded)|docker image "
    r"(?:was |is )?(?:built|pushed)|(?:tag|release) (?:was |is )?created|"
    r"(?:application|app|docs) (?:was |is )?deployed|production[- ]ready|approved for "
    r"(?:production|release|pilot|launch|deployment)|(?:production|release|pilot|launch|"
    r"deployment) (?:is )?approved|procore (?:endorsed|partner|certified|officially "
    r"supported))\b"
)
RELEASE_CANDIDATE_PRIVATE_MATERIAL = re.compile(
    r"(?i)(?:github_token|registry_token|package_registry_token|publish_token|ci_secret|"
    r"release_signing_key|signing_key|registry_password|database_url|authorization|"
    r"bearer|signed_url|storage_key|private_path|private_report_contents?)"
    r"\s*[:=]\s*[\"']?(?!placeholder\b|fake\b|none\b|false\b)[^\"'\s]+"
)
RELEASE_CANDIDATE_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:package (?:was |is )?(?:built|published|uploaded)|docker image "
    r"(?:was |is )?(?:built|pushed)|(?:tag|release) (?:was |is )?created|"
    r"(?:application|app|docs) (?:was |is )?deployed|release candidate (?:is )?approved|"
    r"production[- ]ready|approved for (?:production|release|pilot|launch|deployment)|"
    r"(?:production|release|pilot|launch|deployment) (?:is )?approved|procore "
    r"(?:endorsed|partner|certified|officially supported))\b"
)


def _safe_value(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in SAFE_MARKERS) or value.startswith(("${", "{"))


def audit_text(path: Path, text: str) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    if any(
        marker in path.as_posix()
        for marker in ("release-candidate", "release_candidate", "rc-checklist", "rc-readiness")
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        lines = text.splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : index + 1])
            qualified = SETUP_SAFETY_QUALIFIER.search(context) or re.search(
                r"(?i)\b(?:none|absent|not added|not present|did not|has not|excluded)\b",
                context,
            )
            if RELEASE_CANDIDATE_PRIVATE_MATERIAL.search(line) and not excluded:
                issues.append(SafetyIssue(path, "release candidate exposes publishing material"))
                break
            if RELEASE_CANDIDATE_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "release candidate implies live release or approval")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "version-prep",
            "version_prep",
            "version-source",
            "package-metadata",
            "release-boundary",
        )
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        lines = text.splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : index + 1])
            qualified = SETUP_SAFETY_QUALIFIER.search(context) or re.search(
                r"(?i)\b(?:none|absent|not added|not present|did not|has not|excluded)\b",
                context,
            )
            if VERSION_PREP_PRIVATE_MATERIAL.search(line) and not excluded:
                issues.append(
                    SafetyIssue(path, "version prep exposes publishing or private material")
                )
                break
            if VERSION_PREP_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "version prep implies build, publication, or approval")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "docs-site-polish",
            "docs_site_polish",
            "docs-reader",
            "docs-navigation",
            "docs_navigation",
        )
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        lines = text.splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : index + 1])
            qualified = SETUP_SAFETY_QUALIFIER.search(context) or re.search(
                r"(?i)\b(?:none|absent|not added|not present|excluded)\b", context
            )
            if DOCS_SITE_EXTERNAL_SERVICE.search(line) and not excluded and not qualified:
                issues.append(SafetyIssue(path, "docs site references external services or assets"))
                break
            if DOCS_SITE_PRIVATE_MATERIAL.search(line) and not excluded:
                issues.append(SafetyIssue(path, "docs-site guidance exposes private material"))
                break
            if DOCS_SITE_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(SafetyIssue(path, "docs-site guidance implies hosting or approval"))
                break
    if path.suffix.casefold() == ".html" and "templates" in path.parts:
        if HOSTED_UI_EXTERNAL_ASSET.search(text):
            issues.append(SafetyIssue(path, "UI template references external assets or tracking"))
    if any(
        marker in path.as_posix()
        for marker in ("hosted-ui", "hosted_ui", "hosted-page", "hosted_page")
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        lines = text.splitlines()
        for index, line in enumerate(lines):
            context = " ".join(lines[max(0, index - 2) : index + 1])
            qualified = SETUP_SAFETY_QUALIFIER.search(context)
            hosted_ui_qualified = qualified or re.search(
                r"(?i)\b(?:none|absent|not added|not present|excluded)\b", line
            )
            if HOSTED_UI_EXTERNAL_ASSET.search(line) and not excluded and not hosted_ui_qualified:
                issues.append(SafetyIssue(path, "hosted UI references external assets or tracking"))
                break
            if HOSTED_UI_PRIVATE_MATERIAL.search(line) and not excluded:
                issues.append(SafetyIssue(path, "hosted UI guidance exposes private material"))
                break
            if HOSTED_UI_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "hosted UI guidance implies deployment or approval")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in ("api-docs", "api_docs", "api-route", "api_route", "openapi-local")
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        for line in text.splitlines():
            qualified = SETUP_SAFETY_QUALIFIER.search(line)
            if API_DOCS_PRIVATE_MATERIAL.search(line) and not excluded:
                issues.append(SafetyIssue(path, "API docs expose private material"))
                break
            if API_DOCS_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(SafetyIssue(path, "API docs imply approval or certification"))
                break
    if any(
        marker in path.as_posix()
        for marker in ("demo-data", "demo_data", "demo-seed", "demo-reset")
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        for line in text.splitlines():
            qualified = SETUP_SAFETY_QUALIFIER.search(line)
            if DEMO_DATA_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "demo data guidance implies unsafe reset or approval")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "setup-experience",
            "setup_experience",
            "local-installer-guide",
            "first-run-checklist",
            "setup-troubleshooting-guide",
            "setup-command-map",
        )
    ):
        excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
        for line in text.splitlines():
            qualified = SETUP_SAFETY_QUALIFIER.search(line)
            if SETUP_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(SafetyIssue(path, "setup guidance implies approval or certification"))
                break
            if SETUP_DEMO_SECRET_REQUIREMENT.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "setup guidance requires real secrets for Demo Mode")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "security-gap-closeout",
            "security_gap_closeout",
            "privacy-review-template",
            "encryption-at-rest-guidance",
            "private-security-action-register",
            "known-limitations-closeout",
            "policy-implementation-matrix",
        )
    ):
        for line in text.splitlines():
            excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
            qualified = SECURITY_GAP_QUALIFIER.search(line)
            if SECURITY_GAP_UNSAFE_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "security gap closeout implies certification or approval")
                )
                break
            if SECURITY_GAP_IMPLEMENTATION_CLAIM.search(line) and not excluded and not qualified:
                issues.append(
                    SafetyIssue(path, "security gap closeout makes an implementation claim")
                )
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "final-security",
            "final_security",
            "security-readiness",
            "security-gap-register",
            "private-security-review",
            "security-domain-matrix",
        )
    ):
        for line in text.splitlines():
            excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
            negated = re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            if FINAL_SECURITY_UNSAFE_CLAIM.search(line) and not excluded and not negated:
                issues.append(
                    SafetyIssue(path, "final security review implies certification or approval")
                )
                break
            if (
                FINAL_SECURITY_PRIVATE_MATERIAL.search(line)
                and not excluded
                and not _safe_value(line)
            ):
                issues.append(SafetyIssue(path, "final security review contains private material"))
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "incident-response",
            "incident_response",
            "incident-runbook",
            "audit-log-boundary",
            "forensics-evidence",
        )
    ):
        for line in text.splitlines():
            excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
            negated = re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            if INCIDENT_UNSAFE_CLAIM.search(line) and not excluded and not negated:
                issues.append(
                    SafetyIssue(path, "incident review implies certification or approval")
                )
                break
            if INCIDENT_PRIVATE_MATERIAL.search(line) and not excluded and not _safe_value(line):
                issues.append(SafetyIssue(path, "incident review contains private evidence"))
                break
    if any(
        marker in path.as_posix()
        for marker in ("supply-chain", "supply_chain", "dependency-boundary", "package-surface")
    ):
        for line in text.splitlines():
            excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
            negated = re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            if SUPPLY_CHAIN_UNSAFE_CLAIM.search(line) and not excluded and not negated:
                issues.append(
                    SafetyIssue(path, "supply-chain review implies certification or approval")
                )
                break
            if (
                SUPPLY_CHAIN_PRIVATE_MATERIAL.search(line)
                and not excluded
                and not _safe_value(line)
            ):
                issues.append(SafetyIssue(path, "supply-chain review contains private material"))
                break
    if any(
        marker in path.as_posix()
        for marker in (
            "infra-security",
            "infra_security",
            "secret-boundary",
            "storage-boundary",
            "database-boundary",
        )
    ):
        for line in text.splitlines():
            excluded = any(part in path.parts for part in ("tests", "services", "schemas"))
            negated = re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            if INFRA_UNSAFE_CLAIM.search(line) and not excluded and not negated:
                issues.append(
                    SafetyIssue(path, "infrastructure review implies certification or approval")
                )
                break
            if INFRA_PRIVATE_MATERIAL.search(line) and not excluded and not _safe_value(line):
                issues.append(SafetyIssue(path, "infrastructure review contains private material"))
                break
    if any(
        marker in path.as_posix()
        for marker in ("data-policy", "data_policy", "retention-redaction")
    ):
        for line in text.splitlines():
            excluded_source = any(part in path.parts for part in ("tests", "services", "schemas"))
            negated = re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            if DATA_POLICY_UNSAFE_CLAIM.search(line) and not excluded_source and not negated:
                issues.append(
                    SafetyIssue(path, "data policy implies compliance, certification, or approval")
                )
                break
            if (
                DATA_POLICY_PRIVATE_MATERIAL.search(line)
                and not excluded_source
                and not _safe_value(line)
            ):
                issues.append(SafetyIssue(path, "data policy contains private material"))
                break
    if "webhook-security" in path.as_posix() or "webhook_security" in path.as_posix():
        for line in text.splitlines():
            if (
                SECURITY_REVIEW_CLAIM.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and not re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            ):
                issues.append(
                    SafetyIssue(path, "webhook security review implies certification or approval")
                )
                break
            if (
                WEBHOOK_LIVE_MATERIAL.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and "schemas" not in path.parts
                and not _safe_value(line)
            ):
                issues.append(SafetyIssue(path, "webhook review contains live security material"))
                break
    if any(
        marker in path.as_posix()
        for marker in ("auth-boundary", "auth_boundary", "permission-boundary")
    ):
        for line in text.splitlines():
            if (
                SECURITY_REVIEW_CLAIM.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and not re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            ):
                issues.append(
                    SafetyIssue(path, "auth boundary audit implies certification or approval")
                )
                break
    if "security-threat" in path.as_posix() or "security_threat" in path.as_posix():
        for line in text.splitlines():
            if (
                SECURITY_REVIEW_CLAIM.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and not re.search(r"(?i)\b(?:no|not|never|does not|is not|must not)\b", line)
            ):
                issues.append(
                    SafetyIssue(path, "security threat model implies certification or approval")
                )
                break
    if "demo-product" in path.as_posix() or "demo_product" in path.as_posix():
        unsafe_demo_claim = re.compile(
            r"(?i)\b(?:demo|walkthrough)\b.*\b(?:production[- ]ready|"
            r"pilot approved|release approved|compliance certified|"
            r"official customer report|approval granted)\b"
        )
        for line in text.splitlines():
            if (
                unsafe_demo_claim.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and not re.search(r"(?i)\b(?:no|not|never|does not|is not)\b", line)
            ):
                issues.append(SafetyIssue(path, "Demo walkthrough implies an external decision"))
                break
    if "product-dashboard" in path.as_posix() or "product_dashboard" in path.as_posix():
        unsafe_dashboard_claim = re.compile(
            r"(?i)\b(?:dashboard|readiness)\b.*\b(?:production[- ]ready|"
            r"pilot approved|release approved|compliance determination|"
            r"official customer report|approval granted)\b"
        )
        for line in text.splitlines():
            if (
                unsafe_dashboard_claim.search(line)
                and "tests" not in path.parts
                and "services" not in path.parts
                and not re.search(r"(?i)\b(?:no|not|never|does not|is not)\b", line)
            ):
                issues.append(SafetyIssue(path, "product dashboard implies an external decision"))
                break
    if "operator-export" in path.as_posix() or "operator_export" in path.as_posix():
        unsafe_export_claim = re.compile(
            r"(?i)\b(?:official customer report|compliance (?:report|certificate)|"
            r"approval granted|approved export|procore status)\b"
        )
        for line in text.splitlines():
            if (
                unsafe_export_claim.search(line)
                and (
                    not (
                        "tests" in path.parts or ("app" in path.parts and "services" in path.parts)
                    )
                    or "assert" in line
                )
                and not re.search(r"(?i)\b(?:no|not|never|isn't|is not|does not|must not)\b", line)
                and not _safe_value(line)
            ):
                issues.append(
                    SafetyIssue(path, "operator export implies an official external decision")
                )
                break
    if "attachment-review" in path.as_posix() or "attachment_review" in path.as_posix():
        unsafe_attachment_claim = re.compile(
            r"(?i)\b(?:attachment|manifest|file)\b.*\b(?:download|serve|open file|"
            r"source url|signed url|storage key|private path|original filename|"
            r"approval|compliance)\b"
        )
        for line in text.splitlines():
            if (
                unsafe_attachment_claim.search(line)
                and not re.search(
                    r"(?i)\b(?:no|not|never|without|unavailable|does not|do not)\b",
                    line,
                )
                and not _safe_value(line)
            ):
                issues.append(
                    SafetyIssue(
                        path,
                        "attachment review content implies unsafe file access or action",
                    )
                )
                break
    if "operator-triage" in path.as_posix() or "operator_triage" in path.as_posix():
        triage_claim = re.compile(
            r"(?i)\b(?:triage|priority|queue)\b.*\b(?:approval|compliance|"
            r"assignment|notification|procore update|write-back)\b"
        )
        for line in text.splitlines():
            if (
                triage_claim.search(line)
                and not re.search(r"(?i)\b(?:no|not|never|does not|do not|isn't|is not)\b", line)
                and not _safe_value(line)
            ):
                issues.append(
                    SafetyIssue(path, "triage content implies a prohibited external action")
                )
                break
    if "intake-lifecycle" in path.as_posix() or "intake_lifecycle" in path.as_posix():
        lifecycle_claim = re.compile(
            r"(?i)\b(?:status|transition|lifecycle)\b.*\b(?:approval|"
            r"compliance determination|sent to procore|customer communication)\b"
        )
        for line in text.splitlines():
            if (
                lifecycle_claim.search(line)
                and not re.search(r"(?i)\b(?:no|not|never|does not|do not)\b", line)
                and not _safe_value(line)
            ):
                issues.append(
                    SafetyIssue(path, "lifecycle content implies an external decision or action")
                )
                break
    if (
        "intake_review_workspace" in path.as_posix()
        and path.parts
        and path.parts[0] in {"docs", "examples", "tests"}
    ):
        unsafe_workspace_literal = re.compile(
            r"(?i)(?:https?://(?!unsafe\.invalid)|/Users/(?!example/)|"
            r"(?:raw_payload_json|source_url|storage_path|storage_key)\s*[:=]\s*"
            r"[\"'][^\"']+[\"'])"
        )
        for line in text.splitlines():
            if not _safe_value(line) and unsafe_workspace_literal.search(line):
                issues.append(SafetyIssue(path, "workspace fixture contains exposed private data"))
                break
    if path.suffix.casefold() == ".js" and re.search(
        r"(?i)(?:https?://|google-analytics|googletagmanager|segment\.com|mixpanel)",
        text,
    ):
        issues.append(SafetyIssue(path, "external analytics or tracking JavaScript"))
    if "examples/cloud-storage-providers" in path.as_posix():
        for match in CLOUD_STORAGE_CONTENT.finditer(text):
            if not _safe_value(match.group(1)):
                issues.append(
                    SafetyIssue(path, "cloud storage example contains an object key or contents")
                )
    if "examples/postgres-runtime" in path.as_posix():
        if DATABASE_CREDENTIAL_URL.search(text) or ABSOLUTE_LOCAL_PATH.search(text):
            issues.append(SafetyIssue(path, "PostgreSQL example contains private database data"))
        for line in text.splitlines():
            if re.search(
                r"(?i)\b(?:database_url|hostname|username|password|backup_filename|"
                r"dump_filename)\b\s*[:=]",
                line,
            ) and not _safe_value(line):
                issues.append(
                    SafetyIssue(path, "PostgreSQL example contains non-placeholder runtime data")
                )
                break
    if "examples/hosted-deployment-templates" in path.as_posix():
        for line in text.splitlines():
            if _safe_value(line):
                continue
            if CUSTOMER_URL.search(line):
                issues.append(SafetyIssue(path, "hosted template contains a provider URL"))
                break
    if "examples/https-webhook-planning" in path.as_posix():
        for line in text.splitlines():
            if _safe_value(line):
                continue
            if CUSTOMER_URL.search(line):
                issues.append(SafetyIssue(path, "webhook planning example contains a real URL"))
                break
    if "examples/hosted-pilot-dry-run" in path.as_posix():
        for line in text.splitlines():
            if _safe_value(line):
                continue
            if (
                CUSTOMER_URL.search(line)
                or CUSTOMER_EMAIL.search(line)
                or ABSOLUTE_LOCAL_PATH.search(line)
                or CLOUD_RESOURCE_ID.search(line)
                or HOSTED_REGISTRY_REF.search(line)
            ):
                issues.append(
                    SafetyIssue(path, "hosted pilot dry-run example contains private data")
                )
                break
    if "examples/final-public-readiness" in path.as_posix():
        for line in text.splitlines():
            if _safe_value(line):
                continue
            if (
                CUSTOMER_URL.search(line)
                or CUSTOMER_EMAIL.search(line)
                or ABSOLUTE_LOCAL_PATH.search(line)
                or CLOUD_RESOURCE_ID.search(line)
                or DRY_RUN_PRIVATE_CONTENT.search(line)
            ):
                issues.append(SafetyIssue(path, "final readiness example contains private data"))
                break
            if FINAL_READINESS_APPROVAL_CLAIM.search(line) and not re.search(
                r"(?i)\b(?:no|not|never|neither)\b", line
            ):
                issues.append(SafetyIssue(path, "final readiness example claims public approval"))
                break
            if DRY_RUN_PRIVATE_CONTENT.search(line):
                issues.append(
                    SafetyIssue(path, "hosted pilot dry-run example contains report contents")
                )
                break
            if DRY_RUN_APPROVAL_CLAIM.search(line) and not re.search(
                r"(?i)\b(?:no|not|never|neither)\b", line
            ):
                issues.append(SafetyIssue(path, "hosted pilot dry-run example claims approval"))
                break
            if DNS_RECORD_VALUE.search(line):
                issues.append(SafetyIssue(path, "webhook planning example contains a DNS record"))
                break
            if CSR_OR_ACME.search(line):
                issues.append(SafetyIssue(path, "webhook planning example contains CSR/ACME data"))
                break
            if WEBHOOK_PRIVATE_MATERIAL.search(line):
                issues.append(SafetyIssue(path, "webhook planning example contains private data"))
                break
            if WEBHOOK_SETUP_CLAIM.search(line) and not re.search(
                r"(?i)\b(?:no|not|never)\b", line
            ):
                issues.append(SafetyIssue(path, "webhook planning example claims live setup"))
                break
            if HOSTED_REGISTRY_REF.search(line):
                issues.append(SafetyIssue(path, "hosted template contains a registry reference"))
                break
            if HOSTED_PLATFORM_ID.search(line):
                issues.append(SafetyIssue(path, "hosted template contains a platform identifier"))
                break
            if PRODUCTION_APPROVAL_CLAIM.search(line) and not re.search(
                r"(?i)\b(?:no|not|never|neither)\b", line
            ):
                issues.append(SafetyIssue(path, "hosted template contains an approval claim"))
                break
    for line in text.splitlines():
        if (
            path.suffix.casefold() != ".py"
            and CLOUD_RESOURCE_ID.search(line)
            and not _safe_value(line)
            and not ("{" in line and "}" in line)
        ):
            issues.append(SafetyIssue(path, "cloud resource identifier or credential JSON"))
            break
    for line in text.splitlines():
        if (
            path.suffix.casefold() != ".py"
            and CLOUD_STORAGE_RESOURCE.search(line)
            and not _safe_value(line)
            and not ("{" in line and "}" in line)
        ):
            issues.append(SafetyIssue(path, "cloud storage resource identifier or URL"))
            break
    if path.suffix.casefold() != ".py" and CLOUD_CREDENTIAL_PATH.search(text):
        issues.append(SafetyIssue(path, "local cloud credential path"))
    if "examples/sandbox-read-validation" in path.as_posix():
        if re.search(
            r"(?i)[\"']?(?:company|project|rfi|submittal)[_-]?id[\"']?\s*:\s*[0-9]{4,}",
            text,
        ):
            issues.append(SafetyIssue(path, "sandbox read example contains a raw identifier"))
        if re.search(
            r"(?i)[\"']?(?:subject|title|description|vendor|attachment_filename|"
            r"raw_payload|response_body)[\"']?\s*:",
            text,
        ):
            issues.append(SafetyIssue(path, "sandbox read example contains response-like content"))
        if CUSTOMER_EMAIL.search(text) or CUSTOMER_URL.search(text):
            issues.append(SafetyIssue(path, "sandbox read example contains a contact or URL"))
    for match in SECRET_ASSIGNMENT.finditer(text):
        if not _safe_value(match.group(2)):
            issues.append(SafetyIssue(path, f"non-placeholder {match.group(1).casefold()}"))
    for match in BEARER.finditer(text):
        if not _safe_value(match.group(1)):
            issues.append(SafetyIssue(path, "Authorization bearer value"))
    if SIGNED_PROCORE_URL.search(text):
        issues.append(SafetyIssue(path, "signed Procore URL"))
    if OBSERVABILITY_CREDENTIAL.search(text):
        issues.append(SafetyIssue(path, "external observability credential"))
    for match in DATABASE_CREDENTIAL_URL.finditer(text):
        if not _safe_value(match.group(1)):
            issues.append(SafetyIssue(path, "database URL contains credentials"))
    if "examples/customer-deployments" in path.as_posix():
        if CUSTOMER_EMAIL.search(text):
            issues.append(SafetyIssue(path, "customer example contains an email address"))
        for match in CUSTOMER_URL.finditer(text):
            host = match.group(1).casefold()
            if not host.endswith((".local", ".invalid")):
                issues.append(SafetyIssue(path, "customer example contains a non-placeholder URL"))
        if GENERIC_SIGNED_URL.search(text):
            issues.append(SafetyIssue(path, "customer example contains a signed URL"))
    if "examples/private-evidence" in path.as_posix():
        if CUSTOMER_EMAIL.search(text):
            issues.append(SafetyIssue(path, "evidence example contains an email address"))
        for match in CUSTOMER_URL.finditer(text):
            host = match.group(1).casefold()
            if not host.endswith((".local", ".invalid")):
                issues.append(SafetyIssue(path, "evidence example contains a non-placeholder URL"))
        if GENERIC_SIGNED_URL.search(text):
            issues.append(SafetyIssue(path, "evidence example contains a signed URL"))
    if "examples/evidence-review" in path.as_posix():
        if CUSTOMER_EMAIL.search(text):
            issues.append(SafetyIssue(path, "review example contains an email address"))
        for match in CUSTOMER_URL.finditer(text):
            host = match.group(1).casefold()
            if not host.endswith((".local", ".invalid")):
                issues.append(SafetyIssue(path, "review example contains a non-placeholder URL"))
        if GENERIC_SIGNED_URL.search(text):
            issues.append(SafetyIssue(path, "review example contains a signed URL"))
        for match in REVIEWER_IDENTITY.finditer(text):
            if not _safe_value(match.group(1)):
                issues.append(SafetyIssue(path, "review example contains a reviewer identity"))
    if "examples/pilot-approval" in path.as_posix():
        if CUSTOMER_EMAIL.search(text):
            issues.append(SafetyIssue(path, "approval example contains an email address"))
        for match in CUSTOMER_URL.finditer(text):
            host = match.group(1).casefold()
            if not host.endswith((".local", ".invalid")):
                issues.append(SafetyIssue(path, "approval example contains a non-placeholder URL"))
        for match in REVIEWER_IDENTITY.finditer(text):
            if not _safe_value(match.group(1)):
                issues.append(SafetyIssue(path, "approval example contains a reviewer identity"))
        if GENERIC_SIGNED_URL.search(text):
            issues.append(SafetyIssue(path, "approval example contains a signed URL"))
    if (
        "examples/private-evidence" in path.as_posix()
        or "examples/evidence-review" in path.as_posix()
        or "examples/pilot-approval" in path.as_posix()
    ):
        if RAW_PRIVATE_CONTENT.search(text):
            issues.append(SafetyIssue(path, "evidence example contains raw private content"))
        if ABSOLUTE_LOCAL_PATH.search(text):
            issues.append(SafetyIssue(path, "evidence example contains an absolute local path"))
        if BINARY_EVIDENCE_REFERENCE.search(text):
            issues.append(SafetyIssue(path, "evidence example contains a binary reference"))
    if (
        path.as_posix().startswith("docs/walkthrough-")
        or "examples/walkthrough-output" in path.as_posix()
    ):
        if WALKTHROUGH_UNSAFE.search(text):
            issues.append(SafetyIssue(path, "walkthrough contains an unsafe public pattern"))
        if CUSTOMER_EMAIL.search(text):
            issues.append(SafetyIssue(path, "walkthrough contains an email address"))
    return issues


def audit_paths(paths: list[Path]) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    for path in paths:
        if path.name in SKIP_NAMES or not path.is_file():
            continue
        if path.name in {
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "vite.config.js",
            "vite.config.ts",
            "webpack.config.js",
        }:
            issues.append(SafetyIssue(path, "tracked frontend package or build-system file"))
            continue
        if path.parts[:2] == (".github", "workflows"):
            issues.append(SafetyIssue(path, "tracked GitHub Actions automation"))
            continue
        if path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}:
            issues.append(SafetyIssue(path, "tracked local database file"))
            continue
        if path.suffix.casefold() in {".sql", ".dump", ".backup", ".bak", ".pgdump"}:
            issues.append(SafetyIssue(path, "tracked database dump or backup"))
            continue
        if path.suffix.casefold() in {
            ".pem",
            ".key",
            ".crt",
            ".csr",
            ".p12",
            ".pfx",
            ".tfstate",
            ".tfvars",
        }:
            issues.append(SafetyIssue(path, "tracked certificate or infrastructure state"))
            continue
        if path.name.endswith((".smoke.json", ".smoke.log")):
            issues.append(SafetyIssue(path, "tracked sandbox smoke output"))
            continue
        if any(
            part
            in {
                "release-candidate-output",
                "release-candidate-review-output",
                "rc-checklist-output",
                "rc-readiness-output",
                "candidate-release-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".release-candidate-report.json",
                ".release-candidate-report.md",
                ".release-candidate-checklist.md",
                ".release-candidate-gap-register.md",
                ".release-candidate-command-plan.md",
                ".release-candidate-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated release-candidate output"))
            continue
        if any(
            part
            in {
                "version-prep-output",
                "package-metadata-output",
                "release-prep-output",
                "version-review-output",
                "package-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".version-prep-report.json",
                ".version-prep-report.md",
                ".package-metadata-summary.md",
                ".version-source-map.md",
                ".release-boundary-checklist.md",
                ".version-readiness-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated version-prep output"))
            continue
        if any(
            part
            in {
                "docs-site-polish-output",
                "docs-site-review-output",
                "docs-navigation-output",
                "docs-reader-path-output",
                "docs-link-check-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".docs-site-polish-report.json",
                ".docs-site-polish-report.md",
                ".docs-reader-paths.md",
                ".docs-navigation-map.md",
                ".docs-site-checklist.md",
                ".docs-link-inventory.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated docs-site polish output"))
            continue
        if any(
            part
            in {
                "hosted-ui-review-output",
                "hosted-ui-output",
                "ui-readiness-output",
                "hosted-page-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".hosted-ui-review-report.json",
                ".hosted-ui-review-report.md",
                ".hosted-ui-page-inventory.md",
                ".hosted-ui-route-matrix.csv",
                ".hosted-ui-readiness-checklist.md",
                ".hosted-ui-private-gates.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated hosted UI output"))
            continue
        if any(
            part
            in {
                "api-docs-output",
                "api-reference-output",
                "route-reference-output",
                "openapi-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".api-docs-report.json",
                ".api-docs-report.md",
                ".api-route-reference.md",
                ".api-route-matrix.csv",
                ".api-usage-examples.md",
                ".openapi-local-guide.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated API docs output"))
            continue
        if any(
            part
            in {
                "demo-walkthrough-output",
                "demo-product-output",
                "demo-tour-output",
                "demo-evaluation-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".demo-walkthrough-report.json",
                ".demo-walkthrough-report.md",
                ".demo-product-tour.md",
                ".demo-evaluation-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated Demo walkthrough output"))
            continue
        if any(
            part
            in {
                "security-threat-model-output",
                "threat-model-output",
                "security-review-output",
                "security-assessment-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".security-threat-model-report.json",
                ".security-threat-model-report.md",
                ".threat-model.md",
                ".security-boundary-map.md",
                ".security-review-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated security threat-model output"))
            continue
        if any(
            part
            in {
                "auth-boundary-audit-output",
                "permission-boundary-output",
                "auth-review-output",
                "permission-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".auth-boundary-audit-report.json",
                ".auth-boundary-audit-report.md",
                ".auth-boundary-map.md",
                ".permission-boundary-checklist.md",
                ".route-permission-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated auth-boundary output"))
            continue
        if any(
            part
            in {
                "webhook-security-review-output",
                "webhook-hardening-output",
                "webhook-replay-review-output",
                "webhook-signature-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".webhook-security-review-report.json",
                ".webhook-security-review-report.md",
                ".webhook-signature-boundary.md",
                ".webhook-replay-checklist.md",
                ".webhook-fixture-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated webhook security-review output"))
            continue
        if any(
            part
            in {
                "data-policy-review-output",
                "data-retention-redaction-output",
                "retention-redaction-output",
                "redaction-review-output",
                "data-classification-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".data-policy-review-report.json",
                ".data-policy-review-report.md",
                ".data-retention-map.md",
                ".redaction-boundary-map.md",
                ".generated-output-inventory.csv",
                ".data-handling-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated data-policy output"))
            continue
        if any(
            part
            in {
                "infra-security-review-output",
                "secrets-storage-db-review-output",
                "secret-storage-review-output",
                "database-security-review-output",
                "storage-security-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".infra-security-review-report.json",
                ".infra-security-review-report.md",
                ".secret-boundary-map.md",
                ".storage-boundary-map.md",
                ".database-boundary-map.md",
                ".infra-security-checklist.md",
                ".infra-provider-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated infrastructure-security output"))
            continue
        if any(
            part
            in {
                "supply-chain-review-output",
                "dependency-security-output",
                "dependency-review-output",
                "package-security-output",
                "sbom-review-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".supply-chain-review-report.json",
                ".supply-chain-review-report.md",
                ".dependency-boundary-map.md",
                ".optional-extras-matrix.csv",
                ".package-surface-map.md",
                ".supply-chain-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated supply-chain output"))
            continue
        if any(
            part
            in {
                "incident-response-review-output",
                "incident-review-output",
                "forensics-review-output",
                "audit-log-review-output",
                "security-incident-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".incident-response-review-report.json",
                ".incident-response-review-report.md",
                ".incident-runbook.md",
                ".audit-log-boundary-map.md",
                ".forensics-evidence-checklist.md",
                ".incident-scenario-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated incident-response output"))
            continue
        if any(
            part
            in {
                "security-gap-closeout-output",
                "security-closeout-output",
                "privacy-review-output",
                "encryption-guidance-output",
                "private-security-action-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".security-gap-closeout-report.json",
                ".security-gap-closeout-report.md",
                ".privacy-review-template.md",
                ".encryption-at-rest-guidance.md",
                ".policy-implementation-matrix.csv",
                ".private-security-action-register.md",
                ".known-limitations-closeout.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated security-gap closeout output"))
            continue
        if any(
            part
            in {
                "demo-data-output",
                "demo-seed-output",
                "demo-reset-output",
                "demo-db-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".demo-data-report.json",
                ".demo-data-report.md",
                ".demo-seed-plan.md",
                ".demo-reset-plan.md",
                ".demo-data-inventory.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated demo-data output"))
            continue
        if any(
            part
            in {
                "setup-experience-output",
                "installer-review-output",
                "first-run-output",
                "local-setup-output",
                "setup-diagnostics-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".setup-experience-report.json",
                ".setup-experience-report.md",
                ".first-run-checklist.md",
                ".local-installer-guide.md",
                ".setup-troubleshooting-guide.md",
                ".setup-command-map.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated setup-experience output"))
            continue
        if any(
            part
            in {
                "final-security-review-output",
                "security-readiness-output",
                "final-security-output",
                "private-security-review-output",
                "security-gate-output",
            }
            for part in path.parts
        ) or path.name.endswith(
            (
                ".final-security-review-report.json",
                ".final-security-review-report.md",
                ".security-readiness-summary.md",
                ".security-gap-register.md",
                ".private-security-review-checklist.md",
                ".security-domain-matrix.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated final-security output"))
            continue
        if path.name.endswith(
            (
                ".hosted-deployment-report.json",
                ".hosted-deployment-report.md",
                ".hosted-deployment-plan.md",
                ".platform-deployment-plan.md",
                ".container-deployment-plan.md",
                ".hosting-checklist.md",
                ".hosting-runbook.md",
                ".deployment-log",
            )
        ):
            issues.append(SafetyIssue(path, "tracked hosted deployment output"))
            continue
        if path.name.endswith(
            (
                ".operator-export.json",
                ".operator-export.md",
                ".operator-export.csv",
                ".review-export.json",
                ".review-export.md",
                ".review-export.csv",
                ".intake-summary-export.json",
                ".intake-summary-export.md",
                ".intake-summary-export.csv",
                ".lifecycle-summary-export.json",
                ".lifecycle-summary-export.md",
                ".lifecycle-summary-export.csv",
                ".triage-summary-export.json",
                ".triage-summary-export.md",
                ".triage-summary-export.csv",
                ".attachment-summary-export.json",
                ".attachment-summary-export.md",
                ".attachment-summary-export.csv",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated operator export output"))
            continue
        if path.name.endswith(
            (
                ".final-readiness-report.json",
                ".final-readiness-report.md",
                ".public-readiness-report.json",
                ".public-readiness-report.md",
                ".maintainer-handoff.md",
                ".public-repo-checklist.md",
                ".final-audit-summary.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked final public readiness output"))
            continue
        if path.name.endswith(
            (
                ".hosted-pilot-dry-run-report.json",
                ".hosted-pilot-dry-run-report.md",
                ".pilot-dry-run-checklist.md",
                ".pilot-dry-run-runbook.md",
                ".pilot-dry-run-evidence-map.md",
                ".pilot-dry-run-blockers.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked hosted pilot dry-run output"))
            continue
        if path.name.endswith(
            (
                ".https-webhook-report.json",
                ".https-webhook-report.md",
                ".webhook-ingress-plan.md",
                ".tls-plan.md",
                ".dns-plan.md",
                ".webhook-disable-plan.md",
                ".webhook-rollback-plan.md",
                ".webhook-evidence-ref.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked HTTPS/webhook planning output"))
            continue
        if path.suffix.casefold() == ".tf" or path.name in {
            "Pulumi.yaml",
            "Pulumi.yml",
            "Chart.yaml",
        }:
            issues.append(SafetyIssue(path, "tracked deployment automation"))
            continue
        if path.name.endswith((".migration-log", ".restore-log", ".backup-log")):
            issues.append(SafetyIssue(path, "tracked PostgreSQL operation log"))
            continue
        if path.name.endswith(
            (
                ".postgres-runtime-report.json",
                ".postgres-runtime-report.md",
                ".postgres-ops-report.json",
                ".postgres-ops-report.md",
                ".migration-execution-report.json",
                ".backup-verification-report.json",
                ".restore-drill-report.json",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated PostgreSQL operation output"))
            continue
        if path.name.endswith(
            (".smoke.txt", ".smoke.md", ".smoke.transcript", ".sandbox-smoke.json")
        ):
            issues.append(SafetyIssue(path, "tracked sandbox smoke transcript or report"))
            continue
        if path.name.endswith(
            (
                ".sandbox-evidence-link.json",
                ".sandbox-evidence-link.md",
                ".sandbox-evidence-summary.json",
                ".sandbox-evidence-summary.md",
                ".sandbox-evidence-manifest.json",
                ".sandbox-evidence-manifest.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated sandbox evidence-linkage output"))
            continue
        if path.name.endswith(
            (
                ".sandbox-read-report.json",
                ".sandbox-read-report.md",
                ".sandbox-read-evidence.json",
                ".sandbox-read-evidence.md",
                ".read-validation-report.json",
                ".read-validation-report.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated sandbox read-validation output"))
            continue
        if path.name.endswith((".docs-site-report.json", ".docs-site-report.md")):
            issues.append(SafetyIssue(path, "tracked generated docs-site report"))
            continue
        if path.name == "mkdocs.yml":
            try:
                config = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                config = ""
            if re.search(
                r"(?im)^\s*(?:site_url|google_analytics|analytics|extra_javascript)\s*:",
                config,
            ):
                issues.append(SafetyIssue(path, "docs config contains hosting or tracking config"))
                continue
        if path.name.endswith(
            (
                ".release-readiness-report.json",
                ".release-readiness-report.md",
                ".release-notes-draft.md",
                ".release-blockers.md",
                ".maintainer-review-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated release-readiness output"))
            continue
        if path.suffix.casefold() in {".whl", ".gz", ".tgz"}:
            issues.append(SafetyIssue(path, "tracked package or release archive"))
            continue
        if path.name.endswith(
            (
                ".mode-report.json",
                ".mode-report.md",
                ".doctor-report.json",
                ".doctor-report.md",
                ".quickstart-report.json",
                ".quickstart-report.md",
                ".usability-report.json",
                ".usability-report.md",
                ".first-run-report.json",
                ".first-run-report.md",
                ".sandbox-pilot-flow.json",
                ".sandbox-pilot-flow.md",
                ".flow-report.json",
                ".flow-report.md",
                ".pilot-preflight.json",
                ".pilot-preflight.md",
                ".sandbox-onboarding-report.json",
                ".sandbox-onboarding-report.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated usage-mode output"))
            continue
        if path.name.endswith(
            (
                ".secret",
                ".secret.txt",
                ".secrets.json",
                ".secrets.env",
                ".credential",
                ".credentials.json",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated secret or credential file"))
            continue
        if (
            path.name.endswith(
                (
                    ".private.json",
                    ".private.md",
                    ".private.env",
                    ".workspace-report.json",
                    ".workspace-report.md",
                    ".workspace-manifest.json",
                )
            )
            and "examples/private-workspace" not in path.as_posix()
        ):
            issues.append(SafetyIssue(path, "tracked generated private workspace output"))
            continue
        if path.name.endswith(
            (
                ".customer-profile.json",
                ".customer-deployment-report.json",
                ".customer-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated customer deployment output"))
            continue
        if path.name.endswith(
            (
                ".pilot-approval-packet.json",
                ".pilot-approval-packet.md",
                ".pilot-approval-summary.md",
                ".pilot-approval-manifest.json",
                ".pilot-signoff.md",
                ".risk-acceptance.md",
                ".launch-conditions.md",
                ".rollback-conditions.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated pilot approval output"))
            continue
        if path.name.endswith(
            (
                ".evidence-review.json",
                ".evidence-review.md",
                ".evidence-expiry-report.json",
                ".evidence-renewal-checklist.md",
                ".evidence-signoff.md",
                ".reviewer-signoff.json",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated evidence review output"))
            continue
        if path.name.endswith(
            (
                ".evidence-manifest.json",
                ".evidence-index.md",
                ".evidence-report.json",
                ".evidence-redaction-report.json",
                ".evidence-checklist.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated private evidence output"))
            continue
        if path.suffix.casefold() in {
            ".pdf",
            ".docx",
            ".xlsx",
            ".xls",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".zip",
        }:
            issues.append(SafetyIssue(path, "tracked binary evidence-capable file"))
            continue
        if path.name.endswith(
            (
                ".pilot-readiness.json",
                ".pilot-readiness.md",
                ".pilot-readiness-report.json",
                ".pilot-checklist.md",
                ".go-no-go.md",
            )
        ):
            issues.append(SafetyIssue(path, "tracked generated pilot readiness output"))
            continue
        if path.name.endswith(
            (
                ".support-bundle.json",
                ".support-bundle.md",
                ".support-bundle.log",
                ".diagnostics.json",
                ".diagnostics.md",
                ".diagnostics.log",
                ".redaction-report.json",
            )
        ):
            issues.append(SafetyIssue(path, "tracked diagnostics or support output"))
            continue
        if (
            any(part in PRIVATE_PATH_PARTS for part in path.parts)
            and "examples/private-workspace" not in path.as_posix()
        ):
            issues.append(SafetyIssue(path, "tracked private output path"))
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        issues.extend(audit_text(path, text))
    return issues


def repository_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit public text without printing discovered values."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    paths = args.paths or repository_files(root)
    issues = audit_paths(paths)
    for issue in issues:
        try:
            display = issue.path.relative_to(root)
        except ValueError:
            display = issue.path
        print(f"{display}: {issue.issue_type}")
    if issues:
        print(f"Public safety audit failed with {len(issues)} issue(s); values were suppressed.")
        return 1
    print(f"Public safety audit passed ({len(paths)} files inspected).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
