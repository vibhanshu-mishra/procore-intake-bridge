# Deployment recipes

Recipes may contain storage reference placeholders only. They must not contain provider resource
names, object keys from live data, signed URLs, credentials, paths, or object contents.

Recipes contain secret references only. Optional cloud SDKs belong in a private runtime extra;
recipes must not contain credentials, provider resource identifiers, or credential paths.

Recipes are placeholder-only planning inputs. They do not deploy, provision, change DNS/TLS, or
register webhooks. What to run next: `make deployment-check`, then
`make deployment-safety-check`.

Recipe validation is one local milestone in [pilot preflight](pilot-preflight.md), not a
deployment action.

D4 provides offline recipe validation and checklist generation, not deployment automation.
Supported targets are local Docker, Docker on a privately managed VPS, managed PaaS, and generic
cloud hosting. Demo needs no deployment recipe; hosted Sandbox and Pilot should review one.

```bash
make deployment-template
make deployment-check
make deployment-safety-check
make https-webhook-checklist
```

Generated artifacts are ignored and contain placeholder references only. Never commit domains,
URLs, secrets, certificates, private keys, infrastructure identifiers, registry values, logs,
database artifacts, or completed private runbooks. The repository contains no Terraform, Pulumi,
Kubernetes, Helm, GitHub Actions, DNS automation, certificate issuance, or cloud provisioning.

G3 runtime planning consumes the private database, maintenance-window, backup, restore-drill, and
rollback references anticipated by D4. It adds no provisioning or deployment automation, and its
offline pool summary is not validation of a hosted database.

G4 adds [hosted deployment templates](hosted-deployment-templates.md) as a more detailed,
placeholder-only extension of D4 recipes. Platform names describe conceptual shapes, not active
provider configuration. No cloud API, registry, DNS, TLS, image, resource, or deployment action is
performed.

G5 adds reference-only HTTPS webhook ingress planning. Deployment recipes carry private DNS, TLS,
reverse-proxy, ingress, signature-secret, queue, disable, and rollback references; public checks
neither validate an endpoint nor register a webhook.
