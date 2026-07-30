# Final public repository readiness

Phase H1 is an offline maintainer-review aid that consolidates the public repository’s onboarding,
documentation, safety, examples, fixtures, optional dependencies, live-command separation, and
handoff posture.

```bash
make final-readiness
make final-readiness-checklist
make public-handoff-summary
make final-readiness-artifact-check
```

Final readiness is not release approval, is not production approval, and is not pilot approval.
No live operation or external call occurs. The audit does not deploy, publish, tag, package, call
Procore, connect to databases, or contact cloud, DNS, TLS, storage, or secret services.

Private values and real reports stay outside Git. Before a real pilot, authorized people must
privately configure scope and credentials, review evidence and expiry, verify provider and
database operations, complete deployment and rollback planning, and make separate approval and
launch decisions.

## Maintainer sequence

1. Run `make quality`.
2. Run `make safety-check`.
3. Run `make docs-site-check`.
4. Run `make release-readiness`.
5. Run `make final-readiness`.
6. Review warnings and known limitations before deciding the next private step.

## Security threat model

Phase I1 adds `make security-threat-model`, `make security-boundary-map`, and
`make security-review-checklist` to the offline maintainer sequence. These commands document
trust boundaries and public controls; they do not scan a live system, certify security, approve
production, or replace a private security review.
