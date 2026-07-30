# Permission boundary checklist

Use `make permission-boundary-checklist` for the generated offline checklist.

- [ ] Intentionally public routes remain limited to health/readiness status.
- [ ] Admin, dashboard, review, and deployment guard patterns remain present.
- [ ] H4 lifecycle POST routes remain local-only and admin-protected.
- [ ] Webhook ingress retains signature verification.
- [ ] Export packs remain CLI-only with no public download route.
- [ ] Attachment review remains metadata-only with no file-serving route.
- [ ] Live-capable commands remain separately gated and outside quality.
- [ ] Generated/private output remains ignored.
- [ ] Environment-specific authorization and permission review happens privately.

This checklist performs no live permission check and grants no approval or certification. It
does not add an authentication provider, SSO, OAuth, login, user account, RBAC, session, or
cookie implementation.
