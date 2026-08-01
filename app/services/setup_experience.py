import csv
import io
import json
import re
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.setup_experience import (
    SetupCommand,
    SetupCommandMapItem,
    SetupExperienceArtifactResult,
    SetupExperienceDecision,
    SetupExperienceFinding,
    SetupExperienceReport,
    SetupExperienceStatus,
    SetupExperienceStep,
    SetupModePath,
    SetupPrerequisite,
    SetupTroubleshootingItem,
)


class SetupExperienceError(ValueError):
    pass


class SetupExperienceBlockedError(SetupExperienceError):
    pass


IGNORED_OUTPUTS = (
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
)
SAFE_ROOTS = {item.rstrip("/") for item in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "setup-experience-report.json",
    "setup-experience-report.md",
    "first-run-checklist.md",
    "local-installer-guide.md",
    "setup-troubleshooting-guide.md",
    "setup-command-map.csv",
    "manifest.json",
)

URL_PATTERN = re.compile(r"(?i)\b(?:https?|s3|gs|postgres|postgresql)://\S+")
EMAIL_PATTERN = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{8,}\d)(?!\w)")
DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|dev|cloud|app|co)\b"
)
LONG_ID_PATTERN = re.compile(r"(?<![\w.-])[A-Za-z0-9]{20,}(?![\w.-])")
PRIVATE_PATH_PATTERN = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
SECRET_PATTERN = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:github_token|registry_token|"
    r"package_registry_token|publish_token|ci_secret|release_signing_key|admin_token|"
    r"webhook_secret|dmsa_(?:client_id|client_secret)|database_url|signed_url|"
    r"presigned_url|source_url|storage_key|object_key|cloud_(?:account_)?id)\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+)"
)
PRIVATE_MATERIAL_PATTERN = re.compile(
    r"(?i)(?:private_report_contents|raw_log|raw_payload|db_dump_content|"
    r"backup_manifest|live_webhook_(?:headers|payload))\s*[:=]\s*"
    r"(?!false|none|placeholder)\S+"
)
UNSAFE_CLAIM_PATTERN = re.compile(
    r"(?i)\bproduction[- ]ready\b|\b(?:production|launch|pilot|release|deployment) "
    r"approved\b|\bapproved for (?:production|launch|pilot|release|deployment)\b|"
    r"\b(?:production|pilot|release) approval (?:granted|complete)\b|"
    r"\b(?:soc ?2|iso ?27001|security|compliance) certified\b|"
    r"\b(?:gdpr|ccpa|hipaa|slsa|sbom|privacy|legally) compliant\b|"
    r"\bprocore (?:endorsed|partner|certified)\b"
)
NEGATION_PATTERN = re.compile(
    r"(?i)\b(?:no|not|never|does not|is not|without|false|out of scope|"
    r"not implied|requires separate|remain(?:s)? gated)\b"
)
DEMO_SECRET_REQUIREMENT_PATTERN = re.compile(
    r"(?i)demo(?: mode)?.{0,80}(?:requires?|must (?:set|provide|use)).{0,40}"
    r"(?:secret|credential|token|dmsa|procore)"
)
MODE_BLUR_PATTERN = re.compile(
    r"(?i)demo(?: mode)?.{0,60}(?:is|equals|same as|becomes).{0,20}"
    r"(?:sandbox|pilot|hosted|production)"
)
FORBIDDEN_KEYS = {
    "authorization",
    "admin_token",
    "webhook_secret",
    "github_token",
    "registry_token",
    "package_registry_token",
    "publish_token",
    "ci_secret",
    "release_signing_key",
    "database_url",
    "source_url",
    "signed_url",
    "presigned_url",
    "storage_key",
    "object_key",
    "cloud_id",
    "cloud_account_id",
    "cloud_resource_id",
    "private_path",
    "report_contents",
    "private_report_contents",
    "customer_name",
    "company_name",
    "reviewer_name",
    "approver_name",
    "operator_name",
    "real_domain",
}


def sanitize_setup_experience_value(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        LONG_ID_PATTERN,
        PRIVATE_PATH_PATTERN,
        SECRET_PATTERN,
        PRIVATE_MATERIAL_PATTERN,
    )
    return "[redacted]" if any(pattern.search(text) for pattern in patterns) else text[:400]


