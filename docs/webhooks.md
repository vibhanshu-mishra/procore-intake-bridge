# Webhooks and the local event queue

Webhooks let Procore notify the Bridge that an RFI or Submittal may have changed. They reduce intake
latency, while polling remains the recovery and reconciliation fallback if delivery is delayed,
duplicated, or missed.

## Store first, process later

The webhook receiver does not call Procore and does not run sync immediately. It reads the raw JSON
body, applies the configured signature policy, sanitizes credential-like payload fields,
normalizes flexible event shapes, deduplicates the delivery, and stores one `WebhookEvent`.
Separating receipt from processing keeps response time bounded and lets retries, locks, and failure
state remain explicit.

Relevant RFI and Submittal events enter `queued` state. Unknown resource types are stored as
`skipped` rather than causing receiver errors. Raw request headers are never stored, and event API
responses omit the raw payload.

## Deduplication and replay

An event ID from the configured header or payload is the primary deduplication key. If it is absent,
the normalizer creates a stable SHA-256 fingerprint of the sanitized canonical payload. The
database enforces uniqueness, including for concurrent duplicate deliveries.

Replay resets local queue state, locks, failures, and availability for an existing event. Replay
does not contact or mutate Procore; it makes the stored event eligible for the local worker again.

## Signature verification

Local development does not require a signature by default. When
`PROCORE_INTAKE_REQUIRE_WEBHOOK_SIGNATURE=true`, the receiver fails closed unless an opaque webhook
secret reference resolves and a valid HMAC SHA-256 signature is present. Secrets use the same
environment-backed reference mapping as DMSA credentials and are never stored in the database.
Comparison is constant-time and errors never echo signatures or secret values.

The default signature and event-ID header names are configurable placeholders. The generic verifier
also accepts an optional `sha256=` prefix. Production teams must verify Procore's current webhook
signing method, canonical body requirements, header names, and delivery semantics against current
official documentation before enabling signature-required production traffic.

## Event processing

`POST /event-queue/run-once` and `scripts/run_event_queue_once.py` default to dry-run. The worker
selects available queued events, recovers stale locks, and maps company/project/resource metadata
to an enabled mock `SyncProfile`. A matching event invokes the existing profile run-once service;
dry-run writes no intake records and changes no event, profile, or watermark state.

Persisted processing uses both event locks and the A3 profile lock. Success marks the event
processed. Missing profiles and unknown resources are skipped with sanitized reasons. Failures
increment a counter, discard raw exception text, and stop after the configured maximum attempts.
There is no Celery, Redis, SQS, Kafka, background daemon, or external queue in Phase A4.

The worker uses only the fixture/mock sync path. Live Procore calls remain disabled by default and
are not implemented for event processing. Webhook handling never writes to Procore.
