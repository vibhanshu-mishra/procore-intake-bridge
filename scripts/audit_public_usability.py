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
}
REQUIRED_TARGETS = {
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
}
IGNORED_OUTPUTS = {
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
}
UNSAFE_SUFFIXES = {
    ".bak", ".backup", ".crt", ".csr", ".db", ".docx", ".dump", ".gif",
    ".jpeg", ".jpg", ".key", ".log", ".p12", ".pdf", ".pem", ".pfx", ".png",
    ".sql", ".sqlite", ".sqlite3", ".webp", ".xlsx", ".zip",
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
    return [
        item.decode("utf-8", errors="replace")
        for item in result.stdout.split(b"\0")
        if item
    ]


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
        _read(root, path).casefold()
        for path in REQUIRED_DOCS
        if (root / path).is_file()
    )
    quality_header = next(
        (line for line in makefile.splitlines() if line.startswith("quality:")),
        "",
    )
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
            "never contact cloud"
            in _read(root, "docs/cloud-storage-providers.md").casefold()
        ),
        "cloud storage excludes presigned URLs": (
            "no presigned url"
            in _read(root, "docs/cloud-storage-providers.md").casefold()
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
            "make start" in quickstart
            and "run_sandbox_dmsa_smoke.py" not in quickstart
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
            "offline planning"
            in _read(root, "docs/sandbox-smoke-ux.md").casefold()
            and "never invokes the live command"
            in _read(root, "docs/sandbox-smoke-ux.md").casefold()
        ),
        "live smoke remains manually gated": (
            "manual live read-only execution"
            in _read(root, "docs/sandbox-smoke-ux.md").casefold()
        ),
        "smoke evidence refs remain private": (
            "outside git"
            in _read(root, "docs/sandbox-smoke-evidence.md").casefold()
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
        "docs index docs-site link": (
            "docs-site.md" in _read(root, "docs/index.md").casefold()
        ),
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
        if public_content and candidate.is_file() and candidate.suffix.casefold() in {
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
        }:
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
        level: sum(item.level == level for item in findings)
        for level in ("PASS", "WARN", "FAIL")
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
