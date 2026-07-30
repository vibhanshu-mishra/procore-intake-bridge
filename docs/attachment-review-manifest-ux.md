# Attachment Review and Manifest UX

Phase H6 adds a GET-only, metadata-only view of local attachment manifest rows connected to H3
intake records. It summarizes manifest availability, planned and stored-metadata counts,
skipped/blocked counts, safe content-type categories, known sizes, checksum presence, sanitized
storage status, and source-metadata availability.

Open `/review/attachments`, or inspect `/review/api/attachments` and
`/review/api/attachments/summary`. A record-specific metadata view is available through the
corresponding HTML and JSON detail routes. Every route uses the existing admin guard.

```bash
make attachment-review-check
make attachment-review-summary
```

The commands are local, read-only, and empty-database-safe. They query local database metadata
only. There is no file access, and they make no Procore, storage-provider, or external call.

## Safety boundary

- Attachment contents are unavailable by design.
- No Procore attachment download, file serving, or file opening occurs.
- Source and signed URLs, private paths, storage keys, original live filenames, raw source IDs,
  raw payloads, and checksum values are not returned.
- Attachment IDs are masked and/or hashed; only checksum presence is summarized.
- Metadata review does not approve a document, determine compliance, or change Procore status.
- Demo Mode may use fake fixture metadata. Sandbox and Pilot data remain private and gated.

Future separately scoped phases may add sanitized export summaries. They must not turn this
metadata view into a file-serving surface.

H7 now provides those [sanitized export summaries](operator-export-pack.md). It exports aggregate
manifest metadata only and still performs no file or storage access.
# Product dashboard navigation

H8 reports metadata-only manifest counts and links to attachment review. It exposes no filename,
path, storage key, URL, or content and never opens an attachment file.

H9 evaluates this metadata-only surface without reading or serving a file.
