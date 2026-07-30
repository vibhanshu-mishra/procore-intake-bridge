from enum import StrEnum

from pydantic import BaseModel, Field


class SecurityThreatModelStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class SecurityThreatModelDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "threat_model_ready_for_security_review"
    NEEDS_REVIEW = "threat_model_needs_review"
    BLOCKED = "threat_model_blocked"
    NOT_RUN = "threat_model_not_run"


class SecurityThreatCategory(StrEnum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    SUPPLY_CHAIN = "supply_chain"
    MISCONFIGURATION = "misconfiguration"
    DATA_RETENTION = "data_retention"
    PUBLIC_PRIVATE_BOUNDARY = "public_private_boundary"
    LIVE_OPERATION_BOUNDARY = "live_operation_boundary"


class SecurityThreatBoundary(BaseModel):
    name: str
    description: str
    private_review_required: bool = False


class SecurityThreatFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class SecurityThreatRequirement(BaseModel):
    name: str
    path: str
    present: bool


class SecurityThreatScenario(BaseModel):
    category: SecurityThreatCategory
    boundary: str
    threat: str
    consequence: str


class SecurityThreatControl(BaseModel):
    name: str
    boundary: str
    description: str
    evidence_path: str
    implemented_publicly: bool = True


class SecurityThreatModelReport(BaseModel):
    status: SecurityThreatModelStatus
    decision: SecurityThreatModelDecision
    boundaries: list[SecurityThreatBoundary]
    scenarios: list[SecurityThreatScenario]
    controls: list[SecurityThreatControl]
    requirements: list[SecurityThreatRequirement]
    boundaries_total: int
    scenarios_total: int
    controls_total: int
    findings: list[SecurityThreatFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    live_operation_attempted: bool = False
    external_call_attempted: bool = False
    procore_call_attempted: bool = False
    cloud_call_attempted: bool = False
    db_connection_attempted: bool = False
    deployment_attempted: bool = False
    scanner_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    ids_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class SecurityThreatModelArtifactResult(BaseModel):
    status: SecurityThreatModelStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
