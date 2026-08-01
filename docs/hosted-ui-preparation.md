# Hosted UI Preparation

Phase J4 prepares the existing local interface for possible future hosted evaluation. It is an
offline, public-safe review of routes, templates, documentation, and command guidance. It performs
no hosted deployment, live call, cloud operation, frontend build, or external UI-tool invocation.

J4 adds no frontend framework, package manager, authentication provider, account system, SSO,
OAuth, RBAC engine, session framework, WebSocket, external script/style/font/CDN asset, analytics,
tracking, telemetry, notification integration, file-serving endpoint, or public download route.

The invariant is explicit: no hosted deployment, no external frontend assets or tooling, and no
frontend build system. Hosted preparation is not production approval.

## Surface boundaries

- Product and admin dashboards, the review workspace, triage queue, and lifecycle controls require
  the existing admin protection. Lifecycle controls mutate local state only.
- Attachment review remains metadata-only and never serves local or cloud files.
- Export packs remain command-only local artifacts; there is no public export download route.
- Demo-ready surfaces depend on fake, demo-marked data in local SQLite.
- Sandbox, Pilot, Hosted, deployment, and security-readiness surfaces stay gated or require private
  review. Private data must never be placed in public examples or generated output.

The review can identify a hosted candidate, but that label is not permission to expose it. A hosted
Pilot still requires private infrastructure, authentication, authorization, secret, storage,
database, TLS, monitoring, incident-response, privacy, and security review.

Run the non-writing review commands:

```bash
make hosted-ui-review
make hosted-ui-page-inventory
make hosted-ui-readiness-checklist
make hosted-ui-private-gates
```

`make hosted-ui-artifact-check` uses temporary output and cleans it. Generated artifacts belong
only in ignored roots. Hosted UI preparation does not approve production, Pilot, release,
deployment, launch, certification, compliance, or Procore use.

Continue with the [page inventory](hosted-ui-page-inventory.md),
[readiness checklist](hosted-ui-readiness-checklist.md), and
[private gates](hosted-ui-private-gates.md).
