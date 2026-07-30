# Release checklist

This checklist prepares a maintainer decision; checking every box does not approve or create a
release.

- [ ] Run `make quality`.
- [ ] Run `make safety-check`, including public usability and read-only route audits.
- [ ] Run `make walkthroughs-check`.
- [ ] Confirm no private/generated files are staged.
- [ ] Confirm public examples and fixtures are fake or placeholder-only.
- [ ] Review README, QUICKSTART, command reference, walkthroughs, and internal links.
- [ ] Review Sandbox/Pilot boundaries and confirm no live/default behavior changed.
- [ ] Confirm F2 live Sandbox read validation remains separately gated and absent from quality.
- [ ] Review known limitations and the explicit not-production-ready language.
- [ ] Review CHANGELOG’s Unreleased section.
- [ ] Review `pyproject.toml` version and packaging metadata without building a package.
- [ ] Draft release notes with `make release-notes-draft`.
- [ ] Run `make release-readiness`.
- [ ] Obtain an explicit manual maintainer decision outside generated artifacts.
- [ ] If approved later, decide separately whether to create a tag/release manually.

Never commit credentials, customer data, evidence, approvals, reports, logs, screenshots,
databases, backups, packages, archives, build output, or release-readiness output.
# Hosted template review

- [ ] Confirm hosted profiles and snippets remain placeholder-only.
- [ ] Confirm no provider IDs, registry references, domains, secrets, or generated output are tracked.
- [ ] Confirm release and deployment remain manual and outside this repository.
- [ ] Confirm HTTPS/webhook profiles remain placeholder-only.
- [ ] Confirm no URL, domain, DNS record, certificate/key/CSR, ACME value, secret, webhook ID, or report is tracked.
- [ ] Confirm no public verification or webhook registration occurred.
