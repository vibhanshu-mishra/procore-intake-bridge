import json
import re

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.onboarding_packets import OnboardingPacket
from app.schemas.onboarding import (
    OnboardingPacketCreate,
    OnboardingPacketExportResponse,
    OnboardingPacketPreviewResponse,
    OnboardingPacketSection,
    PermissionChecklistItem,
    TroubleshootingChecklistItem,
)


class OnboardingPacketError(RuntimeError):
    pass


def build_permission_checklist(
    requested_tools: list[str] | None = None,
) -> list[PermissionChecklistItem]:
    tools = set(requested_tools or ["rfis", "submittals"])
    items = []
    if "rfis" in tools:
        items.append(
            PermissionChecklistItem(
                category="required",
                tool="RFIs",
                access="Read Only",
                rationale="Read explicitly permitted project RFIs and visible attachments.",
            )
        )
    if "submittals" in tools:
        items.append(
            PermissionChecklistItem(
                category="required",
                tool="Submittals",
                access="Read Only",
                rationale="Read explicitly permitted project Submittals and visible attachments.",
            )
        )
    items.extend(
        [
            PermissionChecklistItem(
                category="required",
                tool="Project access",
                access="Explicitly permitted projects only",
                rationale="The DMSA should not receive unrelated project access.",
            ),
            PermissionChecklistItem(
                category="required",
                tool="Attachments",
                access="Visible through RFIs/Submittals only",
                rationale="No separate broad document-library access is requested.",
            ),
            PermissionChecklistItem(
                category="optional",
                tool="RFI webhooks",
                access="Created/updated events",
                rationale="Reduce intake latency; polling remains the fallback.",
            ),
            PermissionChecklistItem(
                category="optional",
                tool="Submittal webhooks",
                access="Created/updated events",
                rationale="Reduce intake latency; polling remains the fallback.",
            ),
        ]
    )
    for tool in (
        "Financial tools",
        "Directory administration",
        "Drawings/specifications",
        "Upload permissions",
        "Create/update/delete permissions",
        "Approval/submission permissions",
        "Administrative permissions outside installation/authorization",
    ):
        items.append(
            PermissionChecklistItem(
                category="not_requested",
                tool=tool,
                access="Not requested by default",
                rationale="Outside the read-only RFI/Submittal intake scope.",
            )
        )
    return items


def build_data_access_summary(requested_tools: list[str]) -> list[str]:
    resources = []
    if "rfis" in requested_tools:
        resources.append("RFI metadata, status, dates, and visible attachment metadata.")
    if "submittals" in requested_tools:
        resources.append(
            "Submittal metadata, status, dates, and visible attachment metadata."
        )
    resources.extend(
        [
            "Minimal project/company identifiers needed to match the permitted connection.",
            "No financial tools or unrelated project data are requested by default.",
        ]
    )
    return resources


def build_safety_summary() -> list[str]:
    return [
        "Read-only: the app performs no Procore writes.",
        "No creates, updates, deletes, approvals, submissions, closures, or uploads.",
        "No financial access is requested by default.",
        "No unrelated project access is requested.",
        "Raw signed attachment URLs are never stored.",
        "No external AI/model calls are made.",
        "The GC/Owner controls project and tool permissions and can revoke access.",
        "Secrets and installation keys are referenced, not stored in this packet.",
    ]


def build_installation_steps() -> list[str]:
    return [
        "Confirm the private app identity, requester, and intended read-only scope.",
        "Review the requested project list and remove any project not approved.",
        "Configure or install the private app using an approved App Version Key "
        "supplied through a separate secure channel.",
        "Assign the DMSA only to approved projects and grant the minimum checklist permissions.",
        "Verify current Procore documentation and your company's current "
        "UI/workflow; labels and steps may change.",
        "Run the Bridge health check and resolve any read-access findings before enabling intake.",
        "Record the GC/Owner contact who can change or revoke access.",
    ]


def build_troubleshooting_checklist() -> list[TroubleshootingChecklistItem]:
    return [
        TroubleshootingChecklistItem(
            symptom="Credentials or client construction fail",
            checks=[
                "Confirm the private app/DMSA credential references are current.",
                "Confirm sandbox versus production configuration matches.",
                "Rotate credentials through the approved secret channel if necessary.",
            ],
        ),
        TroubleshootingChecklistItem(
            symptom="Project is not visible",
            checks=[
                "Confirm the DMSA is assigned to the requested project.",
                "Confirm the project ID matches the approved list.",
                "Confirm the GC/Owner company context is correct.",
            ],
        ),
        TroubleshootingChecklistItem(
            symptom="RFIs or Submittals are unavailable",
            checks=[
                "Confirm the corresponding tool is enabled on the project.",
                "Confirm Read Only permission is granted to the DMSA.",
                "Confirm the sync profile enables the corresponding source.",
            ],
        ),
        TroubleshootingChecklistItem(
            symptom="Attachments are unavailable",
            checks=[
                "Confirm the attachment is visible to the DMSA through its parent item.",
                "Confirm no separate document permission is being assumed.",
                "Use polling reconciliation after permission changes.",
            ],
        ),
    ]


