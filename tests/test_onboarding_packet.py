import json

from app.config import Settings
from app.schemas.onboarding import OnboardingPacketCreate
from app.services.onboarding_packet import (
    build_permission_checklist,
    preview_onboarding_packet,
)


def request(**overrides):
    values = {
        "packet_name": "Synthetic GC Owner Packet",
        "recipient_company_name": "Example GC Company",
        "requester_company_name": "Example Engineering Firm",
        "requested_project_ids": ["111111", "222222"],
        "app_version_key_ref": "APP_VERSION_KEY_PLACEHOLDER",
    }
    values.update(overrides)
    return OnboardingPacketCreate(**values)


def test_default_permission_checklist_is_minimum_read_only():
    items = build_permission_checklist()
    required = {(item.tool, item.access) for item in items if item.category == "required"}
    not_requested = " ".join(
        item.tool for item in items if item.category == "not_requested"
    ).casefold()
    assert ("RFIs", "Read Only") in required
    assert ("Submittals", "Read Only") in required
    for term in ("create", "update", "delete", "approval", "submission", "upload"):
        assert term in not_requested
    assert "financial" in not_requested
    assert "administrative" in not_requested


def test_preview_contains_all_safety_and_control_sections():
    preview = preview_onboarding_packet(request())
    markdown = preview.markdown.casefold()
    assert preview.json_packet
    assert len(preview.sections) == 19
    assert "read-only" in markdown
    assert "no procore writes" in markdown
    assert "no creates" in markdown
    assert "no financial access" in markdown
    assert "raw signed attachment urls are never stored" in markdown
    assert "webhook and polling" in markdown
    assert "can reduce or revoke access" in markdown
    assert "independent tool" in markdown
    assert "not affiliated with, endorsed by" in markdown


def test_preview_has_no_raw_install_key_without_explicit_reference():
    preview = preview_onboarding_packet(
        request(app_version_key_ref=None)
    )
    serialized = json.dumps(preview.json_packet)
    assert "APP_VERSION_KEY_REFERENCE_NOT_PROVIDED" in serialized
    assert "client_secret" not in serialized
    assert "access_token" not in serialized


def test_settings_supply_safe_defaults():
    preview = preview_onboarding_packet(
        OnboardingPacketCreate(
            recipient_company_name="Example GC Company",
            requester_company_name=None,
            app_name=None,
        ),
        Settings(
            _env_file=None,
            default_requester_company_name="Your Company",
            default_app_name="Procore Intake Bridge",
        ),
    )
    assert preview.json_packet["identity"]["requester_company_name"] == "Your Company"
    assert preview.json_packet["identity"]["app_name"] == "Procore Intake Bridge"
