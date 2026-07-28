# Public launch checklist

## Repository truth and safety

- [ ] Run `make quality`, the public-safety audit, and the route read-only audit.
- [ ] Confirm no secrets, tokens, App Version Keys, private identifiers, URLs, logs, or outputs
      are committed.
- [ ] Confirm tests make no live Procore calls and require no credentials.
- [ ] Review README claims against current behavior, including the independent-project disclaimer.
- [ ] Confirm fixtures/examples use synthetic placeholders and contain no private data.
- [ ] Confirm generated databases, `.env`, storage, downloads, packet/sync outputs, and screenshots
      are untracked and ignored.
- [ ] Review OpenAPI routes for Procore write-back semantics; admin routes must remain GET-only.
- [ ] Keep the local admin warning visible and do not represent its token as production auth.
- [ ] Review all production-readiness blockers; do not imply readiness from documentation polish.
- [ ] Confirm LICENSE, CONTRIBUTING, SUPPORT, SECURITY, and CODE_OF_CONDUCT are present.
- [ ] Run the fixture-only demo locally from a clean database.

## Initial community work

Possible first issues: improve fixture coverage, add documentation link checking, expand
readiness-check explanations, test migration review procedures, and review accessibility of the
local admin templates. These are ideas, not promised roadmap commitments.