def preview_onboarding_packet(
    request: OnboardingPacketCreate, settings: Settings | None = None
) -> OnboardingPacketPreviewResponse:
    resolved = settings or get_settings()
    requester = request.requester_company_name or resolved.default_requester_company_name
    app_name = request.app_name or resolved.default_app_name
    projects = _unique(request.requested_project_ids) or ["PROJECT_ID_PLACEHOLDER"]
    tools = _unique(request.requested_tools)
    permissions = build_permission_checklist(tools)
    safety = build_safety_summary()
    troubleshooting = build_troubleshooting_checklist()
    sections = _build_sections(
        request,
        requester=requester,
        app_name=app_name,
        projects=projects,
        tools=tools,
        permissions=permissions,
        safety=safety,
        troubleshooting=troubleshooting,
    )
    packet_json = render_onboarding_packet_json(
        request,
        requester=requester,
        app_name=app_name,
        projects=projects,
        tools=tools,
        permissions=permissions,
        safety=safety,
        troubleshooting=troubleshooting,
        sections=sections,
    )
    markdown = render_onboarding_packet_markdown(packet_json, sections)
    return OnboardingPacketPreviewResponse(
        markdown=markdown,
        json_packet=packet_json,
        sections=sections,
        permissions=permissions,
    )


def generate_onboarding_packet(
    session: Session,
    request: OnboardingPacketCreate,
    settings: Settings | None = None,
) -> tuple[OnboardingPacket, OnboardingPacketPreviewResponse]:
    preview = preview_onboarding_packet(request, settings)
    identity = preview.json_packet["identity"]
    packet = OnboardingPacket(
        connection_id=request.connection_id,
        sync_profile_id=request.sync_profile_id,
        packet_name=request.packet_name,
        packet_type="gc_owner_private_app_install",
        recipient_company_name=request.recipient_company_name,
        recipient_contact_name=request.recipient_contact_name,
        requester_company_name=identity["requester_company_name"],
        requester_contact_name=request.requester_contact_name,
        app_name=identity["app_name"],
        app_version_key_ref=request.app_version_key_ref,
        requested_project_ids_json=preview.json_packet["requested_projects"],
        requested_tools_json=preview.json_packet["requested_tools"],
        requested_permissions_json=[
            item.model_dump() for item in preview.permissions
        ],
        safety_summary_json=preview.json_packet["safety_summary"],
        generated_markdown=preview.markdown,
        generated_json=preview.json_packet,
        status="generated",
    )
    session.add(packet)
    session.commit()
    session.refresh(packet)
    return packet, preview


def render_onboarding_packet_markdown(
    packet_json: dict, sections: list[OnboardingPacketSection]
) -> str:
    lines = [f"# {packet_json['packet_name']}", ""]
    for section in sections:
        lines.extend([f"## {section.title}", ""])
        lines.extend(f"- {item}" for item in section.content)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_onboarding_packet_json(
    request: OnboardingPacketCreate,
    *,
    requester: str,
    app_name: str,
    projects: list[str],
    tools: list[str],
    permissions: list[PermissionChecklistItem],
    safety: list[str],
    troubleshooting: list[TroubleshootingChecklistItem],
    sections: list[OnboardingPacketSection],
) -> dict:
    return {
        "packet_name": request.packet_name,
        "packet_type": "gc_owner_private_app_install",
        "identity": {
            "recipient_company_name": request.recipient_company_name,
            "recipient_contact_name": request.recipient_contact_name,
            "requester_company_name": requester,
            "requester_contact_name": request.requester_contact_name,
            "app_name": app_name,
            "app_version_key_ref": request.app_version_key_ref
            or "APP_VERSION_KEY_REFERENCE_NOT_PROVIDED",
        },
        "requested_projects": projects,
        "requested_tools": tools,
        "permissions": [item.model_dump() for item in permissions],
        "data_access": build_data_access_summary(tools),
        "safety_summary": safety,
        "installation_steps": build_installation_steps(),
        "troubleshooting": [item.model_dump() for item in troubleshooting],
        "sections": [section.model_dump() for section in sections],
        "disclaimer": (
            "Procore Intake Bridge is an independent tool and is not affiliated "
            "with, endorsed by, or officially supported by Procore."
        ),
    }


