# Safety model

Procore Intake Bridge is read-only. It performs no Procore writes: no creates, updates, deletes,
approvals, submissions, closures, uploads, or write-back routes.

Phase A1 adds stronger constraints:

- Local JSON fixtures are the only sync source.
- Live-mode adapter calls fail closed with `LiveProcoreDisabled`.
- Health checks are deterministic mocks and do not resolve tokens.
- Connection APIs accept an opaque secret reference, never a plaintext client secret.
- Fixtures contain synthetic identifiers and data only.
- Tests need no credentials and make no live Procore requests.
- There are no external AI/model calls and no MCP execution.
- There are no GitHub API calls, commits, pushes, or automatic pull requests.
- `.env`, databases, tokens, downloads, and logs are gitignored.

Before production, add tenant authorization, an audited secret-manager integration, encryption and
key rotation, database migrations, data retention controls, request logging with redaction,
rate/backoff policy, and verified DMSA permission checks. Any live mode must preserve project
allowlists and expose read operations only.
