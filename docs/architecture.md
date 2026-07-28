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
attachment metadata. A source/project/item uniqueness constraint supports idempotent re-syncs.