def export_onboarding_packet_local(
    packet: OnboardingPacket, settings: Settings | None = None
) -> OnboardingPacketExportResponse:
    resolved = settings or get_settings()
    root = resolved.packet_output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(packet.packet_name)
    stem = f"packet-{packet.id}-{slug}"
    markdown_path = (root / f"{stem}.md").resolve()
    json_path = (root / f"{stem}.json").resolve()
    if not markdown_path.is_relative_to(root) or not json_path.is_relative_to(root):
        raise OnboardingPacketError("Packet export path escaped its output root.")
    markdown_path.write_text(packet.generated_markdown)
    json_path.write_text(json.dumps(packet.generated_json, indent=2, sort_keys=True) + "\n")
    return OnboardingPacketExportResponse(
        packet_id=packet.id,
        markdown_path=markdown_path.relative_to(root).as_posix(),
        json_path=json_path.relative_to(root).as_posix(),
        message="Markdown and JSON packet artifacts exported locally.",
    )


def _build_sections(
    request: OnboardingPacketCreate,
    *,
    requester: str,
    app_name: str,
    projects: list[str],
    tools: list[str],
    permissions: list[PermissionChecklistItem],
    safety: list[str],
    troubleshooting: list[TroubleshootingChecklistItem],
) -> list[OnboardingPacketSection]:
    required = [
        f"{item.tool}: {item.access} — {item.rationale}"
        for item in permissions
        if item.category == "required"
    ]
    return [
        _section("purpose", "A. Title and purpose", [
            f"{request.packet_name} requests controlled, read-only access for {app_name}.",
        ]),
        _section("audience", "B. Who this packet is for", [
            "Procore Company Admins and project administrators at "
            f"{request.recipient_company_name}.",
        ]),
        _section("product", "C. What Procore Intake Bridge does", [
            "Copies permitted RFI/Submittal metadata into the requester's local tracking workflow.",
        ]),
        _section("dmsa", "D. Why DMSA/private app access is needed", [
            "A dedicated service identity avoids dependence on an employee "
            "account and keeps access reviewable.",
        ]),
        _section("access", "E. Requested Procore access", [
            f"Requested tools: {', '.join(tools) or 'none'}.",
            "Access is read-only and limited to explicitly approved projects.",
        ]),
        _section("projects", "F. Requested projects", projects),
        _section("permissions", "G. Requested permissions", required),
        _section("data", "H. What data is read", build_data_access_summary(tools)),
        _section("does_not_do", "I. What the app does not do", safety),
        _section("attachments", "J. Attachment handling", [
            "Only attachments visible through permitted RFIs/Submittals are considered.",
            "Raw signed attachment URLs are never stored; A5 uses local "
            "manifests and fixture-only downloads.",
        ]),
        _section("events", "K. Webhook and polling behavior", [
            "Webhooks queue notifications but do not call Procore in the receiver.",
            "Read-only polling remains the fallback reconciliation mechanism.",
        ]),
        _section("security", "L. Security and secret handling", [
            "Credentials, tokens, webhook secrets, and App Version Keys are "
            "not embedded in this packet.",
            "The App Version Key reference identifies a separate secure handoff.",
        ]),
        _section("control", "M. GC/Owner control and revocation", [
            "The GC/Owner controls installation, projects, tools, and DMSA permissions.",
            "The GC/Owner can reduce or revoke access at any time.",
        ]),
        _section("installation", "N. Installation checklist", build_installation_steps()),
        _section("permission_checklist", "O. Permission checklist", [
            f"[{item.category}] {item.tool}: {item.access}"
            for item in permissions
        ]),
        _section("health", "P. Health-check checklist", [
            "Confirm credential references resolve in the approved runtime.",
            "Confirm company/project access and Read Only RFI/Submittal visibility.",
            "Confirm attachment visibility separately; metadata checks cannot prove every file.",
        ]),
        _section("troubleshooting", "Q. Troubleshooting", [
            f"{item.symptom}: {'; '.join(item.checks)}"
            for item in troubleshooting
        ]),
        _section("support", "R. Support/contact placeholder", [
            request.support_contact,
            f"Requesting organization: {requester}.",
        ]),
        _section("disclaimer", "S. Independent-tool disclaimer", [
            "Procore Intake Bridge is an independent tool and is not affiliated "
            "with, endorsed by, or officially supported by Procore.",
            "Verify current Procore documentation and internal policy before installation.",
        ]),
    ]


def _section(key: str, title: str, content: list[str]) -> OnboardingPacketSection:
    return OnboardingPacketSection(key=key, title=title, content=content)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_").lower()
    return slug[:80] or "onboarding"
