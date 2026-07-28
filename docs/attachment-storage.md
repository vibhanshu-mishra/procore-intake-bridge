# Attachment storage

Phase A5 introduces an attachment manifest and a local-filesystem storage abstraction for
attachments visible through RFIs and Submittals. It does not add real Procore downloads, file
serving, cloud object storage, presigned URLs, or production file infrastructure.
There are no real Procore downloads in tests or in the A5 runtime.

## Manifests and URL protection

Each `AttachmentObject` records the owning intake/sync context, synthetic Procore identifiers,
sanitized filename, content metadata, relative storage key, checksum, and download state. Intake
sync creates these manifest rows in `planned` state but writes no file.

Signed source URLs are never stored or returned. When fixture metadata contains a URL, the
manifest stores only `source_url_present=true` and a deterministic SHA-256 hash. URL fields are
also redacted from the normalized raw payload stored with the intake record. Logs and API responses
contain neither raw URLs nor absolute storage-root paths.

## Filename and path safety

Filenames are reduced to a basename, control characters are removed, spaces become underscores,
unsafe characters are replaced, empty names receive `attachment.bin`, and long names are truncated
while preserving a short extension. Project, source, and item path components accept only a small
safe character set.

Storage keys follow:

```text
connection-{id}/project-{project_id}/{source_type}-{item_id}/{safe_filename}
```

The local backend rejects absolute keys, `..` traversal, and resolved paths outside its configured
root. Files are not overwritten unless `PROCORE_INTAKE_ATTACHMENT_ALLOW_OVERWRITE=true`.

## Fixture downloads and states

- `planned`: metadata and storage destination exist; no bytes were written.
- `downloaded`: the explicit fixture operation wrote deterministic fake bytes and a checksum.
- `skipped`: policy chose not to download.
- `failed`: a local fixture write failed; only a sanitized reason is stored.

`POST /attachments/{id}/fixture-download` is local/testing-only. It never follows the source URL
and never calls Procore. Tests write only small deterministic fake files under temporary roots.
There is no upload or delete endpoint and no public file-serving endpoint.

## Integration

RFI/Submittal dry-run sync returns storage plans but persists no attachment rows. A normal fixture
sync creates manifests in the same local transaction as intake state. The webhook receiver never
creates files or manifests directly; later event-queue processing invokes `SyncProfile`, which
invokes intake sync and therefore creates the same manifests. Polling follows that same path.

Future production phases may add a separately reviewed encrypted object-storage backend, retention
policy, malware scanning, tenant authorization, and controlled download delivery. A5 intentionally
has no S3, Azure Blob, Google Cloud Storage, or presigned URL implementation.