def build_setup_prerequisites(settings: Settings) -> list[SetupPrerequisite]:
    del settings
    rows = (
        (
            "git",
            SetupExperienceStep.REPOSITORY_LOCATION,
            "git --version",
            "Install git and ensure it is available on PATH.",
        ),
        (
            "python",
            SetupExperienceStep.PYTHON_PREREQUISITES,
            "python3 --version",
            "Install a supported Python version and ensure python3 is available on PATH.",
        ),
        (
            "pip",
            SetupExperienceStep.DEPENDENCY_INSTALL,
            "python3 -m pip --version",
            (
                "Use the selected Python interpreter to locate pip; bootstrap pip locally "
                "if it is missing."
            ),
        ),
        (
            "make",
            SetupExperienceStep.REPOSITORY_LOCATION,
            "make --version",
            "Install make and ensure it is available on PATH.",
        ),
    )
    return [
        SetupPrerequisite(
            name=name,
            step=step,
            available=shutil.which("python3" if name in {"python", "pip"} else name) is not None,
            check_command=command,
            guidance=guidance,
        )
        for name, step, command, guidance in rows
    ]


def build_setup_commands(settings: Settings) -> list[SetupCommand]:
    del settings
    rows = (
        (
            "locate-repository",
            SetupExperienceStep.REPOSITORY_LOCATION,
            "pwd",
            "Confirm the local repository location.",
        ),
        (
            "check-python",
            SetupExperienceStep.PYTHON_PREREQUISITES,
            "python3 --version",
            "Confirm the supported Python interpreter.",
        ),
        (
            "create-environment",
            SetupExperienceStep.VIRTUAL_ENVIRONMENT,
            "python3 -m venv .venv",
            "Create a local virtual environment.",
        ),
        (
            "install-dependencies",
            SetupExperienceStep.DEPENDENCY_INSTALL,
            ".venv/bin/python -m pip install -e '.[dev]'",
            "Install local development dependencies when the maintainer chooses to do so.",
        ),
        (
            "prepare-environment",
            SetupExperienceStep.ENVIRONMENT_FILE,
            "cp .env.example .env",
            "Create a local environment file and keep it untracked.",
        ),
        (
            "try-demo",
            SetupExperienceStep.DEMO_MODE,
            "make try-demo",
            "Run the credential-free Demo Mode walkthrough.",
        ),
        (
            "local-database",
            SetupExperienceStep.LOCAL_DATABASE,
            "make first-run",
            "Prepare the safe local first-run flow.",
        ),
        (
            "start-app",
            SetupExperienceStep.LOCAL_APP_START,
            "make demo",
            "Start the local Demo Mode application.",
        ),
        (
            "product-dashboard",
            SetupExperienceStep.PRODUCT_DASHBOARD,
            "make product-dashboard-overview",
            "Review the local product dashboard guide.",
        ),
        (
            "quality",
            SetupExperienceStep.SAFETY_CHECKS,
            "make quality",
            "Run local quality and safety checks.",
        ),
        (
            "docs",
            SetupExperienceStep.DOCS_SITE,
            "make docs-site-check",
            "Check the local documentation site.",
        ),
        (
            "sandbox",
            SetupExperienceStep.SANDBOX_BOUNDARY,
            "make sandbox-check",
            "Review the separately gated Sandbox path.",
        ),
        (
            "pilot",
            SetupExperienceStep.PILOT_BOUNDARY,
            "make pilot-check",
            "Review the separately gated Pilot path.",
        ),
        (
            "hosted",
            SetupExperienceStep.HOSTED_BOUNDARY,
            "make hosted-deployment-check",
            "Review hosted planning without deployment.",
        ),
        (
            "doctor",
            SetupExperienceStep.TROUBLESHOOTING,
            "make doctor",
            "Print local setup diagnostics and next steps.",
        ),
    )
    return [
        SetupCommand(
            name=name,
            step=step,
            command=command,
            description=description,
            sequence=index,
        )
        for index, (name, step, command, description) in enumerate(rows, start=1)
    ]


