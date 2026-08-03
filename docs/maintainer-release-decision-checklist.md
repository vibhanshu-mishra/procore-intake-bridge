# Maintainer Release Decision Checklist

Use this checklist to decide whether to authorize a future `0.1.0` release. It is a review aid,
not an approval record. Keep completed evidence and private sign-off outside the public repository.

## Public, offline checks

- [ ] Confirm the target is `0.1.0` prepared metadata and the canonical version sources agree.
- [ ] Review the [release-candidate review](release-candidate-review.md) and J7 checklist.
- [ ] Read the [release notes for v0.1.0](release-notes-v0.1.0.md) and [scope summary](release-scope-summary.md).
- [ ] Run `make quality`, `make safety-check`, `make docs-site-check`, and the J8 review commands.
- [ ] Inspect the staged file list and confirm generated output remains ignored.
- [ ] Confirm examples contain placeholders only and no private values.

## Private review gates

- [ ] Obtain authorized security, privacy, legal, infrastructure, and ownership review.
- [ ] Validate supported environments, dependency posture, licensing, and artifact contents privately.
- [ ] Decide signing, registry destination, access controls, rollback, and incident ownership privately.
- [ ] Confirm production, Pilot, hosted, and deployment decisions are separately authorized.

## Decision boundary

- [ ] Record a maintainer decision outside Git: authorize later release, defer, or reject.
- [ ] If not explicitly authorized, stop. Do not build, publish, upload, tag, release, or deploy.

J8 itself performed no package/Docker build, publish, upload, tag, release, documentation
deployment, application deployment, GitHub/registry call, or workflow change. No production,
Pilot, hosted, release, deployment, legal, privacy, or security approval is granted by this page.
