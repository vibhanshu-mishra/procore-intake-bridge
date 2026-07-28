# Polling worker

A `SyncProfile` is one project-level polling plan owned by a DMSA connection. It records the
allowlisted project ID, enabled sources (RFIs and/or Submittals), mock/live mode, polling interval,
watermark, next run, retry metadata, and lock state. Creating a profile validates only local
connection configuration; it does not contact Procore.

## Run-once operation

Phase A3 has no daemon, cron configuration, Celery, Redis, or external queue. The worker is invoked
through `POST /polling/run-once` or `python scripts/run_poll_once.py`. Both default to dry-run.
This makes planning inspectable before local state changes. A later hosted phase can call the same
service from a scheduler.

The worker finds enabled profiles whose `next_run_at` is absent or due. For each profile it plans
the source filters and `updated_after`, runs the fixture intake service, and returns a per-profile
result. `run-once` persists normalized fixture records and sync state. Dry-run reads fixtures and
returns the plan but writes no intake records, attempts, locks, next-run timestamps, or watermarks.

## Watermarks

`last_watermark_at` becomes the next run's `updated_after`. A first run uses the run time minus
`PROCORE_INTAKE_MAX_SYNC_LOOKBACK_DAYS`, which defaults to 30 days. A successful run advances the
watermark to its deterministic run-start time. A dry-run or failed run never advances it, avoiding
silent gaps after incomplete intake.

## Locking and retry state

Before a persisted run, the worker conditionally writes `locked_at` and `lock_owner`. Another
worker cannot acquire an active lock and receives a conflict/skipped result. Locks older than
`PROCORE_INTAKE_SYNC_LOCK_TIMEOUT_MINUTES` are stale and can be recovered. Locks are released after
success or failure.

Each attempt schedules `next_run_at`. Success sets `last_successful_sync_at`, resets
`consecutive_failure_count`, and clears the prior error. Failure increments the count and stores
only an error class code plus a generic sanitized message. Raw exception text is intentionally
discarded so credentials, tokens, headers, and private payload details cannot enter sync state.

## Safety and live mode

Polling reads fixture data by default and never writes to Procore. Live mode remains disabled by
default. When requested while disabled, it fails closed. Even with the A2 flag enabled, Phase A3
returns an explicit not-implemented result for live polling; only A2's read-only health boundary
is production-shaped. Tests use local fixtures and mocks and require no Procore credentials.
