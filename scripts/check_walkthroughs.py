#!/usr/bin/env python3
"""Verify guided walkthrough completeness and public-safe content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WALKTHROUGHS = {
    "docs/walkthrough-index.md",
    "docs/walkthrough-demo.md",
    "docs/walkthrough-sandbox.md",
    "docs/walkthrough-pilot.md",
}
EXPECTED_OUTPUTS = {
    "examples/walkthrough-output/README.md",
    "examples/walkthrough-output/demo_expected_output.md",
    "examples/walkthrough-output/sandbox_expected_output.md",
    "examples/walkthrough-output/pilot_expected_output.md",
}
UNSAFE = re.compile(
    r"(?ix)(?:"
    r"https?://|"
    r"(?:postgres(?:ql)?|mysql|mariadb|mongodb|sqlite)://|"
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|"
    r"(?:/Users/|/home/[^/\s]+/|[A-Z]:\\Users\\)|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?(?:PRIVATE KEY|CERTIFICATE)-----|"
    r"(?:client_secret|admin_token|webhook_secret|app_version_key)\s*[:=]\s*"
    r"(?![A-Z_]*PLACEHOLDER)[^\s]+|"
    r"\b(?:company|project)[_-]?id\s*[:=]\s*\d{4,}\b|"
    r"\+?\d[\d(). -]{8,}\d"
    r")"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")


@dataclass(frozen=True)
class WalkthroughFinding:
    level: str
    check: str
    message: str


def _read(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def check_walkthroughs(root: Path = ROOT) -> list[WalkthroughFinding]:
    findings: list[WalkthroughFinding] = []

    def add(level: str, check: str, message: str) -> None:
        findings.append(WalkthroughFinding(level, check, message))

    required = WALKTHROUGHS | EXPECTED_OUTPUTS
    for relative in sorted(required):
        exists = (root / relative).is_file()
        add(
            "PASS" if exists else "FAIL",
            f"required file: {relative}",
            "present" if exists else "missing",
        )

    navigation = {
        "README walkthrough link": ("README.md", "docs/walkthrough-index.md"),
        "QUICKSTART walkthrough link": ("QUICKSTART.md", "docs/walkthrough-index.md"),
        "docs index walkthrough link": ("docs/index.md", "walkthrough-index.md"),
        "command reference Demo link": (
            "docs/command-reference.md",
            "walkthrough-demo.md",
        ),
        "command reference Sandbox link": (
            "docs/command-reference.md",
            "walkthrough-sandbox.md",
        ),
        "command reference Pilot link": (
            "docs/command-reference.md",
            "walkthrough-pilot.md",
        ),
    }
    for check, (relative, marker) in navigation.items():
        passed = marker in _read(root, relative)
        add("PASS" if passed else "FAIL", check, "linked" if passed else "link missing")

    demo = _read(root, "docs/walkthrough-demo.md").casefold()
    sandbox = _read(root, "docs/walkthrough-sandbox.md").casefold()
    pilot = _read(root, "docs/walkthrough-pilot.md").casefold()
    content_checks = {
        "Demo friendly flow": all(
            command in demo
            for command in ("make start", "make try-demo", "make doctor", "make commands")
        ),
        "Demo safety boundary": all(
            phrase in demo
            for phrase in ("no procore credentials", "no secrets", "no external database")
        ),
        "Sandbox friendly flow": all(
            command in sandbox
            for command in ("make start", "make init-private-workspace", "make prepare-sandbox")
        ),
        "Sandbox private DMSA boundary": "private dmsa" in sandbox,
        "Sandbox no-live default": (
            "run live smoke by default" in sandbox and "does not" in sandbox
        ),
        "Sandbox smoke UX commands": all(
            command in sandbox
            for command in (
                "make sandbox-smoke-explain",
                "make sandbox-smoke-preflight",
                "make sandbox-smoke-evidence-template",
            )
        ),
        "Sandbox read-validation offline commands": all(
            command in sandbox
            for command in (
                "make sandbox-read-plan",
                "make sandbox-read-preflight",
                "make sandbox-read-evidence-template",
            )
        ),
        "Sandbox read validation is not a default step": (
            "make sandbox-read-validation" in sandbox
            and "do not run it as part of this walkthrough" in sandbox
        ),
        "Sandbox read validation safety": all(
            phrase in sandbox
            for phrase in (
                "writes nothing to procore",
                "registers no webhooks",
                "downloads no attachments by default",
                "stores no raw payloads",
            )
        ),
        "Pilot friendly flow": all(
            command in pilot
            for command in ("make start", "make init-private-workspace", "make prepare-pilot")
        ),
        "Pilot private boundary": all(
            term in pilot for term in ("private workspace", "evidence", "approval")
        ),
        "Pilot no-real-approval boundary": "does not approve a real pilot" in pilot,
        "Pilot private smoke evidence ref": "sandbox_smoke_ref_placeholder" in pilot,
        "Pilot private read-validation evidence ref": (
            "sandbox_read_validation_ref_placeholder" in pilot
        ),
    }
    for check, passed in content_checks.items():
        add("PASS" if passed else "FAIL", check, "documented" if passed else "guidance missing")

    walkthrough_text = "\n".join(_read(root, relative).casefold() for relative in WALKTHROUGHS)
    unsafe_defaults = {
        "live smoke is not a default step": (
            "make try-demo" in demo
            and "do not run it as part of this walkthrough" in sandbox
        ),
        "deployment is not a default step": (
            "does not" in pilot and "deploy" in pilot and "launch hold" in pilot
        ),
        "private workspace is never committed": (
            "outside git" in walkthrough_text and "never paste credentials" in sandbox
        ),
    }
    for check, passed in unsafe_defaults.items():
        add("PASS" if passed else "FAIL", check, "safe" if passed else "unsafe default guidance")

    for relative in sorted(EXPECTED_OUTPUTS):
        text = _read(root, relative)
        if UNSAFE.search(text):
            add("FAIL", f"safe example: {relative}", "unsafe public pattern detected")
        else:
            add("PASS", f"safe example: {relative}", "placeholder-safe")
        if relative != "examples/walkthrough-output/README.md":
            placeholder = "PLACEHOLDER" in text
            add(
                "PASS" if placeholder else "FAIL",
                f"placeholder example: {relative}",
                "uses placeholders" if placeholder else "placeholder marker missing",
            )

    for relative in sorted(WALKTHROUGHS):
        source = root / relative
        for target in MARKDOWN_LINK.findall(_read(root, relative)):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            exists = (source.parent / target).resolve().exists()
            if not exists:
                add("FAIL", f"internal links: {relative}", f"broken link: {target}")
        add("PASS", f"internal links: {relative}", "checked")
    return findings


def main() -> int:
    findings = check_walkthroughs()
    counts = {
        level: sum(item.level == level for item in findings)
        for level in ("PASS", "WARN", "FAIL")
    }
    print("Walkthrough verification")
    print("========================")
    for item in findings:
        if item.level != "PASS":
            print(f"[{item.level}] {item.check}: {item.message}")
    print(f"\nSummary: {counts['PASS']} passed, {counts['WARN']} warned, {counts['FAIL']} failed.")
    if counts["FAIL"]:
        print("Result: FAIL — correct the named public walkthrough checks.")
        return 1
    print("Result: PASS — walkthroughs are complete, linked, and placeholder-safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
