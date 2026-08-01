# API Route Reference

This Phase J3 reference covers all 81 routes currently reported by the local read-only route audit.
It is generated from local FastAPI metadata; it performs no live call and adds no route.

## Route-class reference

| Route class | Purpose | Protection and method boundary |
| --- | --- | --- |
| `public_health` | Minimal health status | Intentionally public, safe GET |
| `public_readiness` | Minimal readiness and safety status | Intentionally public, safe GET |
| `admin_dashboard` | Existing administrator views | Admin token required, safe GET |
| `deployment_readiness` | Existing deployment/readiness summaries | Admin token required, safe GET |
| `product_dashboard` | Local product cockpit | Admin token required, safe GET |
| `review_workspace` | Local intake review pages | Admin token required, safe GET |
| `review_api` | Sanitized review metadata | Admin token required, safe GET |
| `lifecycle_local_mutation` | H4 local status changes | Admin token required, local-only POST |
| `webhook_signature_boundary` | Webhook receipt | Signature required, bounded POST |
| `intake_sync_demo` | Demo/intake/sync fixtures and planning | Local/demo/manual gate as classified |
| `attachment_metadata` | Attachment metadata and manifest views | Protected metadata only; no file serving |
| `onboarding_packet` | Local onboarding guidance | Local/private-workspace boundary |
| `sandbox_gated` | Explicit Sandbox operations | Disabled by default and manually gated |
| `diagnostics_support` | Sanitized operational summaries | Admin token or local-only boundary |
| `static_or_docs` | Framework/local documentation surface | Local development use |

Each concrete row printed by `make api-route-reference` includes the method, normalized path,
purpose, class, protection type, and method risk. An `unknown` class, protection, or method risk is
not an acceptable completed review result.

## Mutation and content boundaries

The lifecycle POST routes change local lifecycle state only. They are not Procore write-back routes
and do not approve a workflow action outside this application. Webhook POST routes require the
existing signature boundary; documentation never replays a webhook or publishes payloads, headers,
or signatures.

There is no public export download route, attachment file-serving route, Procore mutation route,
data-deletion route, or endpoint that turns private/generated artifacts into API resources. Export
summaries remain local files outside Git, and attachment review remains metadata-only.

This route inventory is local documentation, not evidence of production, Pilot, release, or
deployment approval. See [API documentation review](api-docs-review.md) for the fail-closed checks.
