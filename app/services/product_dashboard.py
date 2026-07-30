import json
import re
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.product_dashboard import (
    ProductDashboardCard,
    ProductDashboardCardStatus,
    ProductDashboardFinding,
    ProductDashboardGuidanceItem,
    ProductDashboardLink,
    ProductDashboardOverview,
    ProductDashboardStatus,
)
from app.services.attachment_review import build_attachment_review_workspace_summary
from app.services.intake_lifecycle import build_lifecycle_summary
from app.services.intake_review_workspace import build_intake_review_workspace_summary
from app.services.operator_export_pack import build_operator_export_metadata
from app.services.operator_triage_queue import build_operator_triage_summary


class ProductDashboardError(RuntimeError):
    pass


_URL = re.compile(r"https?://", re.IGNORECASE)
_PRIVATE_PATH = re.compile(r"(?:/Users/|/home/|/private/|[A-Z]:\\)", re.IGNORECASE)
_SECRET = re.compile(
    r"(?:access_token|refresh_token|client_secret|webhook_secret|admin_token|"
    r"app_version_key|password)\s*[:=]",
    re.IGNORECASE,
)
_FORBIDDEN_KEYS = {
    "raw_payload",
    "raw_payload_json",
    "payload_json",
    "source_url",
    "signed_url",
    "storage_key",
    "storage_path",
    "original_filename",
    "safe_filename",
    "filename",
    "file_contents",
    "contents",
    "procore_project_id",
    "procore_item_id",
    "procore_attachment_id",
}


def sanitize_product_dashboard_value(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if _URL.search(text) or _PRIVATE_PATH.search(text) or _SECRET.search(text):
        return "[redacted]"
    return text[:240]


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).casefold()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_product_dashboard_response_safe(response: BaseModel | dict | str) -> None:
    payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
    text = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
    keys = set(_walk_keys(payload)) if not isinstance(payload, str) else set()
    if (
        keys & _FORBIDDEN_KEYS
        or _URL.search(text)
        or _PRIVATE_PATH.search(text)
        or _SECRET.search(text)
    ):
        raise ProductDashboardError("Unsafe product dashboard response was blocked.")


def _status(value: object) -> ProductDashboardCardStatus:
    raw = getattr(value, "value", value)
    return (
        ProductDashboardCardStatus(raw)
        if raw in ProductDashboardCardStatus
        else ProductDashboardCardStatus.NEEDS_REVIEW
    )


def _card(
    group: str,
    title: str,
    status: ProductDashboardCardStatus,
    message: str,
    *,
    count: int | None = None,
    metrics: dict[str, int] | None = None,
    links: list[ProductDashboardLink] | None = None,
) -> ProductDashboardCard:
    return ProductDashboardCard(
        group=group,
        title=title,
        status=status,
        count=count,
        metrics=metrics or {},
        message=message,
        links=links or [],
    )


def _unsafe_settings(settings: Settings) -> bool:
    return any(
        (
            not settings.product_dashboard_mask_source_ids,
            not settings.product_dashboard_hash_source_ids,
            settings.product_dashboard_expose_raw_payloads,
            settings.product_dashboard_expose_private_paths,
        )
    )


