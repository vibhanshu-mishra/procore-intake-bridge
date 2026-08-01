# Release readiness

## J1 relationship

The J1 installer experience is local-only and outside release execution. It performs no package
or Docker build, publish, tag, release, or deployment and grants no production, Pilot, release,
deployment, or Procore approval. Demo needs no credentials, cloud service, or external database;
Sandbox, Pilot, and Hosted remain separate gated paths.

## I9 relationship

I9 supplies offline closeout guidance but does not grant release, production, pilot, deployment,
launch, legal, privacy, compliance, certification, or Procore approval. Release maintainers must
resolve the private action register through authorized private review. I9 performs no build,
publish, scanner, encryption, retention enforcement, deletion/purge, or notification operation.

I7 non-writing checks validate public incident-response boundaries without collecting evidence.

I8 adds a separate offline [Final Security Readiness Review](final-security-readiness-review.md)
that aggregates I1–I7 and repository safety boundaries. It is not a release gate or approval: no
live scanner, external/Procore call, deployment, release, or build occurs, and private security
review remains required. It grants no production, pilot, release, legal, compliance, or
security-certification approval.

I6 checks declarations and package surfaces without building, publishing, tagging, or releasing.

I5 non-writing checks are included in quality; artifact generation remains separate, temporary, and ignored.

Release review includes the non-writing I4 policy checks. Artifact generation stays separately gated and temporary; retention policy does not establish legal compliance.

Phase E4 prepares a future public release for maintainer review. It does not publish anything,
create a release or tag, build a package or image, upload to a registry, or deploy.

Run:

```bash
make release-checklist
make release-readiness
make release-notes-draft
make safety-check
make walkthroughs-check
make quality
```

`ready_for_maintainer_review` means automated public checks found no blocker. It is not final
release approval. `needs_review` means a human decision or editorial review remains. `blocked`
means required public material is missing or unsafe.

The local checklist covers repository/public-data safety, command usability, docs, mode clarity,
tests, routes, secrets, generated output, examples, changelog, version and packaging metadata,
release-note drafting, known limitations, and manual maintainer approval.

Generated drafts are ignored and sanitized. They contain no private data or workstation paths.
Run `make release-readiness-artifact-check` for a disposable temporary generation check.

Before any future manual release decision, independently review:

- `make safety-check` and the route audit
- `make public-usability-audit` and `make walkthroughs-check`
- docs navigation, commands, examples, and known limitations
- staged files and ignored/generated output
- CHANGELOG and version metadata
- security, legal, operational, and maintainer approval

Any future tag or publication remains a separate manual action outside E4.

Review the [docs-site guide](docs-site.md) and [navigation map](docs-navigation.md) as part of
documentation completeness. E5 validates only a local navigation foundation; it does not publish
or deploy documentation.

Confirm F2's live `sandbox-read-validation` target remains absent from quality, onboarding,
walkthrough execution, release, and docs checks. Only its offline plan/preflight/template belong
in quality.
# Hosted deployment templates

Passing G4 template checks does not release or deploy anything. Publication, image creation,
provider setup, and deployment remain separate manual decisions after private production review.

G5 checks do not register webhooks, verify public URLs, issue certificates, or complete production
setup. Release review must confirm that real webhook data and evidence remain private and that
deployment and registration decisions remain manual.
## Final public readiness

Run `make final-readiness` as an additional offline maintainer aid. Its result is not release,
production, or pilot approval. It performs no live operation and reads no private report; private
values remain outside Git.

## Security review input

Run `make security-threat-model` before a future manual release decision. A ready result means
the public, placeholder-safe threat-model inputs are complete. It is not a security
certification, compliance determination, production approval, or substitute for authorized
private review.

Also run `make auth-boundary-audit`. It adds no login or identity provider and does not prove
runtime permissions; private deployment authorization review remains a separate manual gate.

Run `make webhook-security-review` and retain its needs-review items for private follow-up. It
performs no replay or registration and does not approve production webhook use.
