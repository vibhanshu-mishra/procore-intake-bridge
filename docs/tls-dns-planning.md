# TLS and DNS planning

TLS and DNS plans are reference-only. G5 does not query DNS, contact an ACME or certificate
provider, issue or renew a certificate, generate a private key or CSR, create a challenge, or
change a DNS record.

Private review should cover domain ownership, record intent, propagation and rollback, certificate
issuance and renewal ownership, termination location, protocol policy, key custody, expiry
monitoring, and failure response. No domain, endpoint URL, record, certificate content, key,
challenge, account ID, or provider log belongs in this repository.

The presence of `DNS_PLAN_REF_PLACEHOLDER` and `TLS_PLAN_REF_PLACEHOLDER` indicates only that a
private plan is expected; it does not validate DNS or TLS.
