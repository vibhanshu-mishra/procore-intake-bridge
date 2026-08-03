# Pre-tag Reminder Checklist (J10)

This is a reminder for a future human maintainer before any tag or release decision. It is
not a command plan and does not perform a tag. “Post-release” means after a future
human-approved `0.1.0` release; the current repository contains prepared metadata only.

J10 performs no release, build, publish, upload, tag, deploy, issue filing, ticket creation, or
approval. Maintainer review and private security, legal, privacy, infrastructure, and ownership
review remain required.
There is no tag, no release, no build, no publish, and no deployment in this planning document.
This reminder is not approval and not certification.

## Review before any future tag decision

- [ ] Confirm the intended version and source map agree with the staged files.
- [ ] Read the release notes, scope summary, known limitations, and current project status.
- [ ] Run the existing local safety, docs, route, and quality checks; keep output disposable.
- [ ] Inspect the staged file list for credentials, private paths, reports, generated output, and
      customer identifiers.
- [ ] Confirm private security, privacy/legal, infrastructure, operations, and ownership reviews
      are recorded by opaque references outside Git.
- [ ] Confirm package, image, signing, registry, rollback, and support decisions are documented
      privately; this checklist does not build or publish them.
- [ ] Confirm no workflow, route, deployment, external integration, or approval claim was added.
- [ ] Record the human decision (`DEFER`, `REJECT`, or `AUTHORIZE_LATER`) outside this repository.

## Stop conditions

Stop and return to private review if a limitation is unresolved, evidence is stale, a value is not
sanitized, ownership is unclear, or scope changed. Do not open issues or tickets from this page.

Before any tag, require explicit human maintainer authorization before any release action; stop for
a human decision. After a future human-approved release, consult the [post-release roadmap](post-release-roadmap.md)
and [known limitations register](known-limitations-register.md). Until then, no release, build,
publish, tag, deploy, or approval is represented.
