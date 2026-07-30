# Release readiness

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
