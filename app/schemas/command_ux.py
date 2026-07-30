from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CommandMode(StrEnum):
    DEMO = "demo"
    SANDBOX = "sandbox"
    PILOT = "pilot"
    SAFETY = "safety"
    DEVELOPER = "developer"
    ADVANCED = "advanced"


class CommandDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PublicCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str
    group: str
    mode: CommandMode
    difficulty: CommandDifficulty
    purpose: str
    safe_for_first_run: bool
    writes_files: bool
    external_calls: bool = False
    procore_calls: bool = False
    requires_private_config: bool = False
    recommended_next_command: str
    notes: tuple[str, ...] = ()
