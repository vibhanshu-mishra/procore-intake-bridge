# Sandbox mode

Sandbox mode is for a user-owned Procore sandbox. Store private credentials and DMSA secret
references only in ignored `.env` or other approved private configuration. Configure an allowlisted
company/project scope without copying identifiers into reports or GitHub.

Run `make sandbox-check` to explain missing prerequisites. It makes no Procore call and does not
resolve secret values. The existing smoke harness remains separate, manual, read-only, explicitly
confirmed, and gated; review its plan before any authorized run. A ready sandbox check is not
production approval.
