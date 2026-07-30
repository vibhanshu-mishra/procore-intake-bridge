from enum import StrEnum

from pydantic import BaseModel, Field


class ProductDashboardStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ProductDashboardCardStatus(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    DISABLED = "disabled"
    NEEDS_CONFIGURATION = "needs_configuration"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ProductDashboardFinding(BaseModel):
    code: str
    message: str
    severity: str = "info"


class ProductDashboardLink(BaseModel):
    label: str
    href: str | None = None
    command: str | None = None
    description: str


class ProductDashboardCard(BaseModel):
    group: str
    title: str
    status: ProductDashboardCardStatus
    count: int | None = Field(default=None, ge=0)
    metrics: dict[str, int] = Field(default_factory=dict)
    message: str
    links: list[ProductDashboardLink] = Field(default_factory=list)


class ProductDashboardGuidanceItem(BaseModel):
    mode: str
    title: str
    message: str
    command: str | None = None


class ProductDashboardOverview(BaseModel):
    status: ProductDashboardStatus
    cards: list[ProductDashboardCard]
    guidance: list[ProductDashboardGuidanceItem]
    findings: list[ProductDashboardFinding] = Field(default_factory=list)
    read_only: bool = True
    local_database_only: bool = True
    procore_calls_made: bool = False
    external_calls_made: bool = False
    database_writes_made: bool = False
    export_artifacts_generated: bool = False
    attachment_files_read: bool = False
    readiness_is_approval: bool = False
