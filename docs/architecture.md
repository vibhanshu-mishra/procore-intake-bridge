# Architecture

Procore Intake Bridge is a separate hosted backend, not an extension of the SDK.

```mermaid
flowchart LR
    A["GC / Owner private app + DMSA"] -. "future read-only access" .-> B["PyProcore SDK layer"]
    B --> C["Procore Intake Bridge services"]
    C --> D["Connections and project allowlists"]
    C --> E["Sync runs and intake records"]
    C --> F["Attachment manifests"]
    D --> G[("Customer database")]
    E --> G
    F --> G
    H["Local JSON fixtures"] --> C
    I["Run-once Polling Worker"] --> J["Project SyncProfile"]
    J --> C
    J --> G
    K["Webhook Receiver"] --> L[("WebhookEvent table")]
    L --> M["Run-once Event Queue Worker"]
    M --> J
    C --> N[("AttachmentObject manifests")]
    N --> O["Local AttachmentStorage"]
    O -. "fixture bytes only" .-> P[("Ignored local storage root")]
    Q["OnboardingPacket service"] --> R[("OnboardingPacket table")]
    R --> S[("Ignored local Markdown/JSON output")]
    T["Local read-only admin dashboard"] --> G
    U["Startup safety checks"] --> V["Deployment readiness layer"]
    V --> C
    W["Alembic migration foundation"] --> G
    X["Docker local runtime"] --> C
```

PyProcore owns OAuth and token refresh, HTTP requests, pagination, retries, typed response parsing,
and attachment download plumbing. The Bridge owns customer connection profiles, DMSA onboarding
state, permitted-project enforcement, health reporting, polling/webhook strategy, normalization,
sync state, intake records, attachment manifests, and operational logs.

In Phase A2, fixtures to Bridge to SQLite remains the only sync path. The Procore path is limited
to an opt-in, read-only health diagnostic. `build_pyprocore_client_for_connection` raises
`LiveProcoreDisabledError` unless the explicit live flag is true. Credential resolution and the
PyProcore constructor remain centralized in the adapter.

The data model separates DMSA connections, sync-run history, normalized intake records, and
attachment metadata. `SyncProfile` adds project-level schedules, watermarks, locks, and retry
state. The run-once Polling Worker selects due profiles and calls the same intake service; there is
no background daemon or external queue. A source/project/item uniqueness constraint supports
idempotent re-syncs.

The A4 webhook receiver stores events only: it never calls Procore or invokes sync in the request
path. The database-backed Event Queue Worker later locks queued events, maps them to `SyncProfile`,
and triggers the existing fixture/mock intake path. Polling remains the fallback reconciliation
mechanism.

Attachment metadata flows from intake sync into `AttachmentObject` manifests. The local storage
service derives safe relative keys and can write deterministic fixture bytes only when explicitly
requested. No real download occurs by default, and no raw signed URL is stored.

The A6 OnboardingPacket service reads only caller input and local connection/profile metadata. It
renders Markdown/JSON for review and optional local export; it does not call Procore, install an
app, send email, or grant access.

The A7 admin dashboard reads the existing local tables through dedicated summary projections.
Both its HTML and JSON surfaces are GET-only. The projections mask identifiers and omit secrets,
payloads, URLs, generated packet content, and filesystem paths. The dashboard does not invoke the
PyProcore adapter or any write service.

The A8 readiness layer inspects sanitized runtime posture at startup and through read-only
operational routes. Production can fail closed on blockers. Alembic supplies a reviewed migration
foundation, while the Docker assets describe a local runtime only.
