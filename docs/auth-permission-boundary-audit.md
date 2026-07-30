# Auth / Permission Boundary Audit

Phase I2 adds an offline, public-safe audit of existing route and command boundaries. It reads
the local FastAPI route table, Makefile, scripts, documentation, route-audit rules, and existing
admin/signature guard patterns. It makes no live permission check, Procore call, external call,
database write, scanner request, or deployment.

I2 adds no authentication provider or login system. It does not implement SSO, OAuth, user
accounts, RBAC, sessions, cookies, identity-provider integration, or permission synchronization.

```bash
make auth-boundary-audit
make auth-boundary-map
make permission-boundary-checklist
```

The intentionally public surface is limited to health, readiness, and safety status routes.
Admin, product-dashboard, review-workspace, review API, and deployment surfaces use the existing
admin guard pattern. The two H4 lifecycle POST routes remain admin-protected local-only
mutations. Webhook ingress is classified at the existing signature-verification boundary.

Legacy fixture and planning routes are local-only. Export packs remain CLI/local artifacts with
no public download route. Attachment review remains metadata-only with no file-serving route.
Live-capable Sandbox and PostgreSQL commands remain separate, disabled by default, and manually
gated; provider, hosted-planning, Demo, and threat-model commands remain offline checks.

Passing I2 is not production approval, security certification, compliance certification, launch
approval, Pilot approval, or proof that a deployment’s private authorization policy is correct.
Authorized reviewers must still assess real identities, secrets, environment configuration,
network exposure, runtime enforcement, provider permissions, evidence, and risk privately.

I3 reviews the webhook-signature and local replay classifications in more detail without changing
their runtime behavior. See the [webhook hardening review](webhook-replay-signature-hardening.md).
