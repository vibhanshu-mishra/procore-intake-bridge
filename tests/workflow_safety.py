"""Test-only checks for pinned Actions and unsafe workflow operations."""

from __future__ import annotations

import re
from pathlib import Path

_ACTION_RULES = (
    (
        "release action",
        re.compile(
            r"^\s*uses:\s*(?:actions/create-release|actions/upload-release-asset|"
            r"ncipollo/release-action|release-drafter/release-drafter|"
            r"softprops/action-gh-release)(?:@|\s|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "package publish action",
        re.compile(
            r"^\s*uses:\s*(?:pypa/gh-action-pypi-publish)(?:@|\s|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "deployment action",
        re.compile(
            r"^\s*uses:\s*(?:actions/deploy-pages|amondnet/vercel-action|"
            r"aws-actions/aws-code-deploy|aws-actions/aws-s3-sync|"
            r"azure/webapps-deploy|chrnorm/deployment-action|"
            r"cloudflare/wrangler-action|google-github-actions/deploy-|"
            r"JamesIves/github-pages-deploy-action|netlify/actions/cli|"
            r"peaceiris/actions-gh-pages|serverless/github-action)(?:@|\s|$)",
            re.IGNORECASE,
        ),
    ),
)

_COMMAND_RULES = (
    (
        "release command",
        re.compile(r"\b(?:gh|hub)\s+release\s+(?:create|upload|edit|delete)\b", re.IGNORECASE),
    ),
    (
        "package publish command",
        re.compile(
            r"\b(?:python\s+-m\s+twine|twine)\s+upload\b|"
            r"\b(?:cargo|hatch|npm|pnpm|poetry|uv|yarn)\s+publish\b",
            re.IGNORECASE,
        ),
    ),
    ("container publish command", re.compile(r"\bdocker\s+push\b", re.IGNORECASE)),
    (
        "tag push command",
        re.compile(r"\bgit\s+push\b[^\n]*(?:--tags|\bv?\d+\.\d+\.\d+)\b", re.IGNORECASE),
    ),
    (
        "tag command",
        re.compile(
            r"\bgit\s+tag(?!\s+--(?:contains|list|merged|no-merged|points-at)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "deployment command",
        re.compile(
            r"\b(?:kubectl\s+apply|helm\s+(?:install|upgrade)|terraform\s+apply|"
            r"aws\s+s3\s+sync|az\s+webapp\s+deploy|"
            r"(?:flyctl|gcloud|netlify|serverless|vercel|wrangler)\s+deploy)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "package upload command",
        re.compile(
            r"\bcurl\b[^\n]*(?:--upload-file|\s-T\s|\s-X\s*POST\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "release target",
        re.compile(r"\bmake\s+(?:deploy|publish|release|tag)\b", re.IGNORECASE),
    ),
)

_DOCKER_PUSH_ACTION = re.compile(
    r"^\s*uses:\s*docker/build-push-action(?:@|\s|$)", re.IGNORECASE
)
_PUSH_TRUE = re.compile(r"^\s*push:\s*true\s*(?:#.*)?$", re.IGNORECASE | re.MULTILINE)
_USES_LINE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<value>.*?)\s*$", re.IGNORECASE)
_GITHUB_ACTION_PATH = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^@\s]+)?$")
_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def workflow_automation_findings(text: str) -> list[str]:
    """Return findings for executable release, upload, tag, or deployment operations."""

    findings: list[str] = []
    commands = _workflow_commands(text)
    for command in commands:
        for label, pattern in _COMMAND_RULES:
            if pattern.search(command):
                findings.append(f"{label}: {command}")
    for line in text.splitlines():
        for label, pattern in _ACTION_RULES:
            if pattern.search(line):
                findings.append(f"{label}: {line.strip()}")
        if _DOCKER_PUSH_ACTION.search(line) and _PUSH_TRUE.search(text):
            findings.append(f"container publish action: {line.strip()}")
    return findings


def workflow_directory_findings(workflow_dir: Path) -> list[str]:
    """Inspect workflow files for unsafe operations and mutable action references."""

    if not workflow_dir.is_dir():
        return []
    findings: list[str] = []
    for path in sorted(workflow_dir.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text()
        findings.extend(workflow_automation_findings(text))
        findings.extend(workflow_action_pin_findings(text))
    return findings


def workflow_action_pin_findings(text: str) -> list[str]:
    """Return findings for external GitHub Actions that do not use a full commit SHA."""

    findings: list[str] = []
    for line in text.splitlines():
        match = _USES_LINE.match(line)
        if match is None:
            continue
        reference = _without_yaml_comment(match.group("value")).strip()
        if len(reference) >= 2 and reference[0] == reference[-1] and reference[0] in "\"'":
            reference = reference[1:-1].strip()
        if not reference or reference.startswith(("./", "docker://")):
            continue

        action, separator, ref = reference.rpartition("@")
        if not separator or not _GITHUB_ACTION_PATH.fullmatch(action):
            findings.append(f"invalid or unpinned external GitHub Action: {reference}")
        elif not _COMMIT_SHA.fullmatch(ref):
            findings.append(
                f"external GitHub Action is not pinned to a full commit SHA: {reference}"
            )
    return findings


def _workflow_commands(text: str) -> list[str]:
    commands: list[str] = []
    in_run_block = False
    run_indent = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip())
        if in_run_block:
            if stripped and indent <= run_indent and not stripped.startswith("#"):
                in_run_block = False
            else:
                if stripped and not stripped.startswith("#"):
                    commands.extend(_command_segments(stripped))
                continue
        match = re.match(r"^(?P<indent>\s*)run:\s*(?P<value>.*)$", raw_line)
        if not match:
            continue
        value = match.group("value").strip()
        if value in {"|", ">", "|-", ">-", "|+", ">+"}:
            in_run_block = True
            run_indent = len(match.group("indent"))
        elif value and not value.startswith("#"):
            commands.extend(_command_segments(value))
    return commands


def _command_segments(command: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(r"(?:&&|\|\||;)", command)
        if segment.strip() and not segment.strip().startswith("echo ")
    ]


def _without_yaml_comment(value: str) -> str:
    quote: str | None = None
    for index, character in enumerate(value):
        if quote is not None:
            if character == quote:
                quote = None
        elif character in "\"'":
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value
