# Webhook Replay and Signature Hardening Review

Phase I4 classifies the webhook payload and event-fingerprint boundary while continuing to exclude live payloads, headers, signatures, and replay reports from public output.

Phase I3 is an offline webhook security review using local code, documentation, tests, and fake
fixtures. It makes no live webhook replay and no webhook registration. It makes no Procore call
and no external call. It exposes no live payload, header, signature, endpoint, shared secret, or private
report.

```bash
make webhook-security-review
make webhook-signature-boundary
make webhook-replay-checklist
```

Existing controls include HMAC-SHA256 over exact request bytes, constant-time digest comparison,
secret references, redacted failures, sensitive-key filtering, event fingerprint fallback,
event-key deduplication, bounded queue processing, local retry/replay tooling, and synthetic
fixtures. Only the configured event-ID header is retained; the submitted signature header is not
stored.

The review records three honest needs-review boundaries: signature enforcement remains private
runtime configuration, timestamp/nonce/freshness-window enforcement is not implemented, and the
local replay route needs private deployment authorization review. I3 does not change receiver or
fixture behavior.

I3 is not production approval, security certification, compliance certification, launch
approval, or Pilot approval. Private security review must still cover runtime signature
enforcement, replay authorization, freshness policy, ingress limits, queue capacity, retention,
source restrictions, secret rotation, logging, monitoring, and hosted network exposure.
