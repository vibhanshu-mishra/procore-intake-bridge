import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.sandbox_evidence_linkage import (
    SandboxEvidenceLinkageProfile,
    SandboxEvidenceRef,
    SandboxEvidenceStatus,
    SandboxEvidenceType,
)
from app.services.private_workspace import build_private_workspace_manifest
from app.services.sandbox_evidence_linkage import (
    ARTIFACT_NAMES,
    SandboxEvidenceLinkageBlockedError,
    build_default_sandbox_evidence_profile,
    build_sandbox_evidence_linkage_report,
    validate_sandbox_evidence_profile,
    validate_sandbox_evidence_report_safe,
    write_sandbox_evidence_linkage_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/sandbox-evidence-linkage/example_sandbox_evidence_profile.json"


def settings() -> Settings:
    return Settings(_env_file=None)


def example_profile() -> SandboxEvidenceLinkageProfile:
    return SandboxEvidenceLinkageProfile.model_validate_json(EXAMPLE.read_text())


def finding_codes(profile: SandboxEvidenceLinkageProfile) -> set[str]:
    return {
        item.code for item in validate_sandbox_evidence_profile(profile, settings())
    }


def test_default_profile_and_example_are_placeholder_only() -> None:
    for profile in (build_default_sandbox_evidence_profile(settings()), example_profile()):
        payload = profile.model_dump_json()
        assert "PLACEHOLDER" in payload
        assert "http://" not in payload and "https://" not in payload
        assert str(ROOT) not in payload
        assert not validate_sandbox_evidence_profile(profile, settings())


def test_required_refs_map_to_all_pilot_workflows_without_approval() -> None:
    report = build_sandbox_evidence_linkage_report(example_profile(), settings())
    assert report.status == SandboxEvidenceStatus.ACCEPTED_PLACEHOLDER
    assert report.required_refs_present
    assert report.refs_total == 6
    for mapping in (
        report.pilot_readiness_mapping,
        report.approval_packet_mapping,
        report.flow_mapping,
        report.evidence_review_mapping,
    ):
        assert mapping.reference_placeholders
        assert mapping.human_review_required
        assert not mapping.approval_granted
        assert not mapping.report_contents_included
    assert not report.pilot_approved
    validate_sandbox_evidence_report_safe(report)


def test_missing_required_refs_need_review_not_approval() -> None:
    profile = example_profile().model_copy(
        update={"sandbox_smoke_ref": "", "sandbox_read_validation_ref": ""}
    )
    report = build_sandbox_evidence_linkage_report(profile, settings())
    assert report.status == SandboxEvidenceStatus.NEEDS_REVIEW
    assert not report.required_refs_present
    assert not report.pilot_approved


def test_too_many_refs_are_blocked() -> None:
    profile = example_profile().model_copy(
        update={
            "evidence_refs": [
                SandboxEvidenceRef(
                    evidence_type=SandboxEvidenceType.SANDBOX_SMOKE,
                    evidence_ref=f"SANDBOX_EVIDENCE_REF_PLACEHOLDER_{index}",
                )
                for index in range(21)
            ]
        }
    )
    assert "too_many_refs" in finding_codes(profile)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        ("notes", ["raw smoke report contents: MUST_NOT_APPEAR"], "report_contents"),
        ("notes", ["https://private.example.invalid/result"], "url"),
        (
            "notes",
            ["postgresql://test-user:test-password@private.invalid/db"],
            "database_url",
        ),
        ("notes", ["operator@example.invalid"], "email"),
        ("notes", ["Call 312-555-0199"], "phone"),
        ("reviewer_placeholder", "Jane Smith", "profile_placeholders"),
        ("notes", ["Procore project 123456789"], "real_id"),
        ("notes", ["/Users/private/reports/result.json"], "absolute_path"),
        ("notes", ["Authorization: Bearer test-token-value"], "authorization"),
        (
            "notes",
            ["https://private.invalid/file?signature=MUST_NOT_APPEAR"],
            "url",
        ),
        ("notes", ["Evidence equals approval"], "approval_claim"),
        (
            "notes",
            ['{"id": "RFI_PRIVATE", "subject": "MUST_NOT_APPEAR"}'],
            "report_contents",
        ),
        ("notes", ["sandbox-read-report.json"], "private_artifact"),
    ),
)
def test_unsafe_private_or_approval_content_is_blocked(
    field: str,
    value,
    expected: str,
) -> None:
    profile = example_profile().model_copy(update={field: value})
    assert expected in finding_codes(profile)
    assert (
        build_sandbox_evidence_linkage_report(profile, settings()).status
        == SandboxEvidenceStatus.BLOCKED
    )


