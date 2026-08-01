from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from app.config import Settings
from app.schemas.supply_chain_review import (
    DependencyBoundary,
    PackageSurfaceBoundary,
    SupplyChainCategory,
)
from app.services.supply_chain_review import (
    ARTIFACT_FILES,
    SupplyChainReviewBlockedError,
    build_supply_chain_review_report,
    render_optional_extras_matrix_csv,
    render_supply_chain_review_markdown,
    validate_supply_chain_review_report_safe,
    write_supply_chain_review_artifacts,
)
from scripts.audit_public_safety import audit_paths, audit_text
from scripts.audit_routes_read_only import application_routes, audit_routes

ROOT = Path(__file__).resolve().parents[1]


def settings(**kw):
    return Settings(_env_file=None, **kw)


def test_report_complete_and_offline():
    r = build_supply_chain_review_report(settings())
    assert r.status == "needs_review"
    assert set(r.categories) == set(SupplyChainCategory)
    assert set(r.dependency_boundaries) == set(DependencyBoundary)
    assert set(r.package_surface_boundaries) == set(PackageSurfaceBoundary)
    assert (
        r.categories_total,
        r.dependency_boundaries_total,
        r.package_surface_boundaries_total,
        r.optional_extra_matrix_items_total,
    ) == (15, 13, 9, 12)
    assert not any(
        (
            r.external_scanner_attempted,
            r.package_audit_service_attempted,
            r.github_api_attempted,
            r.dependency_update_bot_added,
            r.workflow_changed,
            r.package_build_attempted,
            r.publish_attempted,
            r.release_attempted,
            r.deploy_attempted,
            r.docker_build_attempted,
            r.secrets_exposed,
            r.package_registry_tokens_exposed,
            r.ci_secrets_exposed,
            r.signing_keys_exposed,
        )
    )
    validate_supply_chain_review_report_safe(r)


@pytest.mark.parametrize(
    "key",
    (
        "supply_chain_review_require_placeholders",
        "supply_chain_review_require_offline_only",
        "supply_chain_review_require_no_external_scanners",
        "supply_chain_review_require_no_publish_automation",
        "supply_chain_review_require_no_deploy_automation",
        "supply_chain_review_require_no_workflow_changes",
        "supply_chain_review_require_optional_extras_boundaries",
        "supply_chain_review_require_package_metadata",
        "supply_chain_review_require_generated_output_ignores",
    ),
)
def test_requirements_fail_closed(key):
    with pytest.raises(SupplyChainReviewBlockedError):
        build_supply_chain_review_report(settings(**{key: False}))


@pytest.mark.parametrize(
    "value",
    (
        {"github_token": "private-value"},
        {"registry_token": "private-value"},
        {"ci_secret": "private-value"},
        {"signing_key": "private-value"},
        {"message": "This is SLSA compliant"},
        {"message": "production-ready"},
        {"message": "reviewer@example.com"},
    ),
)
def test_validator_blocks(value):
    with pytest.raises(SupplyChainReviewBlockedError):
        validate_supply_chain_review_report_safe(value)


def test_renderers_csv_and_artifacts():
    r = build_supply_chain_review_report(settings())
    r.optional_extras_matrix[0].extra = "=FORMULA_PLACEHOLDER"
    assert "'=FORMULA" in render_optional_extras_matrix_csv(r)
    validate_supply_chain_review_report_safe(render_supply_chain_review_markdown(r))
    with TemporaryDirectory(prefix="procore-intake-bridge-supply-chain-", dir="/tmp") as d:
        result = write_supply_chain_review_artifacts(r, Path(d))
        assert set(result.files) == set(ARTIFACT_FILES)
        assert not result.live_operations
    for p in (Path("../outside"), Path("/"), Path("/tmp/unapproved")):
        with pytest.raises(SupplyChainReviewBlockedError):
            write_supply_chain_review_artifacts(r, p)


def test_commands_and_make():
    commands = (
        (".venv/bin/python", "scripts/run_supply_chain_review.py"),
        (".venv/bin/python", "scripts/print_dependency_boundary_map.py"),
        (".venv/bin/python", "scripts/print_package_surface_map.py"),
        (".venv/bin/python", "scripts/print_supply_chain_checklist.py"),
        (".venv/bin/python", "scripts/generate_supply_chain_review_artifacts.py", "--temporary"),
        ("make", "supply-chain-review"),
        ("make", "dependency-boundary-map"),
        ("make", "package-surface-map"),
        ("make", "supply-chain-checklist"),
        ("make", "supply-chain-artifact-check"),
    )
    for c in commands:
        x = run(c, cwd=ROOT, text=True, capture_output=True)
        assert x.returncode == 0, x.stdout + x.stderr


def test_docs_audits_routes(tmp_path):
    assert len(application_routes()) == 81 and audit_routes() == []
    p = tmp_path / "supply-chain-review.md"
    assert audit_text(p, "github_token=private-value")
    g = tmp_path / "supply-chain-review-output" / "r.md"
    g.parent.mkdir()
    g.write_text("placeholder")
    assert audit_paths([g])
    assert (
        "quality: supply-chain-review dependency-boundary-map package-surface-map "
        "supply-chain-checklist" in (ROOT / "Makefile").read_text()
    )
