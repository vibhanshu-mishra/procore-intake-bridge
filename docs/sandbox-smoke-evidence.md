# Sandbox smoke evidence reference

A completed authorized smoke run may later be represented by a private reference. The public
repository stores neither the smoke report nor its contents.

Print the placeholder structure:

```bash
make sandbox-smoke-evidence-template
```

It contains placeholders for the smoke ref, run label, company/project scope refs, result status,
reviewer, and expiry. Copy the structure only into the approved private workspace or evidence
system, then replace placeholders privately.

The reference feeds:

- C1 private evidence manifest
- C2 private review and expiry
- B9 pilot readiness gate
- C3 private approval packet
- D5 sandbox-to-pilot preflight

Evidence content, real IDs, reviewer identity, timestamps, report paths, payloads, URLs, and
credentials stay outside Git. A reference documents that private evidence exists; it does not
prove approval or production readiness.

Before using a ref, privately verify the run was authorized, sandbox-only, read-only, bounded,
sanitized, current, scoped correctly, and reviewed by an authorized human.
