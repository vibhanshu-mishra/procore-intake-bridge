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
    "release-readiness.md",
    "release-checklist.md",
    "release-notes-template.md",
    "safety-model.md",
    "project-status.md",
    "roadmap.md",
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

    missing = sorted(name for name in nav_docs if not (root / "docs" / name).is_file())
    add(not missing, "nav targets", "one or more nav targets do not exist")
    add(
        not FORBIDDEN_CONFIG.search(config),
        "hosting and tracking config",
        "forbidden config found",
    )
    add(not UNSAFE_TEXT.search(config), "config public safety", "unsafe config value found")

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
        or name.endswith((".docs-site-report.json", ".docs-site-report.md"))
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
        level: sum(item.level == level for item in findings)
        for level in ("PASS", "WARN", "FAIL")
    }
    print("Documentation site check")
    print("========================")
    for item in findings:
        print(f"{item.level}: {item.check} — {item.message}")
    print(
        f"\nSummary: {counts['PASS']} passed, {counts['WARN']} warned, "
        f"{counts['FAIL']} failed."
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
