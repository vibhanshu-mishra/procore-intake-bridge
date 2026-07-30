# Intake Review Workspace

Phase H3 adds a product-facing workspace for reviewing **local intake records only**. In Demo
Mode, those records can come from obviously fake RFI and Submittal fixtures. Open `/review` after
local fixture records have been persisted, or use:

```bash
make review-workspace-summary
make review-workspace-check
```

Both commands are local, non-writing, empty-database safe, and sanitized. They make no Procore,
cloud, storage-provider, or external database call.

## What operators can review

- Local RFI, Submittal, and safely labelled unknown records.
- Masked display numbers and masked/hashed source identifiers.
- Received and updated timestamps with deterministic sorting.
- Attachment manifest counts, checksum counts, URL-hash counts, and content-type summaries.
- Local sync-run context and the count of matching local webhook events.
- Read-only priority signals such as missing manifest, available source context, recent receipt,
  and an operator-review placeholder.

Priority signals are hints, not review statuses, approvals, compliance determinations, or
lifecycle state.

## Safety boundary

All workspace routes are GET-only and use the existing admin access guard. H3 performs no local
database mutation and no Procore write. It does not add lifecycle transitions, assignments,
comments, approvals, outbound notifications, or webhook operations.

Responses do not expose raw Procore payloads, raw source IDs, source URLs, signed URLs, private
paths, storage keys, attachment filenames, or attachment contents. Attachment bytes are neither
downloaded nor read. Unsafe response values fail closed.

Sandbox and Pilot usage remains private, gated, and operator-controlled. Real identifiers and
evidence stay outside Git. H4 may add a separate lifecycle/status flow later; H3 does not.

## Routes

- HTML: `GET /review`, `GET /review/intake`, `GET /review/intake/{record_id}`
- JSON: `GET /review/api/summary`, `GET /review/api/intake`,
  `GET /review/api/intake/{record_id}`

A missing local record returns a sanitized `404`. An empty database points operators to the safe
Demo flow. `make try-demo` remains a dry run; intentionally persisting fake fixture intake uses
the existing `python scripts/run_poll_once.py --execute` flow after a fake local connection and
sync profile have been prepared.
