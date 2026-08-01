# Release Boundary Checklist

Use this checklist for the prepared `0.1.0` target before any later release-candidate review:

- [ ] Canonical version source and `pyproject.toml` agree.
- [ ] Changelog labels the target as prepared or unreleased, never released.
- [ ] Package metadata and known missing/private items receive maintainer review.
- [ ] Public safety, quality, documentation, security, and readiness checks pass.
- [ ] Private security, legal, ownership, registry, signing, credential, and publication decisions
      remain outside the public repository.
- [ ] No package build or Docker build occurred in J6.
- [ ] No publish, upload, tag, release, or deployment occurred in J6.
- [ ] No GitHub/package-registry API was called and no workflow automation was added.
- [ ] A maintainer explicitly performs a later release-candidate review before any release action.

Completing this public checklist does not grant production, Pilot, release, deployment, package
publication, compliance, certification, or Procore approval.
