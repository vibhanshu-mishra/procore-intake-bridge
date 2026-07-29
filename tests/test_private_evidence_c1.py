import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.private_evidence import EvidenceManifest
from app.services.private_evidence import (
    PrivateEvidenceBlockedError,
    build_evidence_validation_report,
    build_fake_evidence_template,
    validate_evidence_manifest,
    write_private_evidence_workspace,
)

EXAMPLE = Path("examples/private-evidence/example_evidence_manifest.json")


def configured(**values) -> Settings:
    return Settings(_env_file=None, **values)


def load_example() -> EvidenceManifest:
    return EvidenceManifest.model_validate_json(EXAMPLE.read_text())


def updated(**values) -> EvidenceManifest:
    data = load_example().model_dump(mode="json")
    data.update(values)
    return EvidenceManifest.model_validate(data)


def item_updated(**values) -> EvidenceManifest:
    data = load_example().model_dump(mode="json")
    data["evidence_items"][0].update(values)
    return EvidenceManifest.model_validate(data)


def blocking_codes(manifest: EvidenceManifest, settings: Settings | None = None) -> set[str]:
    return {
        finding.code
        for finding in validate_evidence_manifest(
            manifest, settings or configured()
        )
        if finding.severity == "blocking"
    }


def test_fake_example_and_generated_template_validate():
    for manifest in (load_example(), build_fake_evidence_template()):
        report = build_evidence_validation_report(manifest, configured())
        assert report.valid is True
        assert report.blocking_findings_count == 0
        assert report.external_calls is False
        assert report.procore_calls is False
        assert report.file_contents_read is False


@pytest.mark.parametrize(
    ("updates", "code"),
    [
        ({"notes": ["Procore company 87654321"]}, "real_id"),
        ({"notes": ["customer-build.com"]}, "domain"),
        ({"notes": ["pilot.owner@customer-build.com"]}, "email"),
        ({"notes": ["312-555-0199"]}, "phone"),
        ({"notes": ["client_secret=fake-private-value"]}, "secret"),
        ({"notes": ["Authorization: Bearer fake-private-value"]}, "secret"),
        (
            {"notes": ["https://files.invalid/object?signature=fake-private-value"]},
            "signed_url",
        ),
        ({"notes": ["/Users/operator/private/evidence.json"]}, "absolute_path"),
        ({"notes": ["PRIVATE_TOKEN=fake-private-value"]}, "env_assignment"),
        (
            {"notes": ["postgresql://operator:placeholder@database.invalid/pilot"]},
            "database_url",
        ),
        ({"notes": ["s3://private-customer-bucket/evidence"]}, "storage_url"),
        ({"notes": ["raw payload: {project_id: private}"]}, "raw_report"),
        ({"notes": ["raw support bundle contents"]}, "raw_report"),
        ({"notes": ["raw smoke report contents"]}, "raw_report"),
        ({"notes": ["raw webhook report contents"]}, "raw_report"),
        ({"notes": ["PRIVATE_EVIDENCE_REF_PLACEHOLDER/report.pdf"]}, "binary_reference"),
        (
            {"notes": ["PRIVATE_EVIDENCE_REF_PLACEHOLDER/report.evidence-report.json"]},
            "binary_reference",
        ),
    ],
)
def test_unsafe_manifest_values_are_blocked(updates, code):
    assert code in blocking_codes(updated(**updates))


def test_raw_payload_like_extra_field_is_rejected_by_schema():
    data = load_example().model_dump(mode="json")
    data["raw_payload"] = {"project": {"id": "PROJECT_ID_PLACEHOLDER"}}
    with pytest.raises(ValueError):
        EvidenceManifest.model_validate(data)


def test_excessive_items_are_blocked():
    data = load_example().model_dump(mode="json")
    data["evidence_items"] *= 34
    manifest = EvidenceManifest.model_validate(data)
    assert "max_items" in blocking_codes(manifest)


def test_non_placeholder_owner_is_blocked():
    assert "owner_placeholder" in blocking_codes(
        item_updated(owner_placeholder="Named Pilot Owner")
    )


def test_production_profile_is_blocked_while_real_ids_are_disabled():
    assert "production_profile" in blocking_codes(updated(environment="production"))


def test_artifacts_write_only_under_output_root(tmp_path):
    root = tmp_path / "private-evidence-output"
    result = write_private_evidence_workspace(load_example(), root, configured())
    target = root / result.output_directory
    assert target.parent == root
    assert set(result.files) == {item.name for item in target.iterdir()}
    assert set(result.files) == {
        "README.md",
        "evidence-manifest.template.json",
        "evidence-index.md",
        "evidence-checklist.md",
        "evidence-redaction-report.json",
        "manifest.json",
    }
    contents = "\n".join(item.read_text() for item in target.iterdir())
    assert "Bearer private" not in contents
    assert "?signature=" not in contents
    assert "/Users/" not in contents
    assert str(tmp_path) not in contents
    assert result.external_calls is False
    assert result.file_contents_included is False


@pytest.mark.parametrize("root", [Path("."), Path("../escape"), Path("/")])
def test_artifact_path_traversal_is_blocked(root):
    with pytest.raises(PrivateEvidenceBlockedError):
        write_private_evidence_workspace(load_example(), root, configured())


def test_unsafe_manifest_is_not_written(tmp_path):
    root = tmp_path / "private-evidence-output"
    with pytest.raises(PrivateEvidenceBlockedError):
        write_private_evidence_workspace(
            updated(notes=["Authorization: Bearer fake-private-value"]),
            root,
            configured(),
        )
    assert not root.exists()


def test_cli_template_validation_and_generation(tmp_path):
    template = subprocess.run(
        [sys.executable, "scripts/print_private_evidence_template.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Example Pilot Evidence Workspace" in template.stdout
    validation = subprocess.run(
        [
            sys.executable,
            "scripts/validate_private_evidence_manifest.py",
            str(EXAMPLE),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"valid": true' in validation.stdout
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_private_evidence_workspace.py",
            str(EXAMPLE),
            "--output-root",
            str(tmp_path / "private-evidence-output"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(tmp_path) not in generated.stdout
    assert '"external_calls": false' in generated.stdout


def test_validate_cli_strict_fails_without_printing_secret(tmp_path):
    secret = "must-not-appear-private-credential"
    blocked = tmp_path / "blocked.json"
    blocked.write_text(
        json.dumps(updated(notes=[f"Authorization: Bearer {secret}"]).model_dump(mode="json"))
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_private_evidence_manifest.py",
            str(blocked),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert secret not in result.stdout


def test_generate_cli_rejects_output_root_traversal():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_private_evidence_workspace.py",
            str(EXAMPLE),
            "--output-root",
            "../unsafe-evidence-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unsafe output root" in result.stdout


def test_docs_and_public_examples_state_boundaries():
    docs = Path("docs/private-pilot-evidence.md").read_text().casefold()
    readme = Path("README.md").read_text().casefold()
    example_docs = Path("examples/private-evidence/README.md").read_text().casefold()
    assert "no real evidence" in docs
    assert "no procore calls" in docs
    assert "fake examples only" in docs
    assert "generated artifacts are ignored" in docs
    assert "phase c1" in readme
    assert "must never be committed" in example_docs


def test_no_c1_api_route_or_deployment_automation_was_added():
    route_sources = "\n".join(path.read_text() for path in Path("app/api").rglob("*.py"))
    assert "/private-evidence" not in route_sources
    assert not Path(".github/workflows/private-evidence.yml").exists()
