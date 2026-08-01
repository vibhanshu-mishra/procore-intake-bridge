from pathlib import Path
from subprocess import run

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import IntakeRecord, SyncRun
from app.schemas.demo_data_experience import DemoDataInventoryItem, DemoDatasetKind
from app.services.demo_data_experience import (
    ARTIFACT_FILES,
    DemoDataExperienceBlockedError,
    build_demo_data_experience_report,
    build_demo_data_inventory,
    build_demo_dataset_plan,
    build_demo_reset_plan,
    build_demo_seed_plan,
    render_demo_data_inventory_csv,
    reset_demo_data,
    seed_demo_data,
    validate_demo_data_report_safe,
    write_demo_data_experience_artifacts,
)
from scripts.audit_public_safety import audit_paths
from scripts.check_docs_site import check_docs_site

ROOT = Path(__file__).resolve().parents[1]


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


@pytest.fixture
def demo_engine(tmp_path: Path):
    return create_engine(f"sqlite:///{tmp_path / 'demo.sqlite'}")


def test_dataset_and_seed_plans_cover_every_dataset_kind():
    plan = build_demo_dataset_plan(settings())
    assert {item.dataset_kind for item in plan} == set(DemoDatasetKind)
    assert build_demo_seed_plan(settings()).planned_total == sum(item.record_count for item in plan)


def test_seed_is_idempotent_in_isolated_sqlite(demo_engine):
    first = seed_demo_data(demo_engine, settings())
    inventory_before = build_demo_data_inventory(demo_engine, settings())
    second = seed_demo_data(demo_engine, settings())
    inventory_after = build_demo_data_inventory(demo_engine, settings())
    assert first.seeded_total > 0
    assert second.already_present_total > 0
    assert inventory_after == inventory_before


def test_seed_supports_dashboard_review_triage_attachment_and_export(demo_engine):
    seed_demo_data(demo_engine, settings())
    counts = {
        item.dataset_kind: item.record_count
        for item in build_demo_data_inventory(demo_engine, settings())
    }
    for kind in (
        DemoDatasetKind.INTAKE_RECORDS,
        DemoDatasetKind.ATTACHMENT_MANIFESTS,
        DemoDatasetKind.LIFECYCLE_STATES,
        DemoDatasetKind.LIFECYCLE_EVENTS,
        DemoDatasetKind.TRIAGE_SIGNALS,
        DemoDatasetKind.DASHBOARD_COUNTS,
        DemoDatasetKind.EXPORT_SUMMARIES,
    ):
        assert counts[kind] > 0


def test_inventory_is_fake_local_and_reset_eligible(demo_engine):
    seed_demo_data(demo_engine, settings())
    inventory = build_demo_data_inventory(demo_engine, settings())
    assert inventory
    assert all(item.fake_only and item.local_only and item.reset_eligible for item in inventory)
    assert all(item.marker == "J2_DEMO_" for item in inventory)


def test_reset_plan_is_non_destructive(demo_engine):
    seed_demo_data(demo_engine, settings())
    before = build_demo_data_inventory(demo_engine, settings())
    plan = build_demo_reset_plan(settings())
    after = build_demo_data_inventory(demo_engine, settings())
    assert plan.confirmation_required
    assert before == after


@pytest.mark.parametrize("confirmation", ["", "reset demo data", "RESET DEMO DATA "])
def test_reset_rejects_every_non_exact_confirmation(demo_engine, confirmation):
    seed_demo_data(demo_engine, settings())
    with pytest.raises(DemoDataExperienceBlockedError, match="Exact"):
        reset_demo_data(demo_engine, settings(), confirmation)


