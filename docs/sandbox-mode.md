# Sandbox mode

Sandbox may use optional cloud storage, but local remains recommended first. Cloud providers and
network operations are disabled by default; preparation and doctor commands never contact them.

Sandbox may use an optional cloud secret provider, but `env` or `file` is recommended first.
Cloud providers are disabled and network-blocked by default; preparation and doctor commands do
not contact them.

Sandbox Mode is private/operator-controlled. It uses private credentials through DMSA secret refs
and a private allowed scope; values and real identifiers stay outside Git. What to run next:
finish Demo Mode, then run `make prepare-sandbox`. This never runs live smoke.

Follow the [Sandbox walkthrough](walkthrough-sandbox.md) for private inputs, safe checks, and the
boundary around the separately gated live smoke path.

`make prepare-sandbox` and `make sandbox-smoke-preflight` are offline. The real smoke command is
manual, gated, read-only, makes no Procore writes, registers no webhooks, and downloads no
attachments by default. See [Sandbox smoke UX](sandbox-smoke-ux.md).

Use the [D5 sandbox onboarding checklist](sandbox-onboarding.md). Readiness checks do not run the
manually gated smoke harness or make automatic live Procore calls.

Sandbox mode is for a user-owned Procore sandbox. Store private credentials and DMSA secret
references only in ignored `.env` or other approved private configuration. Configure an allowlisted
company/project scope without copying identifiers into reports or GitHub.

Run `make prepare-sandbox` to explain missing prerequisites. It makes no Procore call and does not
resolve secret values. The existing smoke harness remains separate, manual, read-only, explicitly
confirmed, and gated; review its plan before any authorized run. A ready sandbox check is not
production approval.

Initialize the C5 sandbox workspace with
`python scripts/init_private_workspace.py --mode sandbox`. It provides ignored placeholder files
for DMSA refs, allowed scope, permissions, webhook review, and diagnostics. Never commit the
privately completed files.

For DMSA credentials, choose `env` for the simplest private sandbox setup or `file` with safe
relative refs under the ignored workspace. Run `make secret-provider-check`; it reports only
masked ref presence and never invokes Procore.

SQLite is acceptable for local Sandbox simulation. A hosted Sandbox should use PostgreSQL through
a private `DATABASE_URL` secret reference. `make database-check` reports posture without resolving
the reference or connecting.

Local Sandbox needs no hosted recipe. Before hosting Sandbox, validate a D4 recipe and review HTTPS
and public ingress when webhooks are planned. The repository does not provision the environment.

For F2, run the offline `make sandbox-read-plan`, `make sandbox-read-preflight`, and
`make sandbox-read-evidence-template` commands. The separate live validation is manual and checks
bounded RFI/Submittal reads only; see [Sandbox read validation](sandbox-read-validation.md).

F3 begins only after private human review. It links opaque refs without reading reports; see
[Sandbox evidence linkage](sandbox-evidence-linkage.md).
