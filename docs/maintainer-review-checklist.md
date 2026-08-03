# Maintainer Review Checklist (J9)

Use this checklist to decide what should happen next. It is not an approval record. No release,
build, tag, publish, or deployment occurred in J9; production/Pilot/release/deployment approval
is not granted. Maintainer review is still required and private review remains required.

## Public repository review

- [ ] Confirm the target is prepared `0.1.0` metadata, not a released version.
- [ ] Read [the handoff](maintainer-handoff.md), [the quickstart](maintainer-quickstart.md), and [the command plan](maintainer-command-plan.md).
- [ ] Run `make quality`, `make safety-check`, and `make docs-site-check`.
- [ ] Run all five non-writing J9 print/review commands.
- [ ] Run `make try-demo` and confirm Demo remains synthetic, local, and non-destructive.
- [ ] Inspect staged files, `.gitignore`, examples, changelog, version metadata, and docs links.
- [ ] Confirm no real credentials, customer data, IDs, domains, URLs, private paths, reports,
      screenshots, logs, generated output, or approval records are present.
- [ ] Confirm no new routes, workflow changes, package/deployment tooling, or external assets.

## Release handoff review

- [ ] Read [versioned release handoff](versioned-release-handoff.md), [release notes draft](release-notes-draft.md), and [release-candidate review](release-candidate-review.md).
- [ ] Verify included scope, known limitations, license, dependency posture, and package metadata.
- [ ] Confirm the handoff says no package/Docker build, publish/upload, tag, release, docs deploy,
      application deploy, or workflow change occurred.
- [ ] Treat every automated ready result as input for human review, never approval.

## Private gates before live or hosted use

- [ ] Obtain authorized security, privacy, legal, infrastructure, and ownership review.
- [ ] Validate customer scope, credentials, identities, provider permissions, database,
      evidence/expiry, rollback, incident ownership, and supported environments privately.
- [ ] Decide whether Sandbox, Pilot, Hosted, or production work is separately authorized.
- [ ] Keep private evidence and sign-off outside Git, using only
      `PRIVATE_REVIEW_REF_PLACEHOLDER` publicly.

## Decision boundary

- [ ] Record `REVIEW_DECISION_PLACEHOLDER` in the private decision log: defer, reject, or authorize
      a later manual release review.
- [ ] If explicit authorization is absent, stop. Do not build, tag, publish, release, or deploy.

J9 grants no production, Pilot, release, deployment, Procore, certification, compliance, or
publication approval.

No release happened, no build happened, no publish happened, no tag happened, and no deployment
happened. Maintainer review and private review remain required.
