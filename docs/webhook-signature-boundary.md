# Webhook signature boundary

The I4 secret and raw-payload redaction boundaries apply to this signature boundary; submitted values remain excluded.

The receiver’s configured verification path computes HMAC-SHA256 over the exact request bytes and
uses constant-time comparison. Missing configuration, missing submitted signature, unavailable
secret reference, and mismatch failures use bounded messages that omit supplied values.

Runtime enforcement remains private configuration. This offline review does not resolve the
shared secret, inspect live headers or payloads, call an endpoint, register a webhook, or prove
production security. See the [I3 review](webhook-replay-signature-hardening.md).
