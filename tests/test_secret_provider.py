import pytest

from app.config import Settings
from app.security.secret_provider import (
    EnvSecretProvider,
    SecretNotFoundError,
    get_secret_provider,
    secret_name_to_env_var,
)


def test_live_mode_defaults_off():
    settings = Settings(_env_file=None)
    assert settings.procore_live_mode_enabled is False
    assert settings.secret_provider == "env"
    assert settings.default_polling_interval_minutes == 30
    assert settings.sync_lock_timeout_minutes == 30
    assert settings.worker_id == "local-dev-worker"
    assert settings.max_sync_lookback_days == 30
    assert settings.webhooks_enabled is True
    assert settings.require_webhook_signature is False
    assert settings.event_lock_timeout_minutes == 30
    assert settings.event_max_attempts == 5
    assert settings.event_worker_id == "local-dev-event-worker"
    assert settings.attachment_storage_backend == "local"
    assert str(settings.attachment_storage_root) == "storage/attachments"
    assert settings.attachment_max_filename_length == 160
    assert settings.attachment_allow_overwrite is False
    assert settings.attachment_fixture_downloads_only is True
    assert str(settings.packet_output_root) == "packet-output"
    assert settings.default_requester_company_name == "Your Company"
    assert settings.default_app_name == "Procore Intake Bridge"


def test_env_secret_provider_maps_and_resolves(monkeypatch):
    monkeypatch.setenv("PROCORE_INTAKE_SECRET_DEMO_GC_DMSA_SECRET", "synthetic-value")
    provider = EnvSecretProvider()
    assert provider.get_secret("demo_gc_dmsa_secret") == "synthetic-value"
    assert (
        secret_name_to_env_var("demo/gc dmsa-secret")
        == "PROCORE_INTAKE_SECRET_DEMO_GC_DMSA_SECRET"
    )


def test_env_secret_provider_missing_error_is_safe(monkeypatch):
    monkeypatch.delenv("PROCORE_INTAKE_SECRET_MISSING_REFERENCE", raising=False)
    with pytest.raises(SecretNotFoundError) as error:
        EnvSecretProvider().get_secret("missing_reference")
    assert "PROCORE_INTAKE_SECRET_MISSING_REFERENCE" in str(error.value)


def test_provider_factory_returns_env_provider():
    assert isinstance(get_secret_provider(Settings(_env_file=None)), EnvSecretProvider)
