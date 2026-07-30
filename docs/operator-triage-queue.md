# Operator Triage Queue

Phase H5 adds a GET-only, read-only projection over the sanitized H3 Intake Review Workspace and
the audited local H4 lifecycle state. It helps an operator sort local records; its deterministic
priority score is a sorting helper only, not risk, approval, compliance, or business advice.

Open `/review/triage`, or inspect the JSON projections at `/review/api/triage` and
`/review/api/triage/summary`. The existing admin guard protects every route. There is no H5 POST
route. H4's two guarded lifecycle POST routes remain the only review mutations.

```bash
make operator-triage-check
make operator-triage-summary
```

Both commands are local, empty-database-safe, and non-writing. They make no Procore or external
call. The queue supports bounded paging; stable priority, received-time, lifecycle, and tool
sorting; and filters for bucket, tool, and lifecycle status.

## Safety boundary

- Raw payloads, source URLs, signed URLs, private paths, attachment contents, and raw source IDs
  are never returned. Source identifiers are masked and/or hashed.
- Attachment signals use manifest metadata only; attachment content is not read.
- H5 does not assign work, add comments, approve anything, determine compliance, notify or
  communicate with anyone, change lifecycle state, or update Procore.
- Demo data is synthetic and fake. Sandbox and Pilot data, credentials, reports, and evidence
  remain private and outside the public repository.
- Unsafe exposure settings fail closed by default.

The queue buckets are local observations such as new, in review, needs follow-up, older
unreviewed, recently received, attachment manifest present, missing source context, unknown
tool, reviewed, and ignored. A record may appear in multiple buckets.

H6 provides a separate [attachment manifest metadata view](attachment-review-manifest-ux.md).
The triage queue links to that context without accessing files or exposing storage details.
