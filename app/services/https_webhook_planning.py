import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.https_webhook_planning import (
    HttpsWebhookArtifactResult,
    HttpsWebhookPlanningFinding,
    HttpsWebhookPlanningProfile,
    HttpsWebhookPlanningReport,
    HttpsWebhookPlanningStatus,
)

SAFE_PLACEHOLDER = re.compile(r"^[A-Z0-9_-]*PLACEHOLDER[A-Z0-9_-]*$")
RAW_URL = re.compile(
    r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mariadb|mongodb)://\S+"
)
DOMAIN = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud)\b")
DNS_RECORD = re.compile(
    r"(?i)(?:\b(?:A|AAAA|CNAME|TXT|MX|CAA|NS)\s+[a-z0-9.-]+\s+\S+|"
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b)"
)
CERTIFICATE = re.compile(
    r"(?i)(?:-----BEGIN (?:RSA |EC |OPENSSH )?(?:CERTIFICATE|PRIVATE KEY)|"
    r"certificate_request|private_key\s*[:=])"
)
CSR = re.compile(r"(?i)(?:-----BEGIN CERTIFICATE REQUEST-----|\bcsr\s*[:=]\s*\S+)")
ACME = re.compile(
    r"(?i)(?:acme[-_ ]challenge\s*[:=]\s*\S+|_acme-challenge\.[a-z0-9.-]+)"
)
SECRET = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+|"
    r"(?:webhook[_ -]?secret|token|password|credential)\s*[:=]\s*\S+)"
)
SIGNED_URL = re.compile(r"(?i)https?://\S+[?&](?:signature|signed|token|expires)=")
CLOUD_CREDENTIAL = re.compile(
    r'(?i)"(?:private_key|private_key_id|client_email|client_x509_cert_url)"\s*:'
)
INFRA_ID = re.compile(
    r"(?i)\b(?:vpc|subnet|cluster|service|resource|ingress|load_balancer)"
    r"[-_:=/][a-z0-9-]{6,}\b"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:\\)")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\d{3}[-. ]\d{3}[-. ]\d{4}\b")
WEBHOOK_CONTENT = re.compile(
    r"(?i)(?:webhook[_ -]?report[_ -]?contents?|"
    r"(?:raw[_ -]?)?(?:payload|headers|response_body)\s*[:=])"
)
WEBHOOK_ID = re.compile(r"(?i)\b(?:procore[_ -]?)?webhook[_ -]?id\s*[:=]\s*\d{4,}")
APPROVAL_CLAIM = re.compile(
    r"(?i)\b(?:production[- ]ready|production setup (?:is )?complete|"
    r"webhook setup (?:is )?complete|approved for production|pilot approved)\b"
)
SAFE_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
SAFE_OUTPUT_ROOTS = {
    "https-webhook-output",
    "webhook-ingress-output",
    "tls-planning-output",
    "dns-planning-output",
}
ARTIFACT_FILES = [
    "https-webhook-report.json",
    "webhook-ingress-plan.md",
    "tls-plan.md",
    "dns-plan.md",
    "webhook-disable-plan.md",
    "webhook-rollback-plan.md",
    "webhook-evidence-ref.md",
    "manifest.json",
]


class HttpsWebhookPlanningError(RuntimeError):
    """HTTPS/webhook planning failed with private details suppressed."""


class HttpsWebhookPlanningBlockedError(HttpsWebhookPlanningError):
    pass


def sanitize_https_webhook_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_https_webhook_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_https_webhook_value(item) for item in value]
    if isinstance(value, Path):
        return "[masked-path]"
    if isinstance(value, str):
        if SAFE_PLACEHOLDER.fullmatch(value) or value == "/webhooks/procore":
            return value
        for pattern, replacement in (
            (SIGNED_URL, "[masked-url]"),
            (RAW_URL, "[masked-url]"),
            (DOMAIN, "[masked-domain]"),
            (DNS_RECORD, "[masked-dns-record]"),
            (CERTIFICATE, "[masked-certificate]"),
            (CSR, "[masked-certificate-request]"),
            (ACME, "[masked-acme-value]"),
            (SECRET, "[masked-secret]"),
            (CLOUD_CREDENTIAL, "[masked-cloud-credential]"),
            (INFRA_ID, "[masked-infrastructure-identifier]"),
            (ABSOLUTE_PATH, "[masked-path]"),
            (EMAIL, "[masked-contact]"),
            (PHONE, "[masked-contact]"),
            (WEBHOOK_CONTENT, "[masked-webhook-content]"),
            (WEBHOOK_ID, "[masked-webhook-identifier]"),
            (APPROVAL_CLAIM, "[masked-claim]"),
        ):
            if pattern.search(value):
                return replacement
    return value


