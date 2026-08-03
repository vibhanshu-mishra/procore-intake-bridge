# Maintainer Quickstart (J9)

This page is the shortest safe path through the public repository. It is offline guidance only:
no release happened, no build happened, no tag happened, no publish happened, and no deployment
happened. Maintainer review is still required; private review remains required before live use.

## 1. Install locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Demo Mode needs no Procore credentials, cloud service, external database, or private workspace.

## 2. Run the safest checks

```bash
make quality
make safety-check
make docs-site-check
make maintainer-handoff
make maintainer-quickstart
make maintainer-review-checklist
make maintainer-command-plan
make maintainer-decision-log-template
```

These commands inspect local files or print sanitized guidance. They make no external calls, do
not read private reports, and do not build, publish, tag, release, or deploy anything.

## 3. Try Demo Mode

```bash
make start
make try-demo
```

Demo uses synthetic fixtures and local SQLite. `make try-demo` is non-destructive. Follow
[Demo seed and reset](demo-data-seed-reset.md) before any explicitly confirmed local reset.

## 4. Read the handoff in order

1. [Public maintainer handoff](maintainer-handoff.md)
2. [Review checklist](maintainer-review-checklist.md)
3. [Command plan](maintainer-command-plan.md)
4. [Decision-log template](maintainer-decision-log-template.md)
5. [Versioned `0.1.0` release handoff](versioned-release-handoff.md)

Then inspect the linked setup, API, hosted UI, security, and release documents as needed. Public
readiness is not production, Pilot, release, or deployment approval.

## 5. Keep private work private

Use placeholders such as `PRIVATE_REVIEW_REF_PLACEHOLDER` in public notes. Keep credentials,
customer identifiers, domains, reports, evidence, logs, screenshots, generated outputs, and
approval records outside Git. No J9 command contacts Procore, GitHub, a registry, cloud, DNS/TLS,
storage, or a database.

In short: no release happened, no build happened, no publish happened, no upload happened, no tag
happened, and no deployment happened. No production, Pilot, release, or deployment approval is
granted.
