from enum import StrEnum

from pydantic import BaseModel, Field


class SupplyChainReviewStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class SupplyChainDecision(StrEnum):
    READY_FOR_SECURITY_REVIEW = "supply_chain_ready_for_security_review"
    NEEDS_REVIEW = "supply_chain_needs_review"
    BLOCKED = "supply_chain_blocked"
    NOT_RUN = "supply_chain_not_run"


class SupplyChainCategory(StrEnum):
    DEPENDENCY_DECLARATIONS = "dependency_declarations"
    OPTIONAL_EXTRAS_BOUNDARY = "optional_extras_boundary"
    DEVELOPMENT_DEPENDENCY_BOUNDARY = "development_dependency_boundary"
    RUNTIME_DEPENDENCY_BOUNDARY = "runtime_dependency_boundary"
    PACKAGE_METADATA_BOUNDARY = "package_metadata_boundary"
    SCRIPT_ENTRYPOINT_BOUNDARY = "script_entrypoint_boundary"
    MAKE_TARGET_BOUNDARY = "make_target_boundary"
    DOCKER_TEMPLATE_BOUNDARY = "docker_template_boundary"
    DOCS_SITE_BOUNDARY = "docs_site_boundary"
    GENERATED_ARTIFACT_BOUNDARY = "generated_artifact_boundary"
    RELEASE_READINESS_BOUNDARY = "release_readiness_boundary"
    WORKFLOW_AUTOMATION_BOUNDARY = "workflow_automation_boundary"
    PUBLISH_DEPLOY_BOUNDARY = "publish_deploy_boundary"
    EXTERNAL_SCANNER_BOUNDARY = "external_scanner_boundary"
    PUBLIC_EXAMPLE_FIXTURE_BOUNDARY = "public_example_fixture_boundary"


class DependencyBoundary(StrEnum):
    RUNTIME_DEPENDENCIES = "runtime_dependencies"
    OPTIONAL_AWS_SECRET_DEPENDENCIES = "optional_aws_secret_dependencies"
    OPTIONAL_AZURE_SECRET_DEPENDENCIES = "optional_azure_secret_dependencies"
    OPTIONAL_GCP_SECRET_DEPENDENCIES = "optional_gcp_secret_dependencies"
    OPTIONAL_CLOUD_SECRET_BUNDLE = "optional_cloud_secret_bundle"
    OPTIONAL_S3_STORAGE_DEPENDENCIES = "optional_s3_storage_dependencies"
    OPTIONAL_AZURE_BLOB_STORAGE_DEPENDENCIES = "optional_azure_blob_storage_dependencies"
    OPTIONAL_GCS_STORAGE_DEPENDENCIES = "optional_gcs_storage_dependencies"
    OPTIONAL_CLOUD_STORAGE_BUNDLE = "optional_cloud_storage_bundle"
    OPTIONAL_POSTGRES_DEPENDENCIES = "optional_postgres_dependencies"
    OPTIONAL_DOCS_DEPENDENCIES = "optional_docs_dependencies"
    TEST_DEPENDENCIES = "test_dependencies"
    DEVELOPMENT_DEPENDENCIES = "development_dependencies"


class PackageSurfaceBoundary(StrEnum):
    APP_PACKAGE_SURFACE = "app_package_surface"
    SCRIPTS_SURFACE = "scripts_surface"
    DOCS_SURFACE = "docs_surface"
    EXAMPLES_SURFACE = "examples_surface"
    TESTS_SURFACE = "tests_surface"
    DOCKER_TEMPLATE_SURFACE = "docker_template_surface"
    MAKEFILE_SURFACE = "makefile_surface"
    GENERATED_OUTPUT_SURFACE = "generated_output_surface"
    RELEASE_ARTIFACT_SURFACE = "release_artifact_surface"


class SupplyChainFinding(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class SupplyChainControl(BaseModel):
    name: str
    evidence_path: str
    description: str
    implemented: bool = True


class SupplyChainScenario(BaseModel):
    category: SupplyChainCategory
    expectation: str


class OptionalExtraMatrixItem(BaseModel):
    extra: str
    boundary: DependencyBoundary
    optional: bool = True
    external_call_attempted: bool = False


class SupplyChainReviewReport(BaseModel):
    status: SupplyChainReviewStatus
    decision: SupplyChainDecision
    categories: list[SupplyChainCategory]
    dependency_boundaries: list[DependencyBoundary]
    package_surface_boundaries: list[PackageSurfaceBoundary]
    controls: list[SupplyChainControl]
    scenarios: list[SupplyChainScenario]
    optional_extras_matrix: list[OptionalExtraMatrixItem]
    categories_total: int
    dependency_boundaries_total: int
    package_surface_boundaries_total: int
    optional_extra_matrix_items_total: int
    findings: list[SupplyChainFinding] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    external_scanner_attempted: bool = False
    package_audit_service_attempted: bool = False
    github_api_attempted: bool = False
    dependency_update_bot_added: bool = False
    workflow_changed: bool = False
    package_build_attempted: bool = False
    publish_attempted: bool = False
    release_attempted: bool = False
    deploy_attempted: bool = False
    docker_build_attempted: bool = False
    private_report_contents_exposed: bool = False
    secrets_exposed: bool = False
    package_registry_tokens_exposed: bool = False
    ci_secrets_exposed: bool = False
    signing_keys_exposed: bool = False
    urls_exposed: bool = False
    real_domains_exposed: bool = False
    private_paths_exposed: bool = False
    ids_exposed: bool = False
    legal_compliance_claimed: bool = False
    certification_claimed: bool = False
    production_approval_claimed: bool = False
    recommended_next_steps: list[str] = Field(default_factory=list)


class SupplyChainArtifactResult(BaseModel):
    status: SupplyChainReviewStatus
    output_directory: str
    files: list[str]
    sanitized: bool = True
    live_operations: bool = False
    scanner_operations: bool = False
    build_publish_release_deploy_operations: bool = False
