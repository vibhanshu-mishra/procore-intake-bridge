# Evidence review and expiry

A private sandbox smoke ref requires authorized review, scope validation, status, and expiry.
Review records never copy the smoke report or raw Procore response into Git.

Phase C2 adds a local-only review, expiry, and renewal workflow for the placeholder evidence refs
defined by C1. It performs no Procore calls, external calls, evidence collection, notifications,
reviewer contact, approval, deployment, or production enablement.

## Public and private boundary

No real review or signoff belongs in this public repo. Public content is limited to fake examples
only. Those fake examples only support schemas, validators, renderers, tests, and documentation.
Real reviewer, approver, operator,
or customer identities; contact details; signatures; review activity; signoff records; evidence
contents; paths; URLs; reports; screenshots; payloads; databases; and attachments must remain in
an approved private system outside GitHub.

C1 organizes opaque evidence refs. C2 attaches placeholder-only review and expiry metadata to
those refs. B9 can use current review posture as private decision evidence, but no C2 status means
a pilot is approved.

## Statuses and expiry

Review statuses describe workflow posture:

- `not_started` and `needs_review` indicate outstanding work.
- `reviewed_placeholder` records a fake/template review state only.
- `accepted_placeholder` and `rejected_placeholder` are template decisions, never real signoff.
- `blocked` prevents gate use.
- `not_applicable` is nonblocking only when the item is not required for its gate.

Expiry statuses include `current`, `needs_review`, `expires_soon`, `expired`,
`renewal_required`, `blocked`, and `not_applicable`. Concrete ISO timestamps can be evaluated
offline. The expiry must follow the review time and cannot exceed the configured maximum window.
Missing or placeholder-only dates retain the declared placeholder status. Items inside the warning
window become `expires_soon`; past dates become `expired`. An expired accepted item must set
`renewal_required`.

## Local workflow

```bash
python scripts/print_evidence_review_template.py
python scripts/validate_evidence_review.py \
  examples/evidence-review/example_evidence_review_manifest.json
python scripts/check_evidence_expiry.py \
  examples/evidence-review/example_evidence_review_manifest.json
python scripts/generate_evidence_review_artifacts.py \
  examples/evidence-review/example_evidence_review_manifest.json \
  --output-root evidence-review-output
```

Use `--strict` to fail validation on unsafe content. Use `--strict-review` to fail while review or
renewal work remains. The expiry checker’s `--strict` mode fails for expired, renewal-required, or
gate-blocking required evidence.

Generated artifacts are ignored by Git. They contain a sanitized summary, expiry status report,
renewal checklist, unexecuted signoff template, review manifest template, and artifact manifest.
They exclude evidence contents, real identities and signoffs, signatures, credentials, URLs,
paths, raw reports, screenshots, payloads, attachments, and private approval records.

Acceptable placeholders include `REVIEWER_PLACEHOLDER`,
`PRIVATE_EVIDENCE_REF_PLACEHOLDER_SANDBOX_SMOKE`, and `REVIEWED_AT_PLACEHOLDER`. Blocked content
includes names, emails, phone numbers, numeric Procore IDs, customer domains, Authorization
material, tokens, signed URLs, `.env` assignments, database/storage URLs, local paths, raw
payloads or reports, and binary/generated evidence references.

For private handoff, validate only the metadata manifest, separately review and redact evidence in
the authorized private system, grant minimum reviewer access, and share only opaque refs through
an approved channel. Do not copy review or signoff records into this repo.

Future work may add a separately authorized private approval system, reviewer authentication,
access control, audit history, retention, notifications, escalation, and renewal scheduling. C2
implements none of those integrations.

C3 consumes only a C2 review-summary ref, status, expired count, and renewal-required count. It
never copies review artifacts, reviewer identities, or signoff records into the packet.
# C5 workspace bootstrap

The ignored C5 workspace includes placeholder-only evidence review and expiry metadata files.
Real reviewer identities, evidence, timestamps, decisions, and renewal records stay private.

An F2 Sandbox read-validation reference can be reviewed and expired like other opaque C1 refs.
C2 never ingests the report, raw RFI/Submittal records, identifiers, or API errors.
