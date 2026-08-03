# Release readiness

## J9 relationship

J9 provides a concise maintainer handoff on top of this offline readiness guidance. It does not
perform or approve a release: no release happened, no build happened, no tag happened, no publish
happened, and no deployment happened. Maintainer review is still required; private review remains
required, and production/Pilot/release/deployment approval is not granted.

## J8 relationship

J8 is a versioned `0.1.0` release handoff only. The target is prepared release metadata, not a
release. J8 adds review documents and placeholder examples but performs no package/Docker build,
publish, upload, tag, release, docs deployment, application deployment, external call, or workflow
change. Maintainer authorization and private security/legal/infrastructure review remain required;
no production, Pilot, hosted, release, or deployment approval is granted.

## J7 relationship

J7 consumes this readiness guidance as one checklist input; it does not replace its decision model
or execute release work. Prepared `0.1.0` remains metadata. No package/Docker build, publish, tag,
release, deployment, workflow change, or approval occurs, and maintainer review remains later.

## J6 relationship

The `0.1.0` value is a prepared target, not a released version. J6 checks local version/package,
changelog, and boundary metadata without building a package/image, publishing, tagging, releasing,
deploying, calling GitHub/registries, or changing workflows. A later human release-candidate review
and explicit release authorization remain required; J6 grants no approval.

## J5 relationship

Documentation-site polish neither executes nor approves a release or deployment. Local preview is
optional; J5 adds no GitHub Pages workflow, hosted publication, external analytics, tracking, search,
CDN asset, or operational approval.

## J4 relationship

Hosted UI preparation neither executes nor approves a release or deployment. It adds no frontend
build, external assets, analytics, telemetry, downloads, or file-serving routes. Existing protected
surfaces remain protected, and hosted evaluation requires private infrastructure/security review.

## J3 relationship

The J3 route reference is documentation only. It inspects 81 local routes without live calls or
external OpenAPI tooling and neither executes nor approves a release. It adds no public export
download, file-serving endpoint, or Procore write-back; production, Pilot, release, and deployment
approval remain outside J3.

## J2 relationship

The J2 local Demo seed/reset experience does not execute or approve a release. It uses
deterministic fake records and local SQLite only, makes no Procore, cloud, or external-database
call, and keeps `make try-demo` non-destructive. Confirmed reset affects only demo-marked local
records and cannot touch private workspace, Sandbox, Pilot, Hosted, cloud, or customer data. J2
grants no production, Pilot, release, deployment, or Procore approval.

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
