# ruff: noqa: E501
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.schemas.incident_response_review import (
    AuditLogBoundary,
    ForensicsEvidenceType,
    IncidentCategory,
    IncidentResponseArtifactResult,
    IncidentResponseControl,
    IncidentResponseDecision,
    IncidentResponseFinding,
    IncidentResponseReviewReport,
    IncidentResponseReviewStatus,
    IncidentResponseScenario,
    IncidentRunbookItem,
    IncidentScenarioMatrixItem,
    IncidentSeverity,
)


class IncidentResponseReviewError(ValueError):
    pass


class IncidentResponseReviewBlockedError(IncidentResponseReviewError):
    pass


IGNORED_OUTPUTS = (
    "incident-response-review-output/",
    "incident-review-output/",
    "forensics-review-output/",
    "audit-log-review-output/",
    "security-incident-output/",
    "*.incident-response-review-report.json",
    "*.incident-response-review-report.md",
    "*.incident-runbook.md",
    "*.audit-log-boundary-map.md",
    "*.forensics-evidence-checklist.md",
    "*.incident-scenario-matrix.csv",
)
SAFE_ROOTS = {x.rstrip("/") for x in IGNORED_OUTPUTS[:5]}
ARTIFACT_FILES = (
    "incident-response-review-report.json",
    "incident-response-review-report.md",
    "incident-runbook.md",
    "audit-log-boundary-map.md",
    "forensics-evidence-checklist.md",
    "incident-scenario-matrix.csv",
    "manifest.json",
)
URL = re.compile(r"(?i)\b(?:https?|s3|gs)://\S+")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PATH = re.compile(r"(?i)(?:/Users/|/home/|/private/|[A-Z]:\\)")
PRIVATE = re.compile(
    r"(?i)(?:authorization|bearer|raw_log|raw_payload|live_headers?|live_payloads?|webhook_secret|signature|admin_token|database_url|signed_url|presigned_url|storage_key|object_key|packet_capture|memory_dump|core_dump|forensic_image|legal_notice|regulator_notice|law_enforcement_report|breach_notification_content|db_dump_content|backup_archive_content|migration_log)\s*[:=]\s*(?!false|none|placeholder)\S+"
)
CLAIM = re.compile(
    r"(?i)\b(?:gdpr|ccpa|hipaa) compliant\b|\b(?:soc ?2|iso ?27001|security|compliance|breach readiness) certified\b|\bproduction[- ]ready\b|\b(?:launch|pilot) approved\b|\bbreach notification completed\b|\bprocore (?:endorsed|partner|certified)\b"
)
KEYS = {
    "raw_log",
    "raw_payload",
    "authorization",
    "webhook_secret",
    "admin_token",
    "database_url",
    "signed_url",
    "storage_key",
    "object_key",
    "packet_capture",
    "memory_dump",
    "core_dump",
    "forensic_image",
    "legal_notice",
    "breach_notification_content",
    "report_contents",
    "private_path",
}


def sanitize_incident_response_value(v: Any) -> str:
    t = str(v).replace("\n", " ").replace("\r", " ").strip()
    return "[redacted]" if any(p.search(t) for p in (URL, EMAIL, PATH, PRIVATE)) else t[:400]


def build_incident_categories(s):
    return list(IncidentCategory)


def build_incident_severity_model(s):
    return list(IncidentSeverity)


def build_audit_log_boundaries(s):
    return list(AuditLogBoundary)


def build_forensics_evidence_types(s):
    return list(ForensicsEvidenceType)


def build_incident_response_controls(s):
    items = (
        ("threat model", "docs/security-threat-model.md"),
        ("auth boundary", "docs/auth-permission-boundary-audit.md"),
        ("webhook review", "docs/webhook-replay-signature-hardening.md"),
        ("data policy", "docs/data-retention-redaction-policy.md"),
        ("infra review", "docs/secrets-storage-db-security-review.md"),
        ("supply chain", "docs/dependency-supply-chain-security.md"),
        ("diagnostics", "docs/operator-diagnostics.md"),
        ("rollback", "docs/deployment-backup-rollback.md"),
        ("public safety", "scripts/audit_public_safety.py"),
    )
    return [
        IncidentResponseControl(
            name=n,
            evidence_path=p,
            description="Offline public-safe review evidence.",
            implemented=Path(p).is_file(),
        )
        for n, p in items
    ]


