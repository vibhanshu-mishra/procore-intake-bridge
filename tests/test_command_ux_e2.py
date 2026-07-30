import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.schemas.command_ux import CommandMode
from app.services.command_ux import (
    ADVANCED_COMMANDS,
    PRIMARY_COMMANDS,
    get_command_catalog,
    next_steps_for_mode,
)

ROOT = Path(__file__).resolve().parents[1]
FRIENDLY = {
    "make start",
    "make doctor",
    "make commands",
    "make next",
    "make try-demo",
    "make prepare-sandbox",
    "make prepare-pilot",
    "make init-private-workspace",
    "make safety-check",
    "make quality",
}


def test_catalog_includes_friendly_and_advanced_commands() -> None:
    catalog = get_command_catalog()
    assert FRIENDLY <= {item.command for item in catalog}
    assert PRIMARY_COMMANDS
    assert ADVANCED_COMMANDS
    assert any(item.procore_calls for item in ADVANCED_COMMANDS)


def test_friendly_commands_never_call_procore_or_external_services() -> None:
    assert all(not item.procore_calls for item in PRIMARY_COMMANDS)
    assert all(not item.external_calls for item in PRIMARY_COMMANDS)
    demo = [item for item in PRIMARY_COMMANDS if item.mode == CommandMode.DEMO]
    assert demo and all(not item.requires_private_config for item in demo)


def test_sandbox_and_pilot_preparation_boundaries_are_explicit() -> None:
    by_name = {item.command: item for item in PRIMARY_COMMANDS}
    sandbox = by_name["make prepare-sandbox"]
    pilot = by_name["make prepare-pilot"]
    assert sandbox.requires_private_config
    assert "never runs" in " ".join(sandbox.notes).casefold()
    assert pilot.requires_private_config
    assert "never approves" in " ".join(pilot.notes).casefold()
    assert sandbox.procore_calls is pilot.procore_calls is False
    assert sandbox.external_calls is pilot.external_calls is False


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ([], "make try-demo"),
        (["--mode", "demo"], "make try-demo"),
        (["--mode", "sandbox"], "make prepare-sandbox"),
        (["--mode", "pilot"], "make prepare-pilot"),
    ],
)
def test_next_steps_cli_is_safe(arguments: list[str], expected: str) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/print_next_steps.py", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    assert str(ROOT) not in result.stdout
    assert "must-not-appear" not in result.stdout
    assert "pilot is approved" not in result.stdout.casefold()
    assert "production-ready" not in result.stdout.casefold()


@pytest.mark.parametrize(
    "script",
    ("print_command_guide.py", "onboarding_summary.py"),
)
def test_command_guide_clis_are_safe(script: str) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "make try-demo" in result.stdout
    assert str(ROOT) not in result.stdout
    assert "must-not-appear" not in result.stdout


@pytest.mark.parametrize("mode", (CommandMode.DEMO, CommandMode.SANDBOX, CommandMode.PILOT))
def test_next_step_service_covers_each_public_mode(mode: CommandMode) -> None:
    guidance = next_steps_for_mode(mode)
    assert guidance
    assert any("Best next command" in item for item in guidance)


def test_makefile_friendly_recipes_exclude_risky_actions() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in (
        "help",
        "start",
        "commands",
        "next",
        "try-demo",
        "prepare-sandbox",
        "prepare-pilot",
        "safety-check",
    ):
        assert f"{target}:" in makefile
    friendly_region = makefile.split(".PHONY: database-template", 1)[0].casefold()
    for forbidden in (
        "run_sandbox_dmsa_smoke.py",
        "check_database_connectivity.py",
        "register_webhook",
        "deploy ",
    ):
        assert forbidden not in friendly_region


def test_make_help_commands_next_and_start_run_locally() -> None:
    for target in ("help", "commands", "next", "start"):
        result = subprocess.run(
            ["make", target],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PROCORE_INTAKE_USAGE_MODE": "demo"},
        )
        assert result.returncode == 0, result.stderr
        assert str(ROOT) not in result.stdout


def test_docs_prioritize_friendly_commands_and_private_boundaries() -> None:
    readme = (ROOT / "README.md").read_text().casefold()
    quickstart = (ROOT / "QUICKSTART.md").read_text().casefold()
    command_reference = (ROOT / "docs/command-reference.md").read_text().casefold()
    for command in ("make start", "make try-demo", "make prepare-sandbox", "make prepare-pilot"):
        assert command in readme
        assert command in quickstart
    assert "no procore credentials" in quickstart
    assert "private dmsa" in readme
    assert "private workspace" in quickstart
    assert "must not be committed" in quickstart
    assert command_reference.index("## friendly commands") < command_reference.index(
        "## advanced"
    )
    assert "beginner" in command_reference
    assert "manual gated live check" in command_reference
