# Operator Export Pack

Phase H7 renders local sanitized summaries of the H3–H6 operator views as JSON, Markdown, and
CSV. It covers intake summary and bounded record rows, local lifecycle status and event metadata,
triage buckets, attachment manifest metadata, and a combined operator packet.

```bash
make operator-export-check
make operator-export-summary
make operator-export-artifact-check
```

The check and summary commands are read-only and write nothing. The artifact check writes only to
a temporary `/tmp` directory and removes it automatically. To create ignored local artifacts:

```bash
python scripts/generate_operator_export_pack.py
```

The configured `operator-export-output/` root and all H7 filename patterns are ignored by Git.
Keep generated exports outside version control. Demo Mode may export fake local fixture data;
Sandbox and Pilot exports remain private, operator-controlled, and gated.

## Safety boundary

- There is no public export route, file-serving control, or generated-file link.
- No Procore call/write, external call, database mutation, attachment operation, or storage
  provider call occurs.
- Exports contain no raw payload, source/signed URL, private path, storage key, original filename,
  attachment content, secret, raw source ID, or private report content.
- These summaries are not compliance reports, approvals, customer reports, audit certifications,
  or Procore statuses.
- CSV cells beginning with `=`, `+`, `-`, or `@` are prefixed to neutralize formula execution.
- Output roots are allowlisted and traversal attempts fail closed.

Markdown deliberately identifies the result as a local sanitized metadata summary. It must not be
presented as an official external report.
# Product dashboard guidance

H8 lists export commands only. It adds no generated-file link, public download, file-serving
route, or artifact generation.

H9 uses `make operator-export-check`; the Demo tour itself generates no export artifact.

I1 models export artifacts as an ignored generated-output trust boundary.

I2 verifies the export pack remains command-only and exposes no public download route. Generated
artifacts remain ignored and any real review stays private.
