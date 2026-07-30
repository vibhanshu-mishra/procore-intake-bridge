# HTTPS and webhook ingress

Hosted webhook receivers require privately reviewed HTTPS and public ingress. D4 checklists cover
certificate references, redirect/protocol posture, renewal ownership, ingress restrictions,
signature enforcement, and verification evidence. They issue no certificate, create no DNS record,
open no ingress, and register no webhook.

Certificate and private-key contents must never enter recipe JSON, generated artifacts, reports,
logs, examples, or Git. Use placeholder references such as `TLS_CERT_REF_PLACEHOLDER` and
`WEBHOOK_INGRESS_REF_PLACEHOLDER`.

# Hosted platform note

G4 does not configure public ingress, DNS, TLS, or webhooks. Every hosted profile carries HTTPS
and webhook-ingress placeholders that must be completed and reviewed privately before any manual
deployment.
