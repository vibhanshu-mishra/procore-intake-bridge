# Auth boundary map

The I2 map assigns every local FastAPI route to a public, protected, local-only, webhook, or
unknown class and records the expected protection and method risk.

- Public health/readiness routes are intentionally limited status surfaces.
- Admin, deployment, dashboard, and review routes retain existing guard dependencies.
- H4 lifecycle POST routes are the only local-only mutations within the review surface.
- Procore webhook receiver routes require the signature-verification boundary.
- Other foundation fixture/planning routes remain local-only.
- Export downloads, attachment file serving, Procore write-back, destructive public methods,
  and unknown mutations are prohibited.

The map inspects code structure only. It performs no live permission check and adds no SSO,
OAuth, login, RBAC, account, cookie, or session capability. See the
[full I2 audit](auth-permission-boundary-audit.md).

I3 records the signature receiver and replay-route gaps in the
[webhook hardening review](webhook-replay-signature-hardening.md).
