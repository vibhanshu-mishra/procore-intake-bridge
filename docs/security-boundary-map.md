# Security Boundary Map

I7 adds the [audit-log boundary map](audit-log-boundary-map.md).

I6 adds [dependency](dependency-boundary-map.md) and [package surface](package-surface-map.md) boundaries.

I5 adds dedicated [secret](secret-boundary-map.md), [storage](storage-boundary-map.md), and [database](database-boundary-map.md) maps.

The [I4 retention map](data-retention-map.md) and [redaction map](redaction-boundary-map.md) document public/private data handling without reading private contents.

The I1 boundary map lists public runtime, local data, administrative, provider, external API,
hosted preparation, private review, and generated-output trust boundaries. Run
`make security-boundary-map` for the sanitized offline projection.

No URL, credential, private path, infrastructure identifier, report content, or live result is
included. The map is review input only, not certification or production authorization.

See the I2 [auth boundary map](auth-boundary-map.md) for the route-class, protection-type, and
method-risk projection.

See the I3 [webhook signature boundary](webhook-signature-boundary.md) for exact-request-byte,
digest-comparison, secret, queue, and replay expectations.

I8 summarizes these boundaries with I1–I7, Demo Mode, Sandbox/Pilot, route, generated-output,
final-readiness, and release boundaries. The [I8 review](final-security-readiness-review.md) is an
offline maintainer aid, not a live scanner, approval, legal determination, compliance claim, or
security certification; private environment review remains required.