def build_incident_response_scenarios(s):
    sev = list(IncidentSeverity)
    return [
        IncidentResponseScenario(
            category=c,
            severity=sev[i % len(sev)],
            expectation="Escalate to authorized private assessment using references only.",
        )
        for i, c in enumerate(IncidentCategory)
    ]


def build_incident_scenario_matrix(s):
    sev = list(IncidentSeverity)
    ev = list(ForensicsEvidenceType)
    return [
        IncidentScenarioMatrixItem(
            category=c, severity=sev[i % len(sev)], evidence_type=ev[i % len(ev)]
        )
        for i, c in enumerate(IncidentCategory)
    ]


def build_incident_response_review_report(s: Settings):
    if not s.incident_response_review_enabled:
        raise IncidentResponseReviewError("Incident response review disabled.")
    req = (
        s.incident_response_review_require_placeholders,
        s.incident_response_review_require_private_evidence_references,
        s.incident_response_review_require_no_raw_logs,
        s.incident_response_review_require_no_secret_values,
        s.incident_response_review_require_no_payload_dumps,
        s.incident_response_review_require_audit_log_boundary_map,
        s.incident_response_review_require_chain_of_custody_placeholders,
        s.incident_response_review_require_runbooks,
        s.incident_response_review_require_generated_output_ignores,
    )
    allow = (
        s.incident_response_review_allow_real_identities,
        s.incident_response_review_allow_real_domains,
        s.incident_response_review_allow_real_urls,
        s.incident_response_review_allow_report_contents,
        s.incident_response_review_allow_private_paths,
    )
    if s.incident_response_review_fail_closed and (not all(req) or any(allow)):
        raise IncidentResponseReviewBlockedError("Unsafe incident review policy blocked.")
    gi = Path(".gitignore").read_text()
    f = [
        IncidentResponseFinding(
            code="missing_ignore_rule",
            message=f"Missing generated-output ignore rule: {x}.",
            severity="blocker",
        )
        for x in IGNORED_OUTPUTS
        if x not in gi
    ]
    f += [
        IncidentResponseFinding(
            code="private_incident_plan_needs_review",
            message="Contacts, authority, evidence custody, notification decisions, and recovery objectives require private review.",
        ),
        IncidentResponseFinding(
            code="live_response_out_of_scope",
            message="Monitoring, collection, forensics, notifications, deletion, and live response remain outside I7.",
        ),
    ]
    b = [x.message for x in f if x.severity == "blocker"]
    st = IncidentResponseReviewStatus.BLOCKED if b else IncidentResponseReviewStatus.NEEDS_REVIEW
    cats = build_incident_categories(s)
    sevs = build_incident_severity_model(s)
    logs = build_audit_log_boundaries(s)
    ev = build_forensics_evidence_types(s)
    scenarios = build_incident_response_scenarios(s)
    matrix = build_incident_scenario_matrix(s)
    runbook = [
        IncidentRunbookItem(
            category=x, action="Preserve private references and escalate to authorized responders."
        )
        for x in cats
    ]
    r = IncidentResponseReviewReport(
        status=st,
        decision=IncidentResponseDecision.BLOCKED if b else IncidentResponseDecision.NEEDS_REVIEW,
        categories=cats,
        severities=sevs,
        audit_log_boundaries=logs,
        forensics_evidence_types=ev,
        controls=build_incident_response_controls(s),
        scenarios=scenarios,
        runbook=runbook,
        scenario_matrix=matrix,
        categories_total=len(cats),
        severities_total=len(sevs),
        audit_log_boundaries_total=len(logs),
        forensics_evidence_types_total=len(ev),
        scenario_matrix_items_total=len(matrix),
        findings=f,
        blockers=b,
        warnings=[x.message for x in f if x.severity != "blocker"],
        recommended_next_steps=[
            "Complete authorized private incident roles, contacts, custody, and notification decisions.",
            "Keep real evidence and response operations outside the public repository.",
            "Treat I7 as planning input, not certification, legal advice, or approval.",
        ],
    )
    validate_incident_response_review_report_safe(r)
    return r


def _keys(v):
    if isinstance(v, dict):
        for k, c in v.items():
            yield str(k).casefold()
            yield from _keys(c)
    elif isinstance(v, list):
        for c in v:
            yield from _keys(c)


