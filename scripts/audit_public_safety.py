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
    "sandbox-output",
    "sandbox-pilot-output",
    "pilot-flow-output",
    "flow-output",
    "sandbox-workspace",
    "secrets.local",
    ".local-secrets",
    "sync-output",
    "tokens",
}


@dataclass(frozen=True)
class SafetyIssue:
    path: Path
    issue_type: str


SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    ["']?(access_token|refresh_token|client_secret|webhook_secret|admin_token|
    app_version_key)["']?\s*[:=]\s*["']([^"'\r\n]+)["']
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


def _safe_value(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in SAFE_MARKERS) or value.startswith(("${", "{"))


def audit_text(path: Path, text: str) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    if path.suffix.casefold() == ".js" and re.search(
        r"(?i)(?:https?://|google-analytics|googletagmanager|segment\.com|mixpanel)",
        text,
    ):
        issues.append(SafetyIssue(path, "external analytics or tracking JavaScript"))
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
