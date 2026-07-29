# Operator observability and support diagnostics

Phase B8 adds local-first, sanitized diagnostics and support-bundle tooling. It summarizes runtime
posture, dependency versions, safe route metadata, aggregate database and queue counts,
configuration posture, migration/readiness signals, and redaction status. It is not production
observability, monitoring, telemetry, APM, centralized logging, incident automation, or a claim
that the application is production-secure.

Diagnostics exclude environment values, complete database URLs, raw rows, RFI/Submittal data,
webhook payloads, source or signed URLs, filenames, local paths, file contents, logs, database
files, attachments, credentials, contacts, and customer data. Collection makes no Procore or
external calls. When no local database session is supplied, counts are reported as unavailable.

The read-only `GET /deployment/diagnostics` route inherits the B4 deployment-operator guard and
no-store security headers. It writes no files. `/health` and `/ready` remain public.

## Commands

```bash
python scripts/print_operator_diagnostics.py
python scripts/generate_support_bundle.py
python scripts/check_support_bundle_redaction.py support-output
```

Use `--output-root` to select another dedicated local directory. Path traversal is rejected and
CLI output contains only relative names. A support bundle contains exactly:

- `diagnostics.json`
- `diagnostics.md`
- `redaction-report.json`
- `manifest.json`

Support bundles are local only and ignored by Git. Raw logs, database files, attachments,
payloads, screenshots, `.env` files, and private reports are deliberately excluded. Redaction is
conservative: secret/token assignments, Authorization and bearer material, database and signed
URLs, cloud URLs, absolute paths, emails, phone-like values, environment assignments, and private
output paths are removed or cause strict validation to fail.

Before sharing a bundle, rerun the redaction checker, inspect all four files manually, confirm the
manifest, use an approved private transfer channel, and share only with the intended support
recipient. Never share logs, databases, `.env`, screenshots, downloaded attachments, payloads,
customer identifiers, URLs, tokens, or credentials alongside it.

## Emergency troubleshooting

- Disable live reads and webhook receiving.
- Keep admin/deployment operator protection enabled.
- Print diagnostics without a database session first.
- Inspect only aggregate queue and readiness status.
- Generate and validate a fresh local support bundle.
- Rotate affected credentials at their external owner if exposure is suspected.
- Preserve sanitized evidence and follow the private incident process.

Future work may add a separately reviewed production monitoring design, audited structured logs,
metrics, alerts, retention, access control, and incident integrations. B8 adds none of those and
introduces no Sentry, Datadog, New Relic, Honeycomb, OpenTelemetry, Prometheus, Grafana, or
external logging dependency.
B9 requires passed B8 diagnostics and support-bundle redaction evidence references. It never
copies support-bundle contents into a readiness profile or packet.

C1 records a diagnostics evidence ref only. Never copy a support bundle, logs, database records,
environment values, or diagnostic output into a public evidence manifest.
