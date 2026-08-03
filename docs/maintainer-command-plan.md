# Maintainer Command Plan (J9)

Run this plan locally and in order. Every command is offline and advisory. No release happened;
these commands do not build packages or Docker images, publish, upload, tag, release, deploy, call
external services, or change workflows. Maintainer review and private review are still required.

| Order | Command | Purpose | Writes/live calls |
|---:|---|---|---|
| 1 | `make quality` | Run the complete offline developer suite. | Temporary only; no live call |
| 2 | `make safety-check` | Audit public data, routes, and safety boundaries. | No |
| 3 | `make docs-site-check` | Verify local docs navigation and safety wording. | No |
| 4 | `make maintainer-handoff` | Build the sanitized J9 handoff report. | No |
| 5 | `make maintainer-quickstart` | Print the shortest safe setup/review path. | No |
| 6 | `make maintainer-review-checklist` | Print public and private review gates. | No |
| 7 | `make maintainer-command-plan` | Print this ordered non-writing plan. | No |
| 8 | `make maintainer-decision-log-template` | Print a private decision record shape. | No |
| 9 | `make release-readiness` | Review prepared release metadata only. | No |
| 10 | `make final-readiness` | Inspect public repository readiness. | No |
| 11 | `make try-demo` | Optional synthetic local Demo walkthrough. | Local Demo DB only |
| 12 | `make maintainer-handoff-artifact-check` | Validate disposable sanitized artifacts. | Temporary only |

The artifact check must use a temporary ignored directory and remove it after validation. It must
not be used as a release, package, image, publication, tag, or deployment step.

## Separate private decisions

After the offline plan, a maintainer must privately review ownership, security/privacy/legal
requirements, supported environments, artifact and signing controls, registry access, rollback,
incident response, customer scope, and any Sandbox/Pilot/Hosted authorization. A ready report is
not approval. If any required decision is missing, record `REVIEW_DECISION_PLACEHOLDER` and stop.

No release happened, no build happened, no publish happened, no tag happened, and no deployment
happened. No production, Pilot, release, or deployment approval is granted.
