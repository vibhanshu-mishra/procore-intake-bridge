# Versioned 0.1.0 Release Handoff (J8)

Phase J8 prepares a public, offline handoff for the target version `0.1.0`. **0.1.0 is
prepared as release metadata; it is not released by this phase.** A maintainer must review the
evidence and provide explicit authorization before any real release decision.

This handoff is documentation and local review material only. The J8 checks inspect repository
files and produce sanitized, disposable output when requested. They do not build a package or
Docker image, publish or upload artifacts, create a tag, create a release, deploy the application
or documentation, call GitHub or a package registry, or change workflow automation. Actual
tag/release/publish/deploy steps are outside J8.

For the explicit boundary: there was **no package build**, **no Docker build**, **no publish**,
**no upload**, **no tag**, **no release**, and **no deployment** in J8.
No actual release happened in J8.

## Recommended review order

1. Run the non-writing J8 commands in the [command reference](command-reference.md).
2. Read the [release notes draft](release-notes-draft.md) and [scope summary](release-scope-summary.md).
3. Work through the [maintainer release decision checklist](maintainer-release-decision-checklist.md).
4. Record evidence references without copying private reports into this repository.
5. If a maintainer later authorizes a release, use the [post-release checklist](post-release-checklist.md)
   as a separate, private operational aid.

## Final command review plan

Run the following in order; each is an offline review command and does not write a release:

```text
make quality
make safety-check
make docs-site-check
make versioned-release-handoff
make release-notes-draft
make release-scope-summary
make maintainer-release-decision-checklist
make post-release-checklist
make versioned-release-artifact-check
```

The artifact check is temporary-only. Do not add a build, publish, tag, release, deploy, or
workflow command to this plan.

## Handoff decisions

- `0.1.0` is a prepared target and package/version metadata value, not a published artifact.
- Maintainer authorization is still required; an automated `ready` result is not approval.
- Production, Pilot, hosted, deployment, legal, privacy, and security approvals are not granted.
- Private infrastructure and security review remains required before hosted or live use.
- No workflow automation, release automation, or deployment automation was added.

## Evidence boundary

The evidence matrix should contain only public checks, short sanitized notes, and references to
private review that remain outside Git. Do not include credentials, tokens, URLs, identities,
customer/project identifiers, private paths, logs, screenshots, reports, attachments, signed
links, cloud/database values, or approval records.

The handoff is complete when a human maintainer can decide whether to proceed later. It does not
mean that a release, tag, publication, upload, build, deployment, or documentation hosting event
occurred.

## Release evidence matrix shape

Record one row per public check with a short status, a sanitized evidence reference, and a known
limitation. References must point to private review systems without copying their contents here.
The matrix is evidence organization, not an approval record.
