# Webhook ingress planning

A future webhook receiver needs public HTTPS ingress that forwards only the intended application
path. Privately review allowed hosts, original host/protocol/client-address headers, request-body
integrity, size and timeout limits, rate controls, signature-header forwarding, health behavior,
and queue backpressure.

The public profile stores only reverse-proxy, ingress-platform, allowed-host, public-URL,
signature-secret, event-queue, and monitoring placeholders. No proxy is configured, no tunnel is
opened, no URL is checked, and no webhook is registered.

B6 remains the local synthetic receiver/normalizer/queue verification layer. G4 remains the hosted
template layer. G5 connects their planning references without proving public reachability or
deploying anything.