def test_reset_removes_only_demo_marked_records(demo_engine):
    seed_demo_data(demo_engine, settings())
    with Session(demo_engine) as session:
        demo = session.scalar(select(IntakeRecord).limit(1))
        session.add(
            IntakeRecord(
                source_type="rfi",
                procore_project_id="LOCAL_TEST_PROJECT",
                procore_item_id="LOCAL_TEST_UNMARKED",
                number="TEST-1",
                title="Synthetic unmarked test record",
                status="open",
                raw_payload_json={"fixture": "synthetic"},
                attachment_count=0,
                sync_run_id=demo.sync_run_id,
            )
        )
        session.commit()
    result = reset_demo_data(demo_engine, settings(), "RESET DEMO DATA")
    assert result.removed_total > 0
    with Session(demo_engine) as session:
        survivor = session.scalar(
            select(IntakeRecord).where(IntakeRecord.procore_item_id == "LOCAL_TEST_UNMARKED")
        )
        assert survivor is not None
        assert session.get(SyncRun, survivor.sync_run_id) is not None
        assert (
            session.scalar(
                select(func.count())
                .select_from(IntakeRecord)
                .where(IntakeRecord.procore_item_id.like("J2_DEMO_%"))
            )
            == 0
        )


def test_report_has_safe_scope_flags_and_validates():
    report = build_demo_data_experience_report(settings())
    assert report.fake_only and report.demo_only and report.local_sqlite_only
    assert report.idempotent_seed and report.reset_confirmation_required
    false_flags = (
        "external_call_attempted",
        "procore_call_attempted",
        "cloud_call_attempted",
        "external_db_connection_attempted",
        "sandbox_data_touched",
        "pilot_data_touched",
        "hosted_data_touched",
        "private_workspace_touched",
        "customer_data_touched",
        "private_report_contents_exposed",
        "secrets_exposed",
        "urls_exposed",
        "private_paths_exposed",
        "ids_exposed",
        "real_domains_exposed",
        "production_approval_claimed",
        "release_approval_claimed",
        "pilot_approval_claimed",
    )
    assert not any(getattr(report, field) for field in false_flags)
    validate_demo_data_report_safe(report)


def test_artifacts_are_path_safe_and_sanitized(tmp_path: Path):
    report = build_demo_data_experience_report(settings())
    with pytest.raises(DemoDataExperienceBlockedError):
        write_demo_data_experience_artifacts(report, tmp_path / ".." / "unsafe")
    output = tmp_path / "procore-intake-bridge-demo-data-test"
    result = write_demo_data_experience_artifacts(report, output)
    assert set(result.files) == set(ARTIFACT_FILES)
    assert not audit_paths(sorted(output.iterdir()))


def test_inventory_csv_neutralizes_formula_injection():
    item = DemoDataInventoryItem(
        dataset_kind=DemoDatasetKind.INTAKE_RECORDS,
        marker="=FORMULA",
        record_count=1,
    )
    assert "'=FORMULA" in render_demo_data_inventory_csv([item])


@pytest.mark.parametrize(
    "script,args",
    (
        ("plan_demo_seed.py", ()),
        ("plan_demo_reset.py", ()),
        ("check_demo_data.py", ()),
    ),
)
def test_read_only_cli_runs(script: str, args: tuple[str, ...]):
    result = run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_seed_and_reset_cli_use_only_temp_sqlite(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'cli-demo.sqlite'}"
    seed = run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/seed_demo_data.py"),
            "--database-url",
            url,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert seed.returncode == 0, seed.stderr
    refused = run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/reset_demo_data.py"),
            "--database-url",
            url,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0
    reset = run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/reset_demo_data.py"),
            "--database-url",
            url,
            "--confirm",
            "RESET DEMO DATA",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert reset.returncode == 0, reset.stderr


def test_j2_docs_and_audits_are_registered():
    assert not [finding for finding in check_docs_site(ROOT) if finding.level == "FAIL"]
    for relative in (
        "docs/demo-data-seed-reset.md",
        "docs/demo-seed-plan.md",
        "docs/demo-reset-guide.md",
        "examples/demo-data-experience/README.md",
    ):
        assert (ROOT / relative).is_file()
