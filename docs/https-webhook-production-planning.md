# HTTPS webhook production planning

Phase G5 provides public-safe planning for a future privately hosted Sandbox/Pilot webhook
receiver. It performs no DNS, TLS, ACME, public URL, cloud, deployment, Procore, or webhook
registration call and generates no certificate, key, CSR, or challenge.

The expected `/webhooks/procore` path is the local application route expectation. Its presence in
a report is not proof that a public endpoint exists, is reachable, uses HTTPS, or has been
registered. Real HTTPS and public ingress are required for future webhooks and must be configured
and reviewed privately.

Use:

```bash
make https-webhook-template
make https-webhook-check
make https-webhook-matrix
make webhook-disable-plan
make https-webhook-artifact-check
```

The first four commands are non-writing and offline. The artifact check writes only to an
automatically removed temporary directory. Real domains, URLs, DNS records, certificates, proxy
configuration, signature secrets, provider identifiers, evidence, and registration details stay
outside Git.

Signature readiness depends on a private webhook-secret reference; no value is resolved.
Event-queue, replay, monitoring, disable, and rollback plans require private review before Pilot
use. Passing this planning check is neither production setup completion nor Pilot approval.
