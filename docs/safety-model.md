# Safety model

Procore Intake Bridge is read-only. It performs no Procore writes: no creates, updates, deletes,
approvals, submissions, closures, uploads, or write-back routes.

Phase A2 preserves these constraints:

- Local JSON fixtures are the only sync source.
- Polling reads Procore-shaped fixture data and never writes to Procore.
- Polling dry-runs write no intake records and advance no watermarks.
- Polling tests use fixtures and mocks only.
- Webhooks never write to Procore, and the receiver does not call Procore.
- The event worker uses the existing fixture/mock read-only sync path.
- Webhook signature secrets are referenced through the secret provider, never stored.
- Webhook tests use fake payloads and fake local HMAC secrets only.
- Live Procore access is opt-in and disabled by default.
- Live-mode adapter calls fail closed with `LiveProcoreDisabledError`.
- Mock health checks are deterministic and do not resolve credentials.
- Live-gated health checks run only after the explicit environment flag is true.
- Connection APIs accept an opaque secret reference, never a plaintext client secret.
- DMSA secrets and resolved client IDs are never stored in plaintext.
- Fixtures contain synthetic identifiers and data only.
- Tests need no credentials and make no live Procore requests.
- There are no external AI/model calls and no MCP execution.
- There are no GitHub API calls, commits, pushes, or automatic pull requests.
- `.env`, databases, tokens, downloads, and logs are gitignored.

Before production, add tenant authorization, an audited secret-manager integration, encryption and
key rotation, database migrations, data retention controls, request logging with redaction,
rate/backoff policy, and verified DMSA permission checks. Any live mode must preserve project
allowlists and expose read operations only.
