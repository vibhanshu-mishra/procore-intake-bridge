# Local admin dashboard

Phase A7 provides a small, server-rendered operations view of the existing local database. Open
`GET /admin` for the overview. Connections, sync profiles, sync runs, intake records, attachment
manifests, webhook events, onboarding packets, and safety state have individual pages. Equivalent
read-only JSON is available beneath `/admin/api`.

## Safety boundary

Every admin route is GET-only. Dashboard services query local tables and never call Procore,
trigger sync, process an event, download an attachment, export a packet, or mutate database state.
Templates use inline CSS and no JavaScript, external asset, CDN, analytics, or browser-side API
request.

Admin responses use purpose-built summary schemas. They mask company, project, item, event, and
record identifiers. They do not include connection names, client ID references, secret names,
raw intake/webhook payloads, webhook signatures, source URLs or hashes, original filenames,
storage keys or paths, generated onboarding content, recipient/requester details, or app key
references. This is defense in depth, not a claim that the dashboard is safe for public exposure.

## Configuration

```dotenv
PROCORE_INTAKE_ADMIN_DASHBOARD_ENABLED=true
PROCORE_INTAKE_ADMIN_REQUIRE_TOKEN=false
PROCORE_INTAKE_ADMIN_TOKEN_SECRET_NAME=
PROCORE_INTAKE_ADMIN_PAGE_SIZE=25
```

When the dashboard is disabled, all admin routes return 404. When token protection is enabled, set
`PROCORE_INTAKE_ADMIN_TOKEN_SECRET_NAME` to an environment-secret reference and send the resolved
value in `X-Procore-Intake-Admin-Token`. Missing configuration fails closed. Token comparison is
constant-time, and tokens are never rendered or returned in errors.

The token-free default is convenient only on a developer machine bound to a trusted local
interface. Before any production exposure, require real application/platform authentication and
authorization, TLS, network restrictions or a private reverse proxy, audited access, rate limits,
managed secrets, and appropriate data-retention controls. The optional header token alone is not
production-grade access control; by itself it is not production-grade authentication.

## Routes

- HTML: `/admin`, `/admin/connections`, `/admin/sync-profiles`, `/admin/sync-runs`,
  `/admin/intake-records`, `/admin/attachments`, `/admin/webhook-events`,
  `/admin/onboarding-packets`, and `/admin/safety`
- JSON: `/admin/api/overview`, `/admin/api/connections`, `/admin/api/sync-profiles`,
  `/admin/api/sync-runs`, `/admin/api/intake-records`, `/admin/api/attachments`,
  `/admin/api/webhook-events`, `/admin/api/onboarding-packets`, and `/admin/api/safety`

List APIs accept `limit` or `page_size`. Results are capped at 100; the configured default is 25.