def build_setup_mode_paths(settings: Settings) -> list[SetupModePath]:
    del settings
    return [
        SetupModePath(
            mode="Demo",
            description=(
                "Local, fixture-backed mode; no secrets, Procore credentials, cloud services, "
                "or external database required."
            ),
            first_command="make first-run",
            gated=False,
            requires_secrets=False,
        ),
        SetupModePath(
            mode="Sandbox",
            description=(
                "Separate manually gated path that may require private credentials; never "
                "entered by Demo Mode."
            ),
            first_command="make sandbox-check",
            gated=True,
            requires_secrets=True,
            local_only=False,
        ),
        SetupModePath(
            mode="Pilot",
            description="Separate private-review path; setup grants no pilot approval.",
            first_command="make pilot-check",
            gated=True,
            requires_secrets=True,
            local_only=False,
        ),
        SetupModePath(
            mode="Hosted",
            description="Separate deployment-planning path; local setup performs no deployment.",
            first_command="make hosted-deployment-check",
            gated=True,
            requires_secrets=True,
            local_only=False,
        ),
    ]


def build_setup_troubleshooting_items(settings: Settings) -> list[SetupTroubleshootingItem]:
    del settings
    rows = (
        (
            "missing_git",
            "git is missing",
            "Install git, then add its executable directory to PATH.",
            "git --version",
        ),
        (
            "missing_python",
            "python3 is missing",
            "Install a supported Python version, then add python3 to PATH.",
            "python3 --version",
        ),
        (
            "missing_pip",
            "pip is missing",
            "Use python3 -m pip so pip matches the selected interpreter.",
            "python3 -m pip --version",
        ),
        (
            "missing_make",
            "make is missing",
            "Install make, then add its executable directory to PATH.",
            "make --version",
        ),
        (
            "path",
            "a command is not found on PATH",
            "Confirm the tool location and update the local shell PATH without adding secrets.",
            None,
        ),
    )
    return [
        SetupTroubleshootingItem(
            code=code, symptom=symptom, guidance=guidance, check_command=command
        )
        for code, symptom, guidance, command in rows
    ]


def build_setup_command_map(settings: Settings) -> list[SetupCommandMapItem]:
    commands = build_setup_commands(settings)
    return [
        SetupCommandMapItem(
            step=item.step,
            purpose=item.description,
            command=item.command,
            mode=(
                "Demo"
                if item.step
                in {
                    SetupExperienceStep.DEMO_MODE,
                    SetupExperienceStep.LOCAL_DATABASE,
                    SetupExperienceStep.LOCAL_APP_START,
                    SetupExperienceStep.PRODUCT_DASHBOARD,
                }
                else "local"
            ),
            sequence=item.sequence,
        )
        for item in commands
    ] + [
        SetupCommandMapItem(
            step=SetupExperienceStep.SAFETY_CHECKS,
            purpose="Run the public safety audit.",
            command="make safety-check",
            mode="local",
        ),
        SetupCommandMapItem(
            step=SetupExperienceStep.SAFETY_CHECKS,
            purpose="Run the public usability audit.",
            command="make public-usability-audit",
            mode="local",
        ),
    ]


