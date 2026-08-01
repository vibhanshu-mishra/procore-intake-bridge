# Product Dashboard

J3 classifies the existing dashboard routes as protected product/admin surfaces in the all-81-route
reference. The reference makes no live call and adds no route. Dashboard documentation does not
create an export download, file-serving endpoint, Procore write-back, or operational approval.

J2 can populate dashboard-friendly counts with deterministic fake, demo-marked records in local
SQLite. Run `make demo-seed-plan`, `make demo-seed`, and `make demo-data-check`; no Procore call,
cloud service, external database, or customer data is involved. `make try-demo` is
non-destructive. The confirmed `make demo-reset` affects only demo-marked local records and never
private workspace, Sandbox, Pilot, Hosted, cloud, or customer data. It grants no approval.

For Phase J1 local setup, follow the [local installer guide](local-installer-guide.md) and run
`make start` before `make try-demo`. Demo requires no Procore credentials, other secrets, cloud
services, or external database. Sandbox, Pilot, and Hosted remain separate and gated; setup
performs no package build, release, or deployment and grants no operational approval.

Phase H8 polishes the existing local admin and review UI into a product cockpit at
`GET /dashboard`. It adds visibility and navigation across existing capabilities; it does not
add a product workflow.

## Safe local use

The dashboard is local, read-oriented, and backed only by the local database. It makes no
Procore calls or writes, external calls, lifecycle changes, export artifacts, storage-provider
calls, or attachment file reads. The JSON projection at `GET /dashboard/api/overview` contains
aggregate counts, safe local links, and command guidance only.

Raw payloads, source URLs, signed URLs, private paths, storage keys, original filenames,
attachment contents, and raw source identifiers are excluded. Export guidance shows
`make operator-export-check` and `make operator-export-summary`; the UI provides no export
download or generated-file link.

## Start locally

```bash
make try-demo
make product-dashboard-check
make product-dashboard-overview
```

Open `/dashboard` after starting the local app. Demo Mode may use fake local fixture data and
needs no credentials.

Sandbox and Pilot preparation remain private and manually gated. Generated outputs and private
evidence stay outside the public repository. Dashboard readiness is preparation context, not
release, production, or pilot authorization. It is not a compliance determination, customer
report, or external system status.

H9 uses this dashboard as the starting cockpit for the
[Demo Product Walkthrough](demo-product-walkthrough.md).

The I1 threat model treats the dashboard as a protected local trust boundary.

The I2 audit classifies both dashboard GET routes as protected by the existing admin guard. It
adds no login system and confirms the dashboard exposes no export download or file-serving route.
