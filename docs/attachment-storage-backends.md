# Attachment storage backends

Phase B5 introduces a production-shaped attachment storage contract while retaining safe local
defaults. It does **not** implement or contact S3, Azure Blob Storage, GCS, R2, MinIO, or another
external service.

## Providers

- `local` writes beneath the configured ignored local root for fixtures and development.
- `test` keeps bytes in memory and is only for automated tests.
- `disabled` refuses reads and writes.
- `external_placeholder` performs no network operation and reports not implemented.

The legacy `ATTACHMENT_STORAGE_BACKEND=local` setting remains compatible. Unknown providers fail
closed. A future adapter must implement the same write, read, existence, description, health, and
sanitized-summary contract and receive separate security and operational review.

## Keys and content

Object keys are deterministic relative identifiers, not URLs or filesystem paths. Validation
rejects empty values, absolute paths, traversal, URL schemes, control characters, and
non-normalized separators. Local resolution verifies that targets remain beneath the configured
root. Content size is limited, checksums use SHA-256, and optional content-type allowlisting can
quarantine unknown types.

No provider exposes absolute local paths, generates presigned URLs, or creates a public
file-serving route. Raw source or signed URLs are never stored; manifests retain only presence and
a one-way hash. Fixture-only downloads remain the default, and B5 downloads no live attachment.

## Operator checks

```bash
python scripts/check_attachment_storage.py
python scripts/check_attachment_manifest_consistency.py
```

The first prints sanitized configuration and health. The second compares downloaded local/test
manifest rows with object existence without reading or printing contents. Add `--strict` for a
nonzero exit on unsafe posture or missing objects. `GET /deployment/storage` exposes the same safe
posture and inherits B4 deployment-route authentication.

Production work still requires a real encrypted object-store adapter, credential delivery,
retention/deletion policy, malware handling, backup/recovery, residency decisions, access logging,
concurrency semantics, and independently reviewed failure recovery.
The B7 customer storage plan records only a provider posture and placeholder bucket reference.
`external_placeholder` remains a production blocker and performs no storage call. Real buckets,
endpoints, credentials, retention, and recovery belong in a separately reviewed private plan.
