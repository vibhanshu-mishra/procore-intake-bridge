from pathlib import Path

import pytest
import yaml

from tests.workflow_safety import (
    workflow_action_pin_findings,
    workflow_automation_findings,
    workflow_directory_findings,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
GITLEAKS_SHA = "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e"
TRIVY_SHA = "ed142fd0673e97e23eac54620cfb913e5ce36c25"
OPENQODEX_SHA = "2f2fa9e48c1f62a6123997eb14111140d8e22a74"


@pytest.mark.parametrize(
    "reference",
    (
        f"gitleaks/gitleaks-action@{GITLEAKS_SHA} # v3",
        f"actions/checkout@{CHECKOUT_SHA} # v7",
    ),
)
def test_full_commit_pins_are_allowed_for_external_actions(reference):
    assert workflow_action_pin_findings(f"steps:\n  - uses: {reference}\n") == []


def test_local_action_references_remain_supported():
    assert workflow_action_pin_findings("steps:\n  - uses: ./.github/actions/local-check\n") == []


@pytest.mark.parametrize(
    "reference",
    (
        "actions/checkout@v7",
        "gitleaks/gitleaks-action@v3",
        "openqodex/openqodex@v0",
    ),
)
def test_mutable_action_version_tags_are_rejected(reference):
    assert workflow_action_pin_findings(f"steps:\n  - uses: {reference}\n")


def test_shortened_commit_sha_is_rejected():
    assert workflow_action_pin_findings("steps:\n  - uses: gitleaks/gitleaks-action@e0c47f4\n")


def test_duplicate_action_references_are_checked_across_jobs():
    workflow = f"""
jobs:
  first:
    steps:
      - uses: actions/checkout@{CHECKOUT_SHA} # v7
  second:
    steps:
      - uses: actions/checkout@v7
"""
    findings = workflow_action_pin_findings(workflow)
    assert len(findings) == 1
    assert "actions/checkout@v7" in findings[0]


def test_workflow_descriptions_are_not_treated_as_executable_actions():
    workflow = """
name: Release and publishing readiness
# This workflow documents the release process; no deployment is performed.
jobs:
  review:
    steps:
      - name: Describe publishing boundary
        run: echo "release, publish, and deploy are manual"
"""
    assert workflow_action_pin_findings(workflow) == []
    assert workflow_automation_findings(workflow) == []


def _load_workflow(name: str) -> dict:
    path = ROOT / ".github" / "workflows" / name
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def _steps_by_name(job: dict) -> dict[str, dict]:
    return {step.get("name", step.get("uses", "")): step for step in job["steps"]}


def _action_references(workflow: dict) -> list[str]:
    return [
        step["uses"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]


def test_affected_workflows_use_the_verified_action_commits_everywhere():
    references = _action_references(_load_workflow("security-scans.yml"))
    references.extend(_action_references(_load_workflow("openqodex.yml")))

    expected = {
        "actions/checkout": CHECKOUT_SHA,
        "gitleaks/gitleaks-action": GITLEAKS_SHA,
        "aquasecurity/trivy-action": TRIVY_SHA,
        "openqodex/openqodex": OPENQODEX_SHA,
    }
    found = {}
    for reference in references:
        action, sha = reference.split("@", 1)
        assert action in expected
        assert sha == expected[action]
        found[action] = found.get(action, 0) + 1

    assert found == {
        "actions/checkout": 4,
        "gitleaks/gitleaks-action": 1,
        "aquasecurity/trivy-action": 1,
        "openqodex/openqodex": 1,
    }


def test_existing_security_workflow_triggers_permissions_and_scans_remain_unchanged():
    workflow = _load_workflow("security-scans.yml")

    assert workflow["on"] == {
        "push": {"branches": ["main"]},
        "pull_request": "",
        "workflow_dispatch": "",
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"secrets", "code-security", "vulnerabilities"}

    secrets_steps = _steps_by_name(workflow["jobs"]["secrets"])
    assert secrets_steps["Gitleaks"]["env"] == {
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "GITLEAKS_ENABLE_UPLOAD_ARTIFACT": "false",
        "GITLEAKS_ENABLE_COMMENTS": "false",
    }
    code_security_steps = _steps_by_name(workflow["jobs"]["code-security"])
    assert code_security_steps["Run Semgrep"]["run"] == (
        "semgrep scan --config p/default --metrics off ."
    )
    vulnerability_steps = _steps_by_name(workflow["jobs"]["vulnerabilities"])
    assert vulnerability_steps["Trivy"]["with"] == {
        "scan-type": "fs",
        "scan-ref": ".",
        "scanners": "vuln,misconfig,secret",
        "format": "table",
        "severity": "HIGH,CRITICAL",
        "exit-code": "1",
    }
    checkout_steps = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if step.get("uses", "").split("@", 1)[0] == "actions/checkout"
    ]
    assert len(checkout_steps) == 3
    assert all(step["with"].get("persist-credentials") == "false" for step in checkout_steps)


def test_existing_openqodex_workflow_configuration_remains_unchanged():
    workflow = _load_workflow("openqodex.yml")

    assert workflow["on"] == {"pull_request": ""}
    assert workflow["permissions"] == {
        "contents": "read",
        "security-events": "write",
        "actions": "read",
    }
    assert set(workflow["jobs"]) == {"scan"}
    steps = _steps_by_name(workflow["jobs"]["scan"])
    assert steps["Checkout repository"]["with"]["fetch-depth"] == "0"
    assert steps["Scan changed code"]["with"] == {
        "review": "off",
        "upload-sarif": "false",
        "fail-on-tool-error": "true",
    }


def test_all_repository_workflows_have_pinned_actions_and_no_release_operations():
    assert workflow_directory_findings(ROOT / ".github" / "workflows") == []
