# API Documentation Review

Phase J3 adds an offline, public-safe reference for all 81 current application routes. The review
inspects the local FastAPI route table and repository documentation only. It makes no live API,
Procore, cloud, or external database call and uses no external OpenAPI tooling.

In short: this is a local-only review with no live API calls and no external OpenAPI tooling.
API documentation is not production approval.

J3 is documentation and inspection, not new product behavior. It adds no product route, public
export download, attachment file-serving endpoint, Procore write-back, deletion endpoint, or live
integration. It does not approve production, Pilot, release, deployment, or hosted operation.

## Review contract

Every route receives a route class, protection type, method risk, and concise purpose. The review
fails closed when a route is undocumented or unknown, or when it detects an unsafe public mutation,
export download, file-serving endpoint, Procore write route, private value, or approval claim.

The documented boundaries are:

- Health, readiness, and safety status are the deliberately limited public surface.
- Admin, deployment/readiness, product-dashboard, review-workspace, and review API routes use the
  existing admin-token boundary.
- H4 lifecycle POST routes are admin-protected local-only mutations.
- Webhook POST routes sit behind the webhook-signature boundary.
- Demo, intake, sync, and fixture-planning routes remain local or explicitly gated.
- Attachment routes expose metadata only; they do not serve attachment contents.
- Export packs remain local CLI artifacts; no export download route exists.

Run the non-writing review commands:

```bash
make api-docs-review
make api-route-reference
make api-usage-examples
make openapi-local-guide
```

`make api-docs-artifact-check` uses temporary output and cleans it. Generated API documentation
belongs in ignored output roots and must contain no real identities, domains, URLs, IDs, secrets,
private paths, logs, payloads, report contents, or approval records.

Continue with the [route reference](api-route-reference.md), [safe examples](api-usage-examples.md),
and [local OpenAPI guide](openapi-local-guide.md).
