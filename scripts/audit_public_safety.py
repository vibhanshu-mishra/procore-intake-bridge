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
    "downloads",
    "customer-deployment-output",
    "customer-output",
    "diagnostics-output",
    "logs",
    "onboarding-output",
    "packet-output",
    "pilot-output",
    "pilot-readiness-output",
    "storage",
    "smoke-output",
    "support-output",
    "sandbox-output",
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
GENERIC_SIGNED_URL = re.compile(
    r"(?i)https?://[^\s\"']+[?&](signature|signed|token|expires)="
)
OBSERVABILITY_CREDENTIAL = re.compile(
    r"(?i)(?:sentry_dsn|datadog_api_key|new_relic_license_key|honeycomb_api_key)"
    r"\s*[:=]\s*[^\s\"']+"
)


def _safe_value(value: str) -> bool:
    lowered = value.casefold()
    return (
        any(marker in lowered for marker in SAFE_MARKERS)
        or value.startswith(("${", "{"))
    )


def audit_text(path: Path, text: str) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
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
    return issues


def audit_paths(paths: list[Path]) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    for path in paths:
        if path.name in SKIP_NAMES or not path.is_file():
            continue
        if path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}:
            issues.append(SafetyIssue(path, "tracked local database file"))
            continue
        if path.name.endswith((".smoke.json", ".smoke.log")):
            issues.append(SafetyIssue(path, "tracked sandbox smoke output"))
            continue
        if path.name.endswith((
            ".customer-profile.json",
            ".customer-deployment-report.json",
            ".customer-checklist.md",
        )):
            issues.append(SafetyIssue(path, "tracked generated customer deployment output"))
            continue
        if path.name.endswith((
            ".pilot-readiness.json",
            ".pilot-readiness.md",
            ".pilot-readiness-report.json",
            ".pilot-checklist.md",
            ".go-no-go.md",
        )):
            issues.append(SafetyIssue(path, "tracked generated pilot readiness output"))
            continue
        if path.name.endswith((
            ".support-bundle.json",
            ".support-bundle.md",
            ".support-bundle.log",
            ".diagnostics.json",
            ".diagnostics.md",
            ".diagnostics.log",
            ".redaction-report.json",
        )):
            issues.append(SafetyIssue(path, "tracked diagnostics or support output"))
            continue
        if any(part in PRIVATE_PATH_PARTS for part in path.parts):
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
