# Hosted UI Page Inventory

The Phase J4 inventory classifies existing UI pages and related guidance without running the app,
connecting to a database, or deploying anything.

| Surface | Page classification | Protection and hosted boundary |
| --- | --- | --- |
| Product dashboard | Admin protected | Demo-capable with fake local data; private review before hosting |
| Admin dashboard | Admin protected | Existing admin-token boundary; private review before hosting |
| Intake review workspace | Admin protected | Fake/local Demo data only in public evaluation |
| Triage queue | Admin protected | Local projection over review metadata |
| Lifecycle controls | Admin protected | Local-only mutation; no Procore write-back |
| Attachment review | Metadata only | No attachment contents, file serving, or downloads |
| Export guidance | Command guidance only | Local CLI artifacts; no public download route |
| Setup and Demo walkthrough | Local Demo safe | Depends on fake demo-marked local SQLite data |
| API reference | Local documentation | No live call or external tooling |
| Deployment/security readiness | Private review required | Guidance only; not a hosted approval |

A page labeled `hosted_candidate` is suitable only for later private evaluation. It is not publicly
hostable by default. Unknown pages, unprotected candidates, external assets, downloads, or file
serving block the review.

J4 adds no route, frontend framework/build system, external asset, analytics, or telemetry. It does
not approve production, Pilot, release, or deployment. See [private gates](hosted-ui-private-gates.md).
