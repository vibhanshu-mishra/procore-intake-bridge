# Webhook disable and rollback planning

A private disable and rollback plan is required before Pilot webhook use. The public checklist
does not change ingress, receiver settings, queue state, secrets, or remote webhook registration.

Privately define:

1. Conditions for disabling ingress and receiver processing.
2. Event-queue pause, retention, replay, and deduplication handling.
3. Secret rotation and incident evidence procedures.
4. The separately approved process for any remote registration change.
5. Rollback triggers, prior-state restoration, health verification, and communications.

Store only `WEBHOOK_DISABLE_PLAN_REF_PLACEHOLDER`,
`WEBHOOK_ROLLBACK_PLAN_REF_PLACEHOLDER`, and `WEBHOOK_EVIDENCE_REF_PLACEHOLDER` in public
examples. Evidence contents remain private. A plan does not prove production setup is complete.
