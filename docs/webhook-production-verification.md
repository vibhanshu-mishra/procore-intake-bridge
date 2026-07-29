# Webhook production verification

Phase B6 is a manual, documentation-aware harness for checking local webhook receiver,
normalization, deduplication, and queue assumptions with synthetic fixtures. It makes no
Procore or internet calls, creates no hooks, exposes no endpoint, enables no production
webhooks, starts no scheduler, and performs no Procore writes.

## Why the documentation gate exists

Webhook contracts change. Current documentation must be checked manually before use. The
working caution for B6 is that current Procore documentation appears to describe v2.0
company/project-scoped hook endpoints, while older v1.0 hooks/resources references are
deprecated as of 2025-09-15. The synthetic fixtures are “v2-like”; they are not official
samples and cannot establish the live contract.

This application does not create, register, update, activate, or delete webhooks. Any future
hook creation must be a separate, explicitly approved write-scope phase.

## Offline workflow

```bash
python scripts/print_webhook_verification_plan.py
python scripts/check_webhook_docs_record.py examples/webhook-verification/example_docs_record.json
```

Copy the example record outside version control, manually check current official
documentation, fill the timestamp, operator placeholder, observed version and scope,
signature and payload conclusions, and only then set all three statuses to `verified`.
Never paste tracking URLs, Authorization headers, webhook secrets, signatures, real IDs, or
payloads into the record.

Enable the harness only for the deliberate invocation, then run:

```bash
PROCORE_INTAKE_WEBHOOK_VERIFICATION_ENABLED=true \
python scripts/run_webhook_verification.py \
  --confirm I_UNDERSTAND_THIS_ONLY_VERIFIES_WEBHOOK_RECEIVER_BEHAVIOR \
  --docs-record /path/outside/repository/verified-docs-record.json
```

The run is blocked when disabled, confirmation is wrong, production is not explicitly
allowed, documentation is unverified, or limits are unsafe. The report contains only
statuses, counts, synthetic fingerprints, and sanitized summaries. It excludes raw
payloads, headers, signatures, Authorization values, secrets, destination URLs, and
exception details. Signature handling is only a configuration/readiness assumption in B6;
no real webhook secret is loaded or displayed.

Statuses mean: `passed` met the synthetic expectation; `failed` did not; `blocked` means a
safety gate stopped execution; `needs_review` requires operator judgment. Fixture-mode
deployment and local fixture tests do not require a report.

## Production checklist

- Re-check current official webhook docs and record who checked them and when.
- Confirm the API version, company/project scope, payload contract, supported events,
  signature algorithm and header, and replay behavior.
- Require signature verification and configure only a secret reference.
- Keep B6 reports and the docs record outside the repository.
- Review TLS, access controls, rate limits, observability, deduplication, queue retention,
  rollback, and incident ownership.
- Obtain separate explicit approval for hook registration or any Procore write scope.

## Emergency stop

Disable the receiver, require signatures, rotate the webhook secret through the external
secret system, remove the external route or tunnel, inspect and pause the event queue, and
purge local `webhook-verification-output` artifacts. Removing a Procore hook is outside B6
and must follow the separately approved production process.
A B7 production customer profile that plans webhooks depends on a verified B6 documentation
record, signature enforcement, and a webhook secret reference. B7 does not register or expose the
hook.
B8 diagnostics expose only webhook enablement, signature-enforcement posture, documentation
status, and aggregate queue counts. They never include webhook payloads, signatures, secrets,
headers, event identifiers, or verification reports.
When a B9 profile plans webhooks, B6 documentation, signature, and verification statuses must all
pass with a placeholder evidence reference. B9 never registers or exposes a hook.

C1 stores only webhook documentation, signature-review, and verification evidence refs. Raw
verification reports, webhook payloads, headers, signatures, and URLs remain private.