def _setting(settings: Settings, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _validate_policy(settings: Settings) -> None:
    required = (
        _setting(settings, "setup_experience_require_demo_safe_defaults", True),
        _setting(settings, "setup_experience_require_no_secrets", True),
        _setting(settings, "setup_experience_require_ignored_outputs", True),
        _setting(settings, "setup_experience_require_local_only", True),
    )
    allowed = (
        _setting(settings, "setup_experience_allow_real_identities", False),
        _setting(settings, "setup_experience_allow_real_domains", False),
        _setting(settings, "setup_experience_allow_real_urls", False),
        _setting(settings, "setup_experience_allow_report_contents", False),
        _setting(settings, "setup_experience_allow_private_paths", False),
    )
    if _setting(settings, "setup_experience_fail_closed", True) and (
        not all(required) or any(allowed)
    ):
        raise SetupExperienceBlockedError("Unsafe setup-experience policy blocked.")


def build_setup_experience_report(settings: Settings) -> SetupExperienceReport:
    if not _setting(settings, "setup_experience_enabled", True):
        raise SetupExperienceError("Setup experience disabled.")
    _validate_policy(settings)
    prerequisites = build_setup_prerequisites(settings)
    commands = build_setup_commands(settings)
    modes = build_setup_mode_paths(settings)
    troubleshooting = build_setup_troubleshooting_items(settings)
    command_map = build_setup_command_map(settings)
    required_files = (
        "README.md",
        "QUICKSTART.md",
        "Makefile",
        ".env.example",
        "docs/demo-product-walkthrough.md",
        "docs/product-dashboard.md",
        "docs/security-gap-closeout.md",
        "scripts/audit_public_safety.py",
        "scripts/audit_routes_read_only.py",
        "scripts/check_docs_site.py",
    )
    if Path("pyproject.toml").exists():
        required_files += ("pyproject.toml",)
    blockers = [
        f"Missing required local setup input: {path}."
        for path in required_files
        if not Path(path).is_file()
    ]
    makefile = Path("Makefile").read_text() if Path("Makefile").is_file() else ""
    required_targets = (
        "first-run",
        "try-demo",
        "quality",
        "safety-check",
        "public-usability-audit",
        "docs-site-check",
        "product-dashboard-overview",
        "security-gap-closeout",
    )
    blockers.extend(
        f"Missing required local Make target: {target}."
        for target in required_targets
        if f"{target}:" not in makefile
    )
    gitignore = Path(".gitignore").read_text() if Path(".gitignore").is_file() else ""
    if not all(pattern in gitignore for pattern in IGNORED_OUTPUTS):
        blockers.append("One or more generated setup output patterns are not ignored.")
    findings = [
        SetupExperienceFinding(code="missing_local_setup_control", message=item, severity="blocker")
        for item in blockers
    ]
    status = SetupExperienceStatus.BLOCKED if blockers else SetupExperienceStatus.READY
    decision = (
        SetupExperienceDecision.BLOCKED
        if blockers
        else SetupExperienceDecision.READY_FOR_MAINTAINER_REVIEW
    )
    report = SetupExperienceReport(
        status=status,
        decision=decision,
        prerequisites_total=len(prerequisites),
        commands_total=len(commands),
        mode_paths_total=len(modes),
        findings=findings[: int(_setting(settings, "setup_experience_max_findings", 300))],
        blockers=blockers,
        warnings=[
            (
                "Demo Mode requires no secrets, Procore credentials, cloud services, or "
                "external database."
            ),
            (
                "Sandbox, Pilot, and Hosted paths remain separate and gated. Local setup "
                "grants no production, pilot, or release approval."
            ),
        ],
        prerequisites=prerequisites,
        commands=commands,
        mode_paths=modes,
        troubleshooting_items=troubleshooting,
        command_map=command_map,
        recommended_next_steps=[
            "Run `make first-run`.",
            "Run `make try-demo`.",
            "Run `make quality` before maintainer review.",
        ],
    )
    validate_setup_experience_report_safe(report)
    return report


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)
    elif isinstance(value, str):
        yield value


def validate_setup_experience_report_safe(report: Any) -> None:
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else report
    if not isinstance(payload, str) and set(_walk_keys(payload)) & FORBIDDEN_KEYS:
        raise SetupExperienceBlockedError("Unsafe setup-experience content blocked.")
    strings = [payload] if isinstance(payload, str) else list(_walk_strings(payload))
    patterns = (
        URL_PATTERN,
        EMAIL_PATTERN,
        PHONE_PATTERN,
        DOMAIN_PATTERN,
        LONG_ID_PATTERN,
        PRIVATE_PATH_PATTERN,
        SECRET_PATTERN,
        PRIVATE_MATERIAL_PATTERN,
    )
    for value in strings:
        if any(pattern.search(value) for pattern in patterns):
            raise SetupExperienceBlockedError("Unsafe setup-experience content blocked.")
        if DEMO_SECRET_REQUIREMENT_PATTERN.search(value) and not NEGATION_PATTERN.search(value):
            raise SetupExperienceBlockedError("Demo Mode secret requirement blocked.")
        if MODE_BLUR_PATTERN.search(value) and not NEGATION_PATTERN.search(value):
            raise SetupExperienceBlockedError("Unsafe setup mode boundary blocked.")
        if UNSAFE_CLAIM_PATTERN.search(value) and not NEGATION_PATTERN.search(value):
            raise SetupExperienceBlockedError("Unsafe setup-experience claim blocked.")


