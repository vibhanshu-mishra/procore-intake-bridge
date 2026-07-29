# Pilot mode

Pilot mode assembles the repository's customer-profile, diagnostics, readiness, evidence review,
expiry, approval, launch-condition, and rollback tooling. Run `make pilot-check` against the
committed fake examples and `make doctor` for a concise posture summary.

Real evidence, identities, signoffs, decisions, customer identifiers, and credentials belong in an
authorized ignored private workspace outside GitHub. The public repository never supplies or
records a real approval. Pilot mode remains `needs_configuration` until operators complete that
private work; its validators do not constitute production approval or security certification.