def build_product_dashboard_cards(
    session: Session, settings: Settings
) -> list[ProductDashboardCard]:
    if not settings.product_dashboard_enabled:
        return [
            _card(
                "system",
                "Product dashboard",
                ProductDashboardCardStatus.DISABLED,
                "The local product dashboard is disabled.",
            )
        ]
    if settings.product_dashboard_fail_closed and _unsafe_settings(settings):
        return [
            _card(
                "system",
                "Product dashboard",
                ProductDashboardCardStatus.NEEDS_CONFIGURATION,
                "Unsafe exposure settings were blocked; restore the safe defaults.",
            )
        ]

    review = build_intake_review_workspace_summary(session, settings)
    lifecycle = build_lifecycle_summary(session, settings)
    triage = build_operator_triage_summary(session, settings)
    attachments = build_attachment_review_workspace_summary(session, settings)
    exports = build_operator_export_metadata(session, settings)
    cards = [
        _card(
            "system",
            "System health",
            ProductDashboardCardStatus.AVAILABLE,
            "Local read-oriented cockpit is available.",
            links=[
                ProductDashboardLink(
                    label="Admin details",
                    href="/admin",
                    description="Inspect sanitized local system summaries.",
                )
            ],
        ),
    ]
    if settings.product_dashboard_include_review_workspace:
        cards.append(
            _card(
                "intake_review",
                "Intake review",
                _status(review.status),
                review.message,
                count=review.total_records,
                metrics={"rfi": review.rfi_records, "submittal": review.submittal_records},
                links=[
                    ProductDashboardLink(
                        label="Open review workspace",
                        href="/review",
                        description="Review sanitized local intake records.",
                    )
                ],
            )
        )
    if settings.product_dashboard_include_lifecycle:
        cards.append(
            _card(
                "lifecycle",
                "Lifecycle distribution",
                ProductDashboardCardStatus.AVAILABLE
                if lifecycle.enabled and lifecycle.total_states
                else ProductDashboardCardStatus.EMPTY
                if lifecycle.enabled
                else ProductDashboardCardStatus.DISABLED,
                lifecycle.message,
                count=lifecycle.total_states,
                metrics={str(k.value): v for k, v in lifecycle.counts_by_status.items()},
                links=[
                    ProductDashboardLink(
                        label="Lifecycle view",
                        href="/review",
                        description="Inspect local lifecycle labels and history.",
                    )
                ],
            )
        )
    if settings.product_dashboard_include_triage:
        cards.append(
            _card(
                "triage",
                "Operator triage",
                _status(triage.status),
                "Deterministic local sorting helper only.",
                count=triage.total_records,
                metrics={item.bucket.value: item.count for item in triage.buckets},
                links=[
                    ProductDashboardLink(
                        label="Open triage",
                        href="/review/triage",
                        description="Use local sorting signals to organize review.",
                    )
                ],
            )
        )
    if settings.product_dashboard_include_attachments:
        cards.append(
            _card(
                "attachments",
                "Attachment metadata",
                _status(attachments.status),
                "Metadata-only manifest visibility; attachment files are never opened.",
                count=attachments.records_with_manifests,
                metrics={
                    "with_manifests": attachments.records_with_manifests,
                    "without_manifests": attachments.records_without_manifests,
                },
                links=[
                    ProductDashboardLink(
                        label="Review metadata",
                        href="/review/attachments",
                        description="Inspect safe attachment manifest counts.",
                    )
                ],
            )
        )
    if settings.product_dashboard_include_exports:
        cards.append(
            _card(
                "exports",
                "Operator export pack",
                _status(exports.status),
                "Exports are command-only and are never generated or downloaded here.",
                links=[
                    ProductDashboardLink(
                        label="Check export safety",
                        command="make operator-export-check",
                        description="Validate sanitized renderers without creating artifacts.",
                    ),
                    ProductDashboardLink(
                        label="Print export summary",
                        command="make operator-export-summary",
                        description="Print a sanitized local summary without writing files.",
                    ),
                ],
            )
        )
    if settings.product_dashboard_include_sandbox_guidance:
        cards.append(
            _card(
                "sandbox",
                "Sandbox preparation",
                ProductDashboardCardStatus.NEEDS_REVIEW,
                "Sandbox use is separate, private, manually gated preparation.",
                links=[
                    ProductDashboardLink(
                        label="Sandbox guide",
                        href="/docs/walkthrough-sandbox/",
                        description="Follow the private gated walkthrough.",
                    )
                ],
            )
        )
    if settings.product_dashboard_include_pilot_guidance:
        cards.append(
            _card(
                "pilot",
                "Pilot preparation",
                ProductDashboardCardStatus.NEEDS_REVIEW,
                "Pilot preparation remains private, gated, and manually evaluated.",
                links=[
                    ProductDashboardLink(
                        label="Pilot guide",
                        href="/docs/pilot-mode/",
                        description="Review private pilot preparation boundaries.",
                    )
                ],
            )
        )
    cards.append(
        _card(
            "safety",
            "Public-output safety",
            ProductDashboardCardStatus.AVAILABLE,
            "Keep generated outputs and private evidence outside the public repository.",
            links=[
                ProductDashboardLink(
                    label="Safety model",
                    href="/docs/safety-model/",
                    description="Review public and private data boundaries.",
                )
            ],
        )
    )
    return cards


def build_product_dashboard_guidance(settings: Settings) -> list[ProductDashboardGuidanceItem]:
    return [
        ProductDashboardGuidanceItem(
            mode="demo",
            title="Try the local Demo",
            message="Use fake local fixture data; no credentials or external calls are needed.",
            command="make try-demo",
        ),
        ProductDashboardGuidanceItem(
            mode="sandbox",
            title="Prepare privately",
            message="Sandbox steps are private and manually gated.",
            command="make prepare-sandbox",
        ),
        ProductDashboardGuidanceItem(
            mode="pilot",
            title="Review the gated plan",
            message="Pilot preparation stays private and does not indicate authorization.",
            command="make prepare-pilot",
        ),
    ]


def build_product_dashboard_overview(
    session: Session, settings: Settings
) -> ProductDashboardOverview:
    cards = build_product_dashboard_cards(session, settings)
    if len(cards) == 1 and cards[0].status in {
        ProductDashboardCardStatus.DISABLED,
        ProductDashboardCardStatus.NEEDS_CONFIGURATION,
    }:
        status = ProductDashboardStatus(cards[0].status.value)
    else:
        status = (
            ProductDashboardStatus.AVAILABLE
            if any(card.status is ProductDashboardCardStatus.AVAILABLE for card in cards)
            else ProductDashboardStatus.EMPTY
        )
    overview = ProductDashboardOverview(
        status=status,
        cards=cards,
        guidance=build_product_dashboard_guidance(settings),
        findings=[
            ProductDashboardFinding(
                code="readiness_boundary",
                message=(
                    "Dashboard readiness is local preparation context, not release, "
                    "production, or pilot authorization."
                ),
            )
        ],
    )
    validate_product_dashboard_response_safe(overview)
    return overview


def render_product_dashboard_markdown(overview: ProductDashboardOverview) -> str:
    lines = ["# Product Dashboard Overview", "", f"Status: {overview.status.value}", ""]
    for card in overview.cards:
        count = f" ({card.count})" if card.count is not None else ""
        lines.extend([f"## {card.title}{count}", "", f"{card.status.value}: {card.message}", ""])
        for link in card.links:
            if link.command:
                lines.append(f"- `{link.command}` — {link.description}")
        if any(link.command for link in card.links):
            lines.append("")
    lines.extend(
        [
            "Local database only; read-oriented; no Procore or external calls.",
            "No artifact was generated and no attachment file was read.",
            "Dashboard readiness is not release, production, or pilot authorization.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    validate_product_dashboard_response_safe(rendered)
    return rendered
