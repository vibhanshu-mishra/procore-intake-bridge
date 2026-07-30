from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictHttpsWebhookModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HttpsWebhookPlanningStatus(StrEnum):
    READY = "ready"
    NEEDS_CONFIGURATION = "needs_configuration"
    BLOCKED = "blocked"


class HttpsWebhookPlanningFinding(StrictHttpsWebhookModel):
    code: str
    severity: str = "blocking"
    message: str


class HttpsWebhookPlanningRequirement(StrictHttpsWebhookModel):
    name: str
    required: bool
    present: bool
    status: HttpsWebhookPlanningStatus
    message: str


class HttpsWebhookPlanningProfile(StrictHttpsWebhookModel):
    profile_name: str
    environment_label: str = "ENVIRONMENT_LABEL_PLACEHOLDER"
    expected_webhook_path: str = "/webhooks/procore"
    public_url_placeholder: str = "PUBLIC_URL_PLACEHOLDER"
    allowed_host_placeholder: str = "ALLOWED_HOST_PLACEHOLDER"
    dns_plan_ref_placeholder: str = "DNS_PLAN_REF_PLACEHOLDER"
    tls_plan_ref_placeholder: str = "TLS_PLAN_REF_PLACEHOLDER"
    webhook_secret_ref_placeholder: str = "WEBHOOK_SECRET_REF_PLACEHOLDER"
    reverse_proxy_ref_placeholder: str = "REVERSE_PROXY_REF_PLACEHOLDER"
    ingress_platform_ref_placeholder: str = "INGRESS_PLATFORM_REF_PLACEHOLDER"
    event_queue_ref_placeholder: str = "EVENT_QUEUE_REF_PLACEHOLDER"
    replay_plan_ref_placeholder: str = "REPLAY_PLAN_REF_PLACEHOLDER"
    disable_plan_ref_placeholder: str = "WEBHOOK_DISABLE_PLAN_REF_PLACEHOLDER"
    rollback_plan_ref_placeholder: str = "WEBHOOK_ROLLBACK_PLAN_REF_PLACEHOLDER"
    monitoring_ref_placeholder: str = "MONITORING_REF_PLACEHOLDER"
    evidence_ref_placeholder: str = "WEBHOOK_EVIDENCE_REF_PLACEHOLDER"
    known_limitations: list[str] = Field(
        default_factory=lambda: ["KNOWN_LIMITATION_PLACEHOLDER"]
    )
    notes: list[str] = Field(
        default_factory=lambda: ["PLANNING_ONLY_PLACEHOLDER"]
    )


class HttpsWebhookIngressPlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    expected_path: str
    reverse_proxy_ref_placeholder: str
    ingress_platform_ref_placeholder: str
    external_check_attempted: bool = False


class TlsCertificatePlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    tls_plan_ref_placeholder: str
    certificate_generated: bool = False
    certificate_contents_included: bool = False


class DnsPlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    dns_plan_ref_placeholder: str
    dns_records_included: bool = False
    dns_check_attempted: bool = False


class WebhookSignaturePlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    webhook_secret_ref_placeholder: str
    secret_value_included: bool = False


class WebhookReplayPlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    replay_plan_ref_placeholder: str
    replay_attempted: bool = False


class WebhookDisablePlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    disable_plan_ref_placeholder: str
    webhook_changed: bool = False


class WebhookRollbackPlan(StrictHttpsWebhookModel):
    status: HttpsWebhookPlanningStatus
    rollback_plan_ref_placeholder: str
    rollback_executed: bool = False


class HttpsWebhookPlanningReport(StrictHttpsWebhookModel):
    profile_name: str
    status: HttpsWebhookPlanningStatus
    https_required: bool
    public_ingress_required: bool
    endpoint_path_expected: str
    tls_plan_present: bool
    dns_plan_present: bool
    signature_secret_ref_present: bool
    event_queue_present: bool
    replay_plan_present: bool
    disable_plan_present: bool
    rollback_plan_present: bool
    webhook_registration_attempted: bool = False
    dns_check_attempted: bool = False
    tls_check_attempted: bool = False
    public_url_check_attempted: bool = False
    procore_call_attempted: bool = False
    cert_contents_exposed: bool = False
    private_key_exposed: bool = False
    real_urls_exposed: bool = False
    real_domains_exposed: bool = False
    dns_records_exposed: bool = False
    secrets_exposed: bool = False
    private_paths_exposed: bool = False
    findings: list[HttpsWebhookPlanningFinding] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class HttpsWebhookArtifactResult(StrictHttpsWebhookModel):
    profile_name: str
    output_directory: str
    files: list[str]
    external_calls: bool = False
    webhook_registration_attempted: bool = False
    certificate_generated: bool = False
    private_values_exposed: bool = False
