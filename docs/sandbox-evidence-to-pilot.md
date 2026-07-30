# Sandbox evidence to Pilot

F3 maps private Sandbox result references without reading the underlying reports:

1. **C1 private evidence manifest:** record opaque smoke/read-validation refs only.
2. **C2 review and expiry:** authorized humans review the private source, then record status,
   expiry, renewal, and limitations privately.
3. **B9 Pilot readiness:** consume reviewed reference posture as one input. Evidence presence
   never makes readiness pass automatically.
4. **C3 Pilot approval packet:** reference the reviewed evidence mapping without copying contents.
   No approval is created.
5. **D5 Sandbox-to-Pilot flow:** reconcile the opaque refs with other private gates while launch
   remains on hold.
6. **Pilot preflight:** checks mapping posture only; it does not read source evidence.

Use `make sandbox-evidence-mapping` to print the placeholder mapping. Source reports, real counts,
IDs, scope, people, URLs, API payloads, errors, screenshots, attachments, and review records stay
in the approved private evidence system outside Git.

Every reference requires human review and remains subject to expiry and renewal. A complete
mapping does not mean a Pilot is approved, secure, deployed, or ready to launch.
## Hosted rehearsal boundary

G6 brings planning and evidence labels into one public-safe map. It reads refs only, performs no
live operation, and requires private human review. Dry-run completion is not launch or pilot
approval.
