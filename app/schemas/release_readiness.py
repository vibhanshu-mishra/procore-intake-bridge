from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class StrictReleaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReleaseReadinessStatus(StrEnum):
    READY_FOR_MAINTAINER_REVIEW = "ready_for_maintainer_review"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ReleaseReadinessFinding(StrictReleaseModel):
    code: str
    status: ReleaseReadinessStatus
    message: str


class ReleaseReadinessRequirement(StrictReleaseModel):
    category: str
    status: ReleaseReadinessStatus
    summary: str
    blocking: bool = False


class ReleaseReadinessChecklist(StrictReleaseModel):
    requirements: tuple[ReleaseReadinessRequirement, ...]
    findings: tuple[ReleaseReadinessFinding, ...]


class ReleaseReadinessReport(StrictReleaseModel):
    status: ReleaseReadinessStatus
    version: str
    checklist: ReleaseReadinessChecklist
    known_limitations: tuple[str, ...]
    manual_maintainer_approval_required: bool = True
    release_approved: bool = False
    release_created: bool = False
    tag_created: bool = False
    package_created: bool = False
    deployment_executed: bool = False
    external_calls: bool = False
    procore_calls: bool = False
    private_values_included: bool = False
    local_paths_included: bool = False


class ReleaseReadinessArtifactResult(StrictReleaseModel):
    output_directory: str
    files: tuple[str, ...]
    release_created: bool = False
    tag_created: bool = False
    package_created: bool = False
    deployment_executed: bool = False
    external_calls: bool = False
    private_values_included: bool = False