def render_setup_experience_markdown(report: SetupExperienceReport) -> str:
    text = "\n".join(
        [
            "# Setup Experience Review",
            "",
            f"Status: `{report.status.value}`",
            f"Decision: `{report.decision.value}`",
            "",
            (
                "This review inspects local public-repository guidance only and performs no "
                "installation or live operation."
            ),
            "",
            *(f"- `{item.step.value}`: `{item.command}`" for item in report.commands),
            "",
            (
                "Demo Mode requires no secrets, Procore credentials, cloud services, or external "
                "database."
            ),
            (
                "Sandbox, Pilot, and Hosted paths remain separate and gated. No production, "
                "pilot, or release approval is implied."
            ),
            "",
        ]
    )
    validate_setup_experience_report_safe(text)
    return text


def render_first_run_checklist_markdown(report: SetupExperienceReport) -> str:
    text = "\n".join(
        [
            "# First-Run Checklist",
            "",
            "1. Run `make first-run` to check the local setup.",
            "2. Run `make try-demo` for credential-free Demo Mode.",
            "3. Run `make quality` before maintainer review.",
            "",
            *(
                f"- [ ] {item.name}: `{item.check_command}` — {item.guidance}"
                for item in report.prerequisites
            ),
            "",
            (
                "No deploy, release, package build, publish, or live service call is performed "
                "by this checklist."
            ),
            "",
        ]
    )
    validate_setup_experience_report_safe(text)
    return text


def render_local_installer_guide_markdown(report: SetupExperienceReport) -> str:
    text = "\n".join(
        [
            "# Local Installer Guide",
            "",
            (
                "These commands are maintainer-run local guidance; this service does not "
                "execute dependency installation."
            ),
            "",
            *(
                f"## {item.mode}\n\n{item.description}\n\nStart with: `{item.first_command}`"
                for item in report.mode_paths
            ),
            "",
            (
                "Demo Mode needs no secrets. Other modes remain separate and gated. No "
                "production, pilot, or release approval is implied."
            ),
            "",
        ]
    )
    validate_setup_experience_report_safe(text)
    return text


def render_setup_troubleshooting_guide_markdown(report: SetupExperienceReport) -> str:
    text = "\n".join(
        [
            "# Setup Troubleshooting Guide",
            "",
            *(
                f"## {item.symptom}\n\n{item.guidance}"
                + (f"\n\nCheck: `{item.check_command}`" if item.check_command else "")
                for item in report.troubleshooting_items
            ),
            "",
        ]
    )
    validate_setup_experience_report_safe(text)
    return text


def _csv_cell(value: Any) -> str:
    text = sanitize_setup_experience_value(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def render_setup_command_map_csv(report: SetupExperienceReport) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("sequence", "step", "mode", "purpose", "command"))
    for item in report.command_map:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    item.sequence or "",
                    item.step.value,
                    item.mode,
                    item.purpose,
                    item.command,
                )
            )
        )
    text = output.getvalue()
    validate_setup_experience_report_safe(text)
    return text


def _safe_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    temporary = (
        root.is_absolute()
        and root.name.startswith("procore-intake-bridge-setup-experience-")
        and (root.parent == Path("/tmp") or "pytest-" in root.as_posix())
    )
    if (
        ".." in root.parts
        or (root.is_absolute() and not temporary)
        or (not temporary and root.parts[:1] not in {(value,) for value in SAFE_ROOTS})
    ):
        raise SetupExperienceBlockedError("Unsafe output root.")
    return root


def write_setup_experience_artifacts(
    report: SetupExperienceReport, output_root: str | Path
) -> SetupExperienceArtifactResult:
    root = _safe_output_root(output_root)
    artifacts = {
        "setup-experience-report.json": report.model_dump_json(indent=2),
        "setup-experience-report.md": render_setup_experience_markdown(report),
        "first-run-checklist.md": render_first_run_checklist_markdown(report),
        "local-installer-guide.md": render_local_installer_guide_markdown(report),
        "setup-troubleshooting-guide.md": render_setup_troubleshooting_guide_markdown(report),
        "setup-command-map.csv": render_setup_command_map_csv(report),
    }
    artifacts["manifest.json"] = json.dumps(
        {
            "files": sorted(artifacts),
            "sanitized": True,
            "live_operations": False,
            "external_operations": False,
            "package_build_operations": False,
            "publish_operations": False,
            "release_operations": False,
            "deployment_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in artifacts.items():
        validate_setup_experience_report_safe(content)
        (root / filename).write_text(content)
    return SetupExperienceArtifactResult(
        status=report.status, output_directory=root.name, files=sorted(artifacts)
    )
