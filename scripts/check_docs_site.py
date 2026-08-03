#!/usr/bin/env python3
"""Validate the local documentation-site foundation without building or publishing it."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REQUIRED_GROUPS = {
    "Start Here",
    "Choose Your Mode",
    "Demo Mode",
    "Sandbox Mode",
    "Pilot Mode",
    "Providers and Infrastructure",
    "Operations",
    "Public Safety and Release",
}
REQUIRED_NAV_DOCS = {
    "index.md",
    "quickstart-site.md",
    "command-reference.md",
    "troubleshooting.md",
    "usage-modes.md",
    "walkthrough-demo.md",
    "walkthrough-sandbox.md",
    "walkthrough-pilot.md",
    "sandbox-read-validation.md",
    "sandbox-read-evidence.md",
    "sandbox-evidence-linkage.md",
    "sandbox-evidence-to-pilot.md",
    "sandbox-to-pilot-flow.md",
    "cloud-secret-providers.md",
    "aws-secrets-manager.md",
    "azure-key-vault-secrets.md",
    "gcp-secret-manager.md",
    "cloud-storage-providers.md",
    "s3-storage.md",
    "azure-blob-storage.md",
    "gcs-storage.md",
    "postgres-runtime-operations.md",
    "postgres-connection-pooling.md",
    "postgres-migration-runbook.md",
    "postgres-backup-restore-drills.md",
    "hosted-deployment-templates.md",
    "docker-vps-hosting.md",
    "managed-paas-hosting.md",
    "container-platform-hosting.md",
    "cloud-platform-hosting.md",
    "https-webhook-production-planning.md",
    "webhook-ingress-planning.md",
    "tls-dns-planning.md",
    "webhook-disable-rollback.md",
    "hosted-pilot-dry-run.md",
    "pilot-operations-rehearsal.md",
    "hosted-pilot-evidence-map.md",
    "final-public-readiness.md",
    "public-repository-handoff.md",
    "final-readiness-checklist.md",
    "maintainer-review-fix-pack.md",
    "intake-review-workspace.md",
    "intake-lifecycle-status-flow.md",
    "operator-triage-queue.md",
    "attachment-review-manifest-ux.md",
    "operator-export-pack.md",
    "product-dashboard.md",
    "demo-product-walkthrough.md",
    "demo-evaluation-checklist.md",
    "security-threat-model.md",
    "security-boundary-map.md",
    "security-review-checklist.md",
    "auth-permission-boundary-audit.md",
    "auth-boundary-map.md",
    "permission-boundary-checklist.md",
    "webhook-replay-signature-hardening.md",
    "webhook-signature-boundary.md",
    "webhook-replay-checklist.md",
    "data-retention-redaction-policy.md",
    "data-retention-map.md",
    "redaction-boundary-map.md",
    "data-handling-checklist.md",
    "secrets-storage-db-security-review.md",
    "secret-boundary-map.md",
    "storage-boundary-map.md",
    "database-boundary-map.md",
    "infra-security-checklist.md",
    "dependency-supply-chain-security.md",
    "dependency-boundary-map.md",
    "package-surface-map.md",
    "supply-chain-checklist.md",
    "incident-response-forensics.md",
    "incident-runbook.md",
    "audit-log-boundary-map.md",
    "forensics-evidence-checklist.md",
    "final-security-readiness-review.md",
    "security-readiness-summary.md",
    "security-gap-register.md",
    "private-security-review-checklist.md",
    "security-gap-closeout.md",
    "privacy-review-template.md",
    "encryption-at-rest-guidance.md",
    "private-security-action-register.md",
    "known-limitations-closeout.md",
    "local-installer-guide.md",
    "first-run-checklist.md",
    "setup-troubleshooting-guide.md",
    "setup-experience-review.md",
    "demo-data-seed-reset.md",
    "demo-seed-plan.md",
    "demo-reset-guide.md",
    "api-route-reference.md",
    "api-usage-examples.md",
    "openapi-local-guide.md",
    "api-docs-review.md",
    "hosted-ui-preparation.md",
    "hosted-ui-page-inventory.md",
    "hosted-ui-readiness-checklist.md",
    "hosted-ui-private-gates.md",
    "docs-site-polish.md",
    "docs-reader-paths.md",
    "docs-navigation-map.md",
    "package-metadata-summary.md",
    "version-source-map.md",
    "release-boundary-checklist.md",
    "version-prep-review.md",
    "release-candidate-review.md",
    "release-candidate-checklist.md",
    "release-candidate-gap-register.md",
    "release-candidate-command-plan.md",
    "versioned-release-handoff.md",
    "release-notes-v0.1.0.md",
    "release-scope-summary.md",
    "maintainer-release-decision-checklist.md",
    "post-release-checklist.md",
    "maintainer-handoff.md",
    "maintainer-quickstart.md",
    "maintainer-review-checklist.md",
    "maintainer-command-plan.md",
    "maintainer-decision-log-template.md",
    "release-readiness.md",
    "release-checklist.md",
    "release-notes-template.md",
    "safety-model.md",
    "project-status.md",
    "roadmap.md",
    "post-release-roadmap.md",
    "known-limitations-register.md",
    "future-work-backlog.md",
    "private-review-backlog.md",
    "pre-tag-reminder-checklist.md",
}
FORBIDDEN_CONFIG = re.compile(
    r"(?im)^\s*(?:site_url|google_analytics|analytics|extra_javascript|remote_branch|"
    r"repo_url|edit_uri)\s*:"
)
UNSAFE_TEXT = re.compile(
    r"(?i)(?:"
    r"https?://|(?:postgres(?:ql)?|mysql|mariadb)://|"
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|"
    r"(?:/Users/|/home/[^/\s]+/|/private/|/tmp/|[A-Z]:\\Users\\)|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)-----|"
    r"(?:client_secret|admin_token|webhook_secret|app_version_key)\s*[:=]|"
    r"\b(?:company|project)[_-]?id\s*[:=]\s*[0-9]{4,}"
    r")"
)
NAV_DOC = re.compile(r"(?m)^\s+-\s+[^:\n]+:\s+([a-zA-Z0-9_./-]+\.md)\s*$")
NAV_GROUP = re.compile(r"(?m)^\s{2}-\s+([^:\n]+):\s*$")
J10_UNSAFE_CLAIM = re.compile(
    r"(?i)\b(?:issue(?:[/ -]ticket)?|ticket)(?:\s+[#A-Z0-9_-]+)? "
    r"(?:was |has been |is )?(?:created|opened|filed|closed|resolved)|"
    r"\b(?:tag|release|package build|publish|upload|deployment|deploy) "
    r"(?:was |has been |is )?(?:created|completed|performed|executed|done|"
    r"published|deployed|happened|occurred|succeeded)|"
    r"\b(?:package|version) (?:was |has been |is )?published|"
    r"\bpackage publication (?:completed|occurred|performed)|"
    r"\b(?:application|app|docs) (?:was |has been |is )?(?:deployed|hosted)|"
    r"\b(?:production|pilot|release|deployment) (?:(?:is|was|has been) )?approved|"
    r"\b(?:production|pilot|release|deployment) approval (?:granted|complete|recorded)|"
    r"\bapproved for (?:production|pilot|release|deployment)|"
    r"\b(?:production|pilot|release|deployment)[- ]ready|"
    r"\b(?:security|compliance|privacy|legal) (?:is )?certified|"
    r"\b(?:gdpr|ccpa|hipaa) compliant\b"
)
J10_NEGATION = re.compile(
    r"(?i)\b(?:no|not|never|without|does not|do not|is not|isn't|out of scope|"
    r"future|later|planned|placeholder|tbd)\b"
)


@dataclass(frozen=True)
class Finding:
    level: str
    check: str
    message: str


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _tracked_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def check_docs_site(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    def add(passed: bool, check: str, failure: str) -> None:
        findings.append(
            Finding("PASS" if passed else "FAIL", check, "valid" if passed else failure)
        )

    config_path = root / "mkdocs.yml"
    config = _read(config_path)
    add(config_path.is_file(), "mkdocs config", "mkdocs.yml is missing")
    if not config:
        return findings

    groups = set(NAV_GROUP.findall(config))
    nav_docs = set(NAV_DOC.findall(config))
    add(REQUIRED_GROUPS <= groups, "required nav groups", "one or more nav groups are missing")
    add(REQUIRED_NAV_DOCS <= nav_docs, "required nav docs", "one or more required docs are absent")
    j8_nav_docs = {
        "versioned-release-handoff.md",
        "release-notes-v0.1.0.md",
        "release-scope-summary.md",
        "maintainer-release-decision-checklist.md",
        "post-release-checklist.md",
    }
    add(
        j8_nav_docs <= nav_docs,
        "J8 docs navigation",
        "versioned release handoff docs are not in the local nav",
    )
    j9_nav_docs = {
        "maintainer-handoff.md",
        "maintainer-quickstart.md",
        "maintainer-review-checklist.md",
        "maintainer-command-plan.md",
        "maintainer-decision-log-template.md",
    }
    add(
        j9_nav_docs <= nav_docs,
        "J9 docs navigation",
        "maintainer handoff docs are not in the local nav",
    )
    j10_nav_docs = {
        "post-release-roadmap.md",
        "known-limitations-register.md",
        "future-work-backlog.md",
        "private-review-backlog.md",
        "pre-tag-reminder-checklist.md",
    }
    add(
        j10_nav_docs <= nav_docs,
        "J10 docs navigation",
        "post-release roadmap docs are not in the local nav",
    )

    missing = sorted(name for name in nav_docs if not (root / "docs" / name).is_file())
    add(not missing, "nav targets", "one or more nav targets do not exist")
    add(
        not FORBIDDEN_CONFIG.search(config),
        "hosting and tracking config",
        "forbidden config found",
    )
    add(not UNSAFE_TEXT.search(config), "config public safety", "unsafe config value found")

    j8_docs = [root / "docs" / name for name in (
        "versioned-release-handoff.md",
        "release-notes-v0.1.0.md",
        "release-scope-summary.md",
        "maintainer-release-decision-checklist.md",
        "post-release-checklist.md",
    )]
    j8_text = "\n".join(_read(path).casefold() for path in j8_docs if path.is_file())
    add(
        all(path.is_file() for path in j8_docs),
        "J8 docs present",
        "versioned release handoff docs are missing",
    )
    add(
        all(
            phrase in j8_text
            for phrase in (
                "0.1.0",
                "no package build",
                "no publish",
                "no upload",
                "no tag",
                "no release",
                "no deployment",
                "maintainer authorization",
                "not granted",
            )
        ),
        "J8 public safety guidance",
        "J8 docs must disclaim live operations and approval",
    )
    j9_docs = [root / "docs" / name for name in sorted(j9_nav_docs)]
    j9_text = "\n".join(_read(path).casefold() for path in j9_docs if path.is_file())
    add(
        all(path.is_file() for path in j9_docs),
        "J9 docs present",
        "maintainer handoff docs are missing",
    )
    add(
        all(
            phrase in j9_text
            for phrase in (
                "no release happened",
                "no build happened",
                "no tag happened",
                "no publish happened",
                "upload happened",
                "no deployment happened",
                "offline",
                "no procore",
                "workflows",
                "maintainer review",
                "private review",
                "not approval",
            )
        ),
        "J9 public safety guidance",
        "J9 docs must disclaim live operations and approval",
    )
    j10_docs = [root / "docs" / name for name in sorted(j10_nav_docs)]
    j10_text = "\n".join(_read(path).casefold() for path in j10_docs if path.is_file())
    add(
        all(path.is_file() for path in j10_docs),
        "J10 docs present",
        "post-release roadmap docs are missing",
    )
    add(
        all(
            phrase in j10_text
            for phrase in (
                "future work",
                "known limitations",
                "offline",
                "no release",
                "no build",
                "no publish",
                "no tag",
                "no deployment",
                "no issue",
                "no ticket",
                "private review",
                "not approval",
            )
        ),
        "J10 public safety guidance",
        "J10 docs must keep roadmap planning offline and non-operational",
    )
    j10_claim = False
    for path in j10_docs:
        lines = _read(path).splitlines()
        for line in lines:
            if J10_UNSAFE_CLAIM.search(line) and not J10_NEGATION.search(line):
                j10_claim = True
                break
        if j10_claim:
            break
    add(
        not j10_claim,
        "J10 no issue, ticket, release, or approval claims",
        "unqualified live claim found",
    )

    links = {
        "README docs-site link": (root / "README.md", "docs/docs-site.md"),
        "QUICKSTART docs-site link": (root / "QUICKSTART.md", "docs/docs-site.md"),
        "docs index docs-site link": (root / "docs/index.md", "docs-site.md"),
    }
    for label, (path, marker) in links.items():
        add(marker in _read(path), label, "required link is missing")

    tracked = _tracked_files(root)
    generated = [
        name
        for name in tracked
        if Path(name).parts[:1] in {("site",), ("docs-site-output",), ("mkdocs-site-output",)}
        or name.endswith(
            (
                ".docs-site-report.json",
                ".docs-site-report.md",
                ".post-release-roadmap-report.json",
                ".post-release-roadmap-report.md",
                ".known-limitations-register.md",
                ".future-work-backlog.md",
                ".private-review-backlog.md",
                ".pre-tag-reminder-checklist.md",
                ".post-release-roadmap-matrix.csv",
            )
        )
    ]
    add(not generated, "generated site output", "generated site output is tracked")

    workflow_dir = root / ".github/workflows"
    deployment_workflows: list[str] = []
    if workflow_dir.is_dir():
        for path in workflow_dir.glob("*"):
            text = _read(path).casefold()
            if any(term in text for term in ("mkdocs gh-deploy", "gh-pages", "pages deploy")):
                deployment_workflows.append(path.name)
    add(not deployment_workflows, "GitHub Pages automation", "docs deployment workflow found")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = check_docs_site(args.root.resolve())
    counts = {
        level: sum(item.level == level for item in findings) for level in ("PASS", "WARN", "FAIL")
    }
    print("Documentation site check")
    print("========================")
    for item in findings:
        print(f"{item.level}: {item.check} — {item.message}")
    print(f"\nSummary: {counts['PASS']} passed, {counts['WARN']} warned, {counts['FAIL']} failed.")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
