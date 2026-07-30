# Storage providers

Demo Mode needs no storage setup. Sandbox/Pilot storage is private and operator-controlled.
What to run next: `make storage-provider-check`; it makes no external storage call.

Storage-provider readiness is a Pilot preflight milestone in the
[sandbox-to-pilot flow](sandbox-to-pilot-flow.md).

Phase D2 adds a shared, fail-closed storage facade for sanitized object references. The default
local provider supports bounded text writes, reads, existence checks, deletion, and masked
inventories only inside ignored private roots. It rejects traversal, absolute keys, symlink
escapes, unsafe roots, oversized or binary values, blocked extensions, and overwrite by default.

```bash
make storage-provider-template
make storage-provider-check
make storage-refs-check
make local-storage-provider-check
```

Reports contain provider posture, counts, sizes, statuses, and masked references only. They never
contain object bytes, absolute paths, bucket names, endpoints, credentials, signed URLs, database
URLs, or private output artifacts. There is no public file-serving route.

The `s3`, `azure_blob`, and `gcs` adapters are optional dependency boundaries. Cloud access is
disabled by default and each adapter performs no SDK or network call during construction, health,
readiness, diagnostics, or quality checks. Enabling one still fails closed until private
configuration and permissions are separately implemented and verified.

Private workspace scaffolds include storage documentation, a provider map, a local-root reference,
and object-reference placeholders. Stored objects and real provider configuration remain private.

D3 must separately authorize retention and cleanup rules. D4 must separately authorize malware
and content scanning. D5 must separately authorize encryption, key management, recovery, and
restore testing. D2 does not claim these controls or production readiness.
