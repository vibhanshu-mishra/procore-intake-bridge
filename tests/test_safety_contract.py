from pathlib import Path

from app.config import get_settings
from app.services.procore_client import LiveProcoreDisabled, build_pyprocore_client_for_connection


def test_live_client_construction_is_disabled(connection):
    try:
        build_pyprocore_client_for_connection(connection)
    except LiveProcoreDisabled:
        pass
    else:
        raise AssertionError("Live client construction must fail closed")


def test_default_mode_is_fixture():
    assert get_settings().procore_mode == "fixture"


def test_docs_state_read_only_and_dmsa_safety():
    readme = Path("README.md").read_text().lower()
    safety = Path("docs/safety-model.md").read_text().lower()
    onboarding = Path("docs/dmsa-onboarding.md").read_text().lower()
    profiles = Path("docs/dmsa-credential-profiles.md").read_text().lower()
    webhooks = Path("docs/webhooks.md").read_text().lower()
    assert "read-only" in readme
    assert "no live" in readme
    assert "no procore writes" in safety
    assert "does not call procore" in webhooks
    assert "never writes to procore" in webhooks
    assert "dmsa" in onboarding
    assert "disabled by default" in profiles
    assert "plaintext" in profiles
    assert "no procore writes" in safety
