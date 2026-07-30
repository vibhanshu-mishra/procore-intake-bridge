from collections import defaultdict

from app.schemas.command_ux import (
    CommandDifficulty,
    CommandMode,
    PublicCommand,
)

PRIMARY_COMMANDS = (
    PublicCommand(
        command="make start",
        group="Start here",
        mode=CommandMode.DEMO,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Show the three paths, run the local doctor, and recommend a next step.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="make try-demo",
        notes=("Safe by default.",),
    ),
    PublicCommand(
        command="make doctor",
        group="Start here",
        mode=CommandMode.DEMO,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Summarize local readiness without resolving private values.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="make try-demo",
    ),
    PublicCommand(
        command="make commands",
        group="Start here",
        mode=CommandMode.DEMO,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Print the concise public command guide.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="make start",
    ),
    PublicCommand(
        command="make next",
        group="Start here",
        mode=CommandMode.DEMO,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Print the best next command; defaults to Demo Mode.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="make try-demo",
    ),
    PublicCommand(
        command="make try-demo",
        group="Demo Mode",
        mode=CommandMode.DEMO,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Set up and run the synthetic fixture demo.",
        safe_for_first_run=True,
        writes_files=True,
        recommended_next_command="make doctor",
        notes=("Uses local SQLite only.", "Requires no Procore credentials."),
    ),
    PublicCommand(
        command="make prepare-sandbox",
        group="Sandbox Mode",
        mode=CommandMode.SANDBOX,
        difficulty=CommandDifficulty.INTERMEDIATE,
        purpose="Run offline sandbox planning and onboarding checks.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make init-private-workspace",
        notes=("Never runs the manually gated live smoke check.",),
    ),
    PublicCommand(
        command="make prepare-pilot",
        group="Pilot Mode",
        mode=CommandMode.PILOT,
        difficulty=CommandDifficulty.INTERMEDIATE,
        purpose="Run placeholder-only pilot planning and preflight checks.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make init-private-workspace",
        notes=("Never approves or deploys a pilot.", "Never reads private evidence contents."),
    ),
    PublicCommand(
        command="make init-private-workspace",
        group="Private workspace",
        mode=CommandMode.PILOT,
        difficulty=CommandDifficulty.INTERMEDIATE,
        purpose="Create ignored placeholder scaffolds for authorized private preparation.",
        safe_for_first_run=False,
        writes_files=True,
        requires_private_config=True,
        recommended_next_command="make private-workspace-check",
    ),
    PublicCommand(
        command="make safety-check",
        group="Safety audits",
        mode=CommandMode.SAFETY,
        difficulty=CommandDifficulty.BEGINNER,
        purpose="Run public content, usability, and read-only route audits.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="make quality",
    ),
    PublicCommand(
        command="make quality",
        group="Developer checks",
        mode=CommandMode.DEVELOPER,
        difficulty=CommandDifficulty.INTERMEDIATE,
        purpose="Run the complete offline lint, test, and safety suite.",
        safe_for_first_run=True,
        writes_files=False,
        recommended_next_command="git status --short",
    ),
)

ADVANCED_COMMANDS = (
    PublicCommand(
        command="make secret-provider-check",
        group="Provider checks",
        mode=CommandMode.ADVANCED,
        difficulty=CommandDifficulty.ADVANCED,
        purpose="Inspect secret-provider posture without printing values.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make secret-refs-check",
    ),
    PublicCommand(
        command="make storage-provider-check",
        group="Provider checks",
        mode=CommandMode.ADVANCED,
        difficulty=CommandDifficulty.ADVANCED,
        purpose="Inspect storage-provider posture without external calls.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make database-check",
    ),
    PublicCommand(
        command="make database-check",
        group="Provider checks",
        mode=CommandMode.ADVANCED,
        difficulty=CommandDifficulty.ADVANCED,
        purpose="Inspect database readiness without connecting.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make deployment-check",
    ),
    PublicCommand(
        command="make deployment-check",
        group="Deployment planning",
        mode=CommandMode.ADVANCED,
        difficulty=CommandDifficulty.ADVANCED,
        purpose="Validate fake deployment recipes without deploying.",
        safe_for_first_run=False,
        writes_files=False,
        requires_private_config=True,
        recommended_next_command="make deployment-safety-check",
    ),
    PublicCommand(
        command="python scripts/run_sandbox_dmsa_smoke.py",
        group="Advanced scripts",
        mode=CommandMode.ADVANCED,
        difficulty=CommandDifficulty.ADVANCED,
        purpose="Separately gated manual read-only sandbox probe.",
        safe_for_first_run=False,
        writes_files=False,
        external_calls=True,
        procore_calls=True,
        requires_private_config=True,
        recommended_next_command="Review the private operator runbook.",
        notes=("Not run by any friendly Make target.", "Never a default onboarding step."),
    ),
)


def get_command_catalog() -> tuple[PublicCommand, ...]:
    return PRIMARY_COMMANDS + ADVANCED_COMMANDS


def group_commands(
    commands: tuple[PublicCommand, ...] | None = None,
) -> dict[str, list[PublicCommand]]:
    grouped: dict[str, list[PublicCommand]] = defaultdict(list)
    for command in commands or get_command_catalog():
        grouped[command.group].append(command)
    return dict(grouped)


def next_steps_for_mode(mode: CommandMode | None = None) -> tuple[str, ...]:
    selected = mode or CommandMode.DEMO
    if selected == CommandMode.DEMO:
        return (
            "Start with Demo Mode. It is safe by default and needs no Procore credentials.",
            "Best next command: make try-demo",
            "Then run: make doctor",
        )
    if selected == CommandMode.SANDBOX:
        return (
            "Use Sandbox Mode when private Procore sandbox/DMSA credentials are available.",
            "Best next command: make prepare-sandbox",
            "Live smoke remains a separate manual operator action.",
        )
    if selected == CommandMode.PILOT:
        return (
            "Use Pilot Mode only for controlled private pilot preparation.",
            "Best next command: make prepare-pilot",
            "Keep evidence, approvals, and launch decisions private and on hold.",
        )
    raise ValueError("Next-step guidance is available for demo, sandbox, or pilot.")


def render_command_guide() -> str:
    lines = [
        "Procore Intake Bridge command guide",
        "=================================",
        "Friendly commands are local-only and make no Procore or external calls.",
        "",
    ]
    for group, commands in group_commands(PRIMARY_COMMANDS).items():
        lines.append(group)
        for item in commands:
            private = " — private configuration required" if item.requires_private_config else ""
            lines.append(f"  {item.command:<29} {item.purpose}{private}")
        lines.append("")
    lines.extend(
        (
            "Advanced commands",
            "  Existing deep targets and scripts remain available.",
            "  See docs/command-reference.md before using a manually gated command.",
        )
    )
    return "\n".join(lines) + "\n"


def render_onboarding_summary() -> str:
    return "\n".join(
        (
            "Onboarding summary",
            "==================",
            "1. Try Demo — make try-demo",
            "   Safe by default; fixtures only; no Procore credentials.",
            "2. Prepare Sandbox — make prepare-sandbox",
            "   Private credentials and allowed scope; offline checks only.",
            "3. Prepare Pilot — make prepare-pilot",
            "   Private workspace and evidence refs; no approval or deployment.",
            "",
            "Best next command: make try-demo",
        )
    ) + "\n"
