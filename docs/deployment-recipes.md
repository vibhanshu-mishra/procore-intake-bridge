# Deployment recipes

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
