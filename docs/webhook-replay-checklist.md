# Webhook replay checklist

- [ ] Require private authorization for any local replay operation.
- [ ] Define timestamp, nonce, or freshness-window expectations.
- [ ] Preserve event fingerprinting and database-backed deduplication.
- [ ] Review retry limits, backoff, queue capacity, locks, and retention privately.
- [ ] Preserve redacted errors and avoid submitted header/signature logging.
- [ ] Use fake fixtures only for public validation.
- [ ] Never replay against a live endpoint or register a remote webhook from this workflow.

This checklist is offline. It makes no Procore or external call and grants no production approval
or security certification.
