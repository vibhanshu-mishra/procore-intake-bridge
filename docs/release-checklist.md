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
- [ ] Review known limitations and the explicit not-production-ready language.
- [ ] Review CHANGELOG’s Unreleased section.
- [ ] Review `pyproject.toml` version and packaging metadata without building a package.
- [ ] Draft release notes with `make release-notes-draft`.
- [ ] Run `make release-readiness`.
- [ ] Obtain an explicit manual maintainer decision outside generated artifacts.
- [ ] If approved later, decide separately whether to create a tag/release manually.

Never commit credentials, customer data, evidence, approvals, reports, logs, screenshots,
databases, backups, packages, archives, build output, or release-readiness output.
