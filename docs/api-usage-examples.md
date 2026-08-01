# API Usage Examples

Phase J3 examples are safe Demo Mode illustrations. They use local/fake values only and never show
customer data, credentials, tokens, webhook material, private paths, real domains, IDs, attachment
contents, or private report contents.

## Inspect a deliberately public route

After starting the application locally, use the interactive local OpenAPI page to inspect the
documented health or readiness GET operation. These routes return limited status data and are the
intentionally public surface. Do not substitute a hosted or customer URL.

## Inspect a protected GET route

Dashboard, review-workspace, review API, admin, and deployment/readiness routes require the existing
admin boundary. The public examples do not provide or simulate a real admin token. Use only a fake
local Demo configuration following the repository quickstart.

## Understand bounded POST routes

- H4 lifecycle POST routes are authenticated, local-only mutations. They do not write to Procore.
- Webhook POST routes require the existing signature boundary. Do not use real payloads, headers,
  signatures, endpoints, or replay material.
- Sandbox operations remain disabled by default and require their documented manual gate.

J3 performs no calls while generating this guide. It adds no public export download or file-serving
route. These examples explain existing behavior and grant no production, Pilot, release, deployment,
compliance, certification, or Procore approval.

For a complete locally derived table, run `make api-route-reference`. For an interactive view, use
the [local OpenAPI guide](openapi-local-guide.md).
