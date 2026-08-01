# Release Candidate Command Plan

This is a non-writing validation plan for the prepared `0.1.0` metadata:

```bash
make version-prep-review
make docs-site-polish-review
make hosted-ui-review
make api-docs-review
make demo-data-check
make setup-experience-review
make final-readiness
make release-readiness
make safety-check
make release-candidate-review
```

The canonical [command reference](command-reference.md) owns command definitions; this page only
orders existing safe reviews. It contains no build, Docker build, publish, tag, release, deploy,
upload, registry, GitHub API, or workflow command.

Passing the plan can support later maintainer review. It does not create a release candidate,
authorize publication, or grant production, Pilot, release, or deployment approval.