def validate_incident_response_review_report_safe(r):
    p = r.model_dump(mode="json") if isinstance(r, BaseModel) else r
    t = json.dumps(p, default=str) if not isinstance(p, str) else p
    if (set(_keys(p)) if not isinstance(p, str) else set()) & KEYS or any(
        x.search(t) for x in (URL, EMAIL, PATH, PRIVATE)
    ):
        raise IncidentResponseReviewBlockedError("Unsafe incident review content blocked.")
    for line in t.splitlines():
        if CLAIM.search(line) and not re.search(r"(?i)\b(?:no|not|never|does not|is not)\b", line):
            raise IncidentResponseReviewBlockedError("Unsafe incident claim blocked.")


def _map(title, items):
    t = "\n".join(
        [
            f"# {title}",
            "",
            "Offline placeholders and private references only; no collection or response action.",
            "",
            *(f"- `{x.value}`" for x in items),
            "",
        ]
    )
    validate_incident_response_review_report_safe(t)
    return t


def render_incident_response_review_markdown(r):
    t = "\n".join(
        [
            "# Incident Response / Audit Log / Forensics Review",
            "",
            f"Status: `{r.status.value}`",
            f"Decision: `{r.decision.value}`",
            "",
            "Offline only. No live response, alerting, notification, SIEM, log collection, evidence collection, packet capture, forensics tool, deletion, purge, external call, Procore call, cloud call, or database call was attempted.",
            "",
            *(f"- `{x.code}` — {x.message}" for x in r.findings),
            "",
            "This is not legal compliance, breach readiness certification, security certification, production approval, or a breach-notification decision.",
            "",
        ]
    )
    validate_incident_response_review_report_safe(t)
    return t


def render_incident_runbook_markdown(r):
    return _map("Incident Runbook", r.categories)


def render_audit_log_boundary_map_markdown(r):
    return _map("Audit Log Boundary Map", r.audit_log_boundaries)


def render_forensics_evidence_checklist_markdown(r):
    return _map("Forensics Evidence Checklist", r.forensics_evidence_types)


def _cell(v):
    t = sanitize_incident_response_value(v)
    return "'" + t if t.lstrip().startswith(("=", "+", "-", "@")) else t


def render_incident_scenario_matrix_csv(r):
    o = io.StringIO()
    w = csv.writer(o, lineterminator="\n")
    w.writerow(("category", "severity", "evidence_reference", "placeholder_only"))
    [
        w.writerow(
            tuple(
                _cell(v)
                for v in (
                    x.category.value,
                    x.severity.value,
                    x.evidence_type.value,
                    str(x.placeholder_only).lower(),
                )
            )
        )
        for x in r.scenario_matrix
    ]
    t = o.getvalue()
    validate_incident_response_review_report_safe(t)
    return t


def _root(p):
    p = Path(p)
    tmp = (
        p.is_absolute()
        and p.name.startswith("procore-intake-bridge-incident-response-")
        and (p.parent == Path("/tmp") or "pytest-" in p.as_posix())
    )
    if (
        ".." in p.parts
        or (p.is_absolute() and not tmp)
        or (not tmp and p.parts[:1] not in {(x,) for x in SAFE_ROOTS})
    ):
        raise IncidentResponseReviewBlockedError("Unsafe output root.")
    return p


def write_incident_response_review_artifacts(r, output_root):
    root = _root(output_root)
    a = {
        "incident-response-review-report.json": r.model_dump_json(indent=2),
        "incident-response-review-report.md": render_incident_response_review_markdown(r),
        "incident-runbook.md": render_incident_runbook_markdown(r),
        "audit-log-boundary-map.md": render_audit_log_boundary_map_markdown(r),
        "forensics-evidence-checklist.md": render_forensics_evidence_checklist_markdown(r),
        "incident-scenario-matrix.csv": render_incident_scenario_matrix_csv(r),
    }
    a["manifest.json"] = json.dumps(
        {
            "files": sorted(a),
            "sanitized": True,
            "live_operations": False,
            "collection_operations": False,
            "notification_operations": False,
        },
        indent=2,
    )
    root.mkdir(parents=True, exist_ok=True)
    for n, c in a.items():
        validate_incident_response_review_report_safe(c)
        (root / n).write_text(c)
    return IncidentResponseArtifactResult(
        status=r.status, output_directory=root.name, files=sorted(a)
    )
