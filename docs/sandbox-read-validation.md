# Real Sandbox read validation

Phase F2 adds a separately gated, bounded read-only validation path for authorized Procore
Sandbox access to RFIs and Submittals. It is never automatic.

## Offline preparation

These commands resolve no credentials, read no private files or database rows, and make no
Procore or external calls:

```bash
make sandbox-read-plan
make sandbox-read-preflight
make sandbox-read-evidence-template
```

`make prepare-sandbox` remains offline and does not invoke read validation. The live command is
never part of quality, doctor, start, walkthroughs, release checks, docs checks, or default
commands; those workflows run only the three offline F2 helpers.

## Separately authorized live command

`make sandbox-read-validation` is the only F2 command that may attempt live calls. Do not run it
as a default walkthrough step. Before it constructs a client or resolves credentials, all of
these private gates must pass:

- `PROCORE_INTAKE_SANDBOX_READ_VALIDATION_ENABLED=true`
- `PROCORE_INTAKE_SANDBOX_READ_VALIDATION_CONFIRMATION` exactly equals
  `I understand this will make read-only Procore sandbox API calls`
- the existing live-mode gate is enabled and the Procore target is Sandbox
- a private DMSA connection has both credential references
- company and project scope match the connection and project allowlist
- project, item, page, and timeout values remain within hard caps
- raw storage and attachment inclusion remain disabled

The command checks bounded RFI and Submittal lists, bounded pagination, optional detail reads for
one safe sample, and a safe updated-since/filtering posture where supported. An empty result is
valid and informative. Permission denied, not found, and generic failures are categorized without
printing raw API errors.

## Hard safety boundary

F2 validates reads only. It does not write to Procore, register webhooks, download attachments by default,
connect to an external database, store raw payloads, or expose raw company, project,
RFI, or Submittal identifiers. Reports omit subjects, titles, descriptions, vendors, people,
contacts, URLs, attachment filenames, secrets, and absolute paths.

Sanitized reports contain counts, statuses, and one-way hashes only. Even sanitized live reports
stay private and ignored. Record only a private evidence reference using
[Sandbox read evidence](sandbox-read-evidence.md). A passing result is not production approval,
pilot approval, or a guarantee of complete permissions.