def _strings(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _finding(code: str) -> HttpsWebhookPlanningFinding:
    return HttpsWebhookPlanningFinding(
        code=code,
        message=f"Unsafe {code.replace('_', ' ')} is blocked.",
    )


def validate_https_webhook_profile(
    profile: HttpsWebhookPlanningProfile, settings: Settings
) -> list[HttpsWebhookPlanningFinding]:
    findings: list[HttpsWebhookPlanningFinding] = []
    if not settings.https_webhook_planning_enabled:
        findings.append(_finding("planning_disabled"))
    if not settings.https_webhook_fail_closed:
        findings.append(_finding("fail_closed_disabled"))
    if not SAFE_PROFILE_NAME.fullmatch(profile.profile_name):
        findings.append(_finding("profile_name"))
    if profile.expected_webhook_path != settings.https_webhook_expected_path:
        findings.append(_finding("unexpected_webhook_path"))
    if profile.expected_webhook_path != "/webhooks/procore":
        findings.append(_finding("unsupported_webhook_path"))
    if any(
        (
            settings.https_webhook_allow_real_domains,
            settings.https_webhook_allow_real_urls,
            settings.https_webhook_allow_cert_contents,
            settings.https_webhook_allow_dns_records,
            settings.https_webhook_allow_absolute_paths,
        )
    ):
        findings.append(_finding("unsafe_policy"))
    checks = (
        ("signed_url", SIGNED_URL),
        ("raw_url", RAW_URL),
        ("real_domain", DOMAIN),
        ("dns_record", DNS_RECORD),
        ("certificate", CERTIFICATE),
        ("csr", CSR),
        ("acme_value", ACME),
        ("secret", SECRET),
        ("cloud_credential", CLOUD_CREDENTIAL),
        ("infrastructure_id", INFRA_ID),
        ("absolute_path", ABSOLUTE_PATH),
        ("email", EMAIL),
        ("phone", PHONE),
        ("webhook_report_contents", WEBHOOK_CONTENT),
        ("webhook_id", WEBHOOK_ID),
        ("approval_claim", APPROVAL_CLAIM),
    )
    for value in _strings(profile.model_dump(mode="json")):
        if SAFE_PLACEHOLDER.fullmatch(value) or value == "/webhooks/procore":
            continue
        for code, pattern in checks:
            if pattern.search(value):
                findings.append(_finding(code))
    required_refs = [
        profile.environment_label,
        profile.public_url_placeholder,
        profile.allowed_host_placeholder,
        profile.dns_plan_ref_placeholder,
        profile.tls_plan_ref_placeholder,
        profile.webhook_secret_ref_placeholder,
        profile.reverse_proxy_ref_placeholder,
        profile.ingress_platform_ref_placeholder,
        profile.event_queue_ref_placeholder,
        profile.replay_plan_ref_placeholder,
        profile.disable_plan_ref_placeholder,
        profile.rollback_plan_ref_placeholder,
        profile.monitoring_ref_placeholder,
        profile.evidence_ref_placeholder,
    ]
    if settings.https_webhook_require_placeholders and any(
        not SAFE_PLACEHOLDER.fullmatch(value) for value in required_refs
    ):
        findings.append(_finding("placeholders_required"))
    required_plans = (
        (
            "tls_plan_required",
            settings.https_webhook_require_tls_plan,
            profile.tls_plan_ref_placeholder,
        ),
        (
            "dns_plan_required",
            settings.https_webhook_require_dns_plan,
            profile.dns_plan_ref_placeholder,
        ),
        (
            "signature_secret_ref_required",
            settings.https_webhook_require_signature_secret_ref,
            profile.webhook_secret_ref_placeholder,
        ),
        (
            "event_queue_required",
            settings.https_webhook_require_event_queue,
            profile.event_queue_ref_placeholder,
        ),
        (
            "replay_plan_required",
            settings.https_webhook_require_replay_plan,
            profile.replay_plan_ref_placeholder,
        ),
        (
            "disable_plan_required",
            settings.https_webhook_require_disable_plan,
            profile.disable_plan_ref_placeholder,
        ),
        (
            "rollback_plan_required",
            settings.https_webhook_require_rollback_plan,
            profile.rollback_plan_ref_placeholder,
        ),
    )
    for code, required, value in required_plans:
        if required and not SAFE_PLACEHOLDER.fullmatch(value):
            findings.append(_finding(code))
    return findings


def build_https_webhook_report(
    profile: HttpsWebhookPlanningProfile, settings: Settings
) -> HttpsWebhookPlanningReport:
    findings = validate_https_webhook_profile(profile, settings)

    def present(value: str) -> bool:
        return bool(SAFE_PLACEHOLDER.fullmatch(value))

    return HttpsWebhookPlanningReport(
        profile_name=profile.profile_name,
        status=(
            HttpsWebhookPlanningStatus.BLOCKED
            if findings
            else HttpsWebhookPlanningStatus.NEEDS_CONFIGURATION
        ),
        https_required=settings.https_webhook_require_https,
        public_ingress_required=settings.https_webhook_require_public_ingress,
        endpoint_path_expected=settings.https_webhook_expected_path,
        tls_plan_present=present(profile.tls_plan_ref_placeholder),
        dns_plan_present=present(profile.dns_plan_ref_placeholder),
        signature_secret_ref_present=present(profile.webhook_secret_ref_placeholder),
        event_queue_present=present(profile.event_queue_ref_placeholder),
        replay_plan_present=present(profile.replay_plan_ref_placeholder),
        disable_plan_present=present(profile.disable_plan_ref_placeholder),
        rollback_plan_present=present(profile.rollback_plan_ref_placeholder),
        findings=findings,
        recommended_next_steps=[
            "Adapt DNS, TLS, reverse-proxy, and ingress plans privately.",
            "Configure the webhook signature secret reference outside Git.",
            "Review queue, replay, disable, rollback, monitoring, and evidence references.",
            "Obtain production review before separately managed webhook registration.",
        ],
    )


def build_default_https_webhook_profile(settings: Settings) -> HttpsWebhookPlanningProfile:
    return HttpsWebhookPlanningProfile(
        profile_name="example-https-webhook-planning",
        expected_webhook_path=settings.https_webhook_expected_path,
    )


def _header(title: str, profile: HttpsWebhookPlanningProfile) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Profile: `{profile.profile_name}`",
        f"Expected local receiver path: `{profile.expected_webhook_path}`",
        "",
        "Planning only: no DNS, TLS, ACME, URL, Procore, or registration call was made.",
        "",
    ]