def test_generated_artifacts_are_safe_and_exact(tmp_path: Path) -> None:
    root = tmp_path / "sandbox-evidence-output"
    result = write_sandbox_evidence_linkage_artifacts(
        example_profile(),
        root,
        settings(),
    )
    output = root / "example-sandbox-evidence-linkage"
    assert result.files == ARTIFACT_NAMES
    assert result.output_directory == "example-sandbox-evidence-linkage"
    assert set(path.name for path in output.iterdir()) == set(ARTIFACT_NAMES)
    combined = "\n".join(path.read_text() for path in output.iterdir())
    assert str(tmp_path) not in combined
    assert "http://" not in combined and "https://" not in combined
    assert "MUST_NOT_APPEAR" not in combined
    assert '"pilot_approved": false' in combined


def test_artifact_generation_blocks_traversal() -> None:
    with pytest.raises(SandboxEvidenceLinkageBlockedError):
        write_sandbox_evidence_linkage_artifacts(
            example_profile(),
            Path("../sandbox-evidence-output"),
            settings(),
        )


@pytest.mark.parametrize(
    ("script", "args"),
    (
        ("print_sandbox_evidence_linkage_template.py", ()),
        (
            "check_sandbox_evidence_linkage.py",
            ("examples/sandbox-evidence-linkage/example_sandbox_evidence_profile.json",),
        ),
        ("print_sandbox_evidence_mapping.py", ()),
    ),
)
def test_nonwriting_clis_are_safe(script: str, args: tuple[str, ...]) -> None:
    result = subprocess.run(
        [sys.executable, f"scripts/{script}", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT) not in result.stdout
    assert "http://" not in result.stdout and "https://" not in result.stdout
    assert "MUST_NOT_APPEAR" not in result.stdout


def test_generation_cli_writes_temp_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "sandbox-evidence-output"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_sandbox_evidence_linkage_artifacts.py",
            str(EXAMPLE.relative_to(ROOT)),
            "--output-root",
            str(root),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["files"] == ARTIFACT_NAMES
    assert str(root) not in result.stdout


def test_make_targets_keep_artifact_generation_out_of_quality() -> None:
    makefile = (ROOT / "Makefile").read_text()
    targets = (
        "sandbox-evidence-template",
        "sandbox-evidence-check",
        "sandbox-evidence-mapping",
        "sandbox-evidence-artifact-check",
    )
    for target in targets:
        assert f"{target}:" in makefile
        result = subprocess.run(
            ["make", target],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    quality = makefile.split("quality:", 1)[1].splitlines()[0]
    assert all(target in quality for target in targets[:3])
    assert "sandbox-evidence-artifact-check" not in quality
    assert "generate_sandbox_evidence_linkage_artifacts.py" not in quality


def test_private_workspace_contains_linkage_placeholder() -> None:
    manifest = build_private_workspace_manifest("sandbox_and_pilot", settings())
    paths = {item.relative_path for item in manifest.files}
    assert "evidence/sandbox-evidence-linkage.private.json" in paths


def test_docs_linkage_is_private_review_only() -> None:
    linkage = (ROOT / "docs/sandbox-evidence-linkage.md").read_text().casefold()
    mapping = (ROOT / "docs/sandbox-evidence-to-pilot.md").read_text().casefold()
    for phrase in (
        "does not read source report contents by default",
        "does not prove",
        "human evidence review",
        "stay private",
    ):
        assert phrase in linkage
    for marker in (
        "c1 private evidence manifest",
        "c2 review and expiry",
        "b9 pilot readiness",
        "c3 pilot approval packet",
        "d5 sandbox-to-pilot flow",
    ):
        assert marker in mapping
    assert "does not mean a pilot is approved" in mapping
    assert "make sandbox-evidence-mapping" in (
        ROOT / "docs/walkthrough-pilot.md"
    ).read_text().casefold()
