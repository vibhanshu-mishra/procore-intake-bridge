# Security Review Checklist

- [ ] Run the offline I5 review and complete provider permissions, resource policies, database roles, and operational evidence review privately.

- [ ] Review the I4 classifications, retention boundaries, redaction boundaries, generated-output ignores, and remaining private legal/security decisions.

- [ ] Review all public trust boundaries and threat categories.
- [ ] Confirm live operations remain separate and manually gated.
- [ ] Confirm secrets, storage, PostgreSQL, and hosted values remain private.
- [ ] Confirm dashboards and review projections exclude raw/private content.
- [ ] Confirm generated outputs are ignored.
- [ ] Record environment-specific findings only in a private workspace.
- [ ] Preserve the absence of certification and production/Pilot authorization claims.

This checklist is offline and calls no scanner, Procore API, external service, or database.

The I2 [permission boundary checklist](permission-boundary-checklist.md) adds route and command
guard review without a live permission check.

The I3 [webhook replay checklist](webhook-replay-checklist.md) records freshness, deduplication,
replay authorization, redaction, and fake-fixture follow-up.