def _render(title: str, profile: HttpsWebhookPlanningProfile, items: tuple[str, ...]) -> str:
    lines = _header(title, profile)
    lines.extend(f"- [ ] {item}" for item in items)
    return "\n".join(lines) + "\n"


def render_https_webhook_plan(profile, report) -> str:
    del report
    return _render(
        "Webhook ingress plan",
        profile,
        (
            "Review HTTPS and public ingress requirements privately.",
            "Preserve proxy forwarding and original-request header expectations.",
            "Route only the expected local receiver path.",
            "Review signature verification and isolated event queue readiness.",
        ),
    )


def render_tls_plan(profile, report) -> str:
    del report
    return _render(
        "TLS certificate plan",
        profile,
        (
            "Keep certificate and key contents outside Git.",
            "Review issuance, renewal, termination, and failure handling privately.",
        ),
    )


def render_dns_plan(profile, report) -> str:
    del report
    return _render(
        "DNS plan",
        profile,
        (
            "Keep domain and DNS record values outside Git.",
            "Review ownership, propagation, rollback, and evidence privately.",
        ),
    )


def render_webhook_disable_plan(profile, report) -> str:
    del report
    return _render(
        "Webhook disable plan",
        profile,
        (
            "Define how private ingress and receiver processing will be disabled.",
            "Pause queue processing and preserve sanitized incident evidence.",
            "Handle any remote registration change through a separately approved process.",
        ),
    )


