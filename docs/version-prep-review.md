# Version Preparation Review

Phase J6 prepares package and version metadata for a later release-candidate review. The prepared
target version is `0.1.0`; it is release-candidate metadata, not a released version.

The review reads local files only: the canonical version source, `pyproject.toml`, changelog,
readiness guides, Makefile, and ignore rules. It performs no package build, Docker build, publish,
upload, tag, release, deployment, GitHub API call, package-registry call, or external packaging
operation. It adds no workflow automation and does not modify `.github/workflows`.

The release boundary is explicit: no package build, no publish, no tag, no release, and no deploy.
Prepared metadata is not production approval.

## Meaning of a prepared target

Consistency means the prepared target, package declaration, changelog language, and readiness
guidance agree. It does not mean an artifact exists or that a maintainer has approved a release.
Release-candidate review still requires human verification of metadata, licensing and ownership,
release notes, supported environments, security/private gaps, artifact contents, signing, registry
destination, credentials, publication controls, and rollback expectations.

Run the non-writing checks:

```bash
make version-prep-review
make package-metadata-summary
make version-source-map
make release-boundary-checklist
```

`make version-prep-artifact-check` uses temporary output and cleans it. Generated output belongs
only in ignored roots. J6 grants no production, Pilot, release, deployment, publication,
certification, compliance, or Procore approval.

Continue with the [package metadata summary](package-metadata-summary.md),
[version source map](version-source-map.md), and
[release boundary checklist](release-boundary-checklist.md).
