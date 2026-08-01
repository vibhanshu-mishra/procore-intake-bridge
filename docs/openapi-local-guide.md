# Local OpenAPI Guide

FastAPI exposes its OpenAPI UI only while the application is running locally. Complete the local
installer steps, start the local app, and open the `/docs` path on the loopback address printed by
the local server. Stop the server when finished.

This is a local developer convenience. Phase J3 does not call the API, contact Procore, publish an
OpenAPI document, or use an external OpenAPI generator, validator, scanner, registry, or hosted
viewer. Never paste private schemas, tokens, payloads, URLs, reports, or customer data into an
external tool.

Use the UI to inspect route methods, summaries, and schemas. Keep these boundaries in view:

- Health/readiness status is deliberately limited and public.
- Admin, deployment/readiness, dashboard, and review surfaces are protected.
- Lifecycle POST operations mutate local state only.
- Webhook POST operations require the signature boundary.
- Attachment routes are metadata-only.
- Export packs are local artifacts; there is no public download route.
- No route writes back to Procore or serves local/cloud attachment files.

OpenAPI visibility does not authorize executing a route. It does not constitute production,
Pilot, release, deployment, security, compliance, certification, or Procore approval. Use fake
Demo Mode data only and follow each route's documented protection and manual-gate requirements.