def render_webhook_rollback_plan(profile, report) -> str:
    del report
    return _render(
        "Webhook rollback plan",
        profile,
        (
            "Define rollback triggers and responsible private review.",
            "Restore the previously reviewed ingress and receiver posture.",
            "Verify queue state without publishing payloads, identifiers, or logs.",
        ),
    )


def render_webhook_evidence_ref(profile, report) -> str:
    del report
    return _render(
        "Webhook evidence reference",
        profile,
        (
            f"Record only `{profile.evidence_ref_placeholder}` in the private workspace.",
            "Do not copy reports, URLs, records, certificates, payloads, or secrets.",
        ),
    )


def validate_https_webhook_report_safe(report: HttpsWebhookPlanningReport) -> None:
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True)
    for pattern in (
        RAW_URL,
        DOMAIN,
        DNS_RECORD,
        CERTIFICATE,
        CSR,
        ACME,
        SECRET,
        CLOUD_CREDENTIAL,
        INFRA_ID,
        ABSOLUTE_PATH,
        EMAIL,
        PHONE,
        WEBHOOK_CONTENT,
        WEBHOOK_ID,
        APPROVAL_CLAIM,
    ):
        if pattern.search(text):
            raise HttpsWebhookPlanningBlockedError(
                "HTTPS/webhook report failed safety validation."
            )
    if any(
        (
            report.webhook_registration_attempted,
            report.dns_check_attempted,
            report.tls_check_attempted,
            report.public_url_check_attempted,
            report.procore_call_attempted,
            report.cert_contents_exposed,
            report.private_key_exposed,
            report.real_urls_exposed,
            report.real_domains_exposed,
            report.dns_records_exposed,
            report.secrets_exposed,
            report.private_paths_exposed,
        )
    ):
        raise HttpsWebhookPlanningBlockedError(
            "HTTPS/webhook report contains unsafe operation flags."
        )


def write_https_webhook_artifacts(
    profile: HttpsWebhookPlanningProfile, output_root: Path
) -> HttpsWebhookArtifactResult:
    temporary_absolute = (
        output_root.is_absolute()
        and output_root.name.startswith("procore-intake-bridge-https-webhook-")
        and (
            output_root.parent == Path("/tmp")
            or "pytest-" in output_root.as_posix()
        )
    )
    if ".." in output_root.parts or (output_root.is_absolute() and not temporary_absolute):
        raise HttpsWebhookPlanningBlockedError("HTTPS/webhook output root is unsafe.")
    if not temporary_absolute and output_root.parts[:1] not in {
        (name,) for name in SAFE_OUTPUT_ROOTS
    }:
        raise HttpsWebhookPlanningBlockedError(
            "HTTPS/webhook output root is not approved."
        )
    report = build_https_webhook_report(profile, Settings(_env_file=None))
    if report.status == HttpsWebhookPlanningStatus.BLOCKED:
        raise HttpsWebhookPlanningBlockedError(
            "HTTPS/webhook profile failed safety validation."
        )
    validate_https_webhook_report_safe(report)
    destination = output_root / profile.profile_name
    destination.mkdir(parents=True, exist_ok=True)
    rendered = {
        "https-webhook-report.json": (
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        ),
        "webhook-ingress-plan.md": render_https_webhook_plan(profile, report),
        "tls-plan.md": render_tls_plan(profile, report),
        "dns-plan.md": render_dns_plan(profile, report),
        "webhook-disable-plan.md": render_webhook_disable_plan(profile, report),
        "webhook-rollback-plan.md": render_webhook_rollback_plan(profile, report),
        "webhook-evidence-ref.md": render_webhook_evidence_ref(profile, report),
        "manifest.json": json.dumps(
            {
                "files": ARTIFACT_FILES,
                "external_calls": False,
                "webhook_registration_attempted": False,
                "certificate_generated": False,
                "placeholder_only": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    }
    for name, content in rendered.items():
        (destination / name).write_text(content, encoding="utf-8")
    return HttpsWebhookArtifactResult(
        profile_name=profile.profile_name,
        output_directory=profile.profile_name,
        files=ARTIFACT_FILES,
    )
