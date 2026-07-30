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
