# Hosted deployment templates

Phase G4 adds placeholder-only planning profiles for Docker VPS, managed PaaS, Render-style,
Railway-style, Fly.io-style, generic container hosts, AWS ECS-style, Azure Container Apps-style,
and Google Cloud Run-style environments.

These are conceptual starting points for private adaptation, not deployment automation. The
repository makes no cloud, registry, DNS, TLS, database, storage, secret-manager, or Procore calls.
It does not build or push images, create resources, publish artifacts, or deploy services. It
includes no GitHub Actions, Terraform, Pulumi, Kubernetes, or Helm configuration.

Start with the offline commands:

```bash
make hosted-deployment-template
make hosted-deployment-check
make hosted-deployment-matrix
make hosted-deployment-artifact-check
```

The artifact check uses a temporary local directory and removes it. Persistent generation is
allowed only under ignored output roots. Every profile requires placeholders for image, registry,
public URL, allowed hosts, database, admin authentication, DMSA credentials, webhook secret,
secret/storage providers, PostgreSQL runtime, migration, backup, rollback, HTTPS, ingress, health,
scaling, logging, and monitoring.

Fill real values only in an approved private workspace outside Git. HTTPS and webhook ingress
still require private setup. Production security, availability, recovery, capacity, provider
configuration, and release/deployment decisions require independent review.

For webhook-compatible hosting, continue to
[HTTPS webhook production planning](https-webhook-production-planning.md). G4 compatibility
remains conceptual; G5 performs no live reachability, DNS, TLS, or registration check.
## G6 handoff

G6 may reference this hosted plan by an opaque placeholder. It does not deploy, inspect private
outputs, or turn a dry run into launch or pilot approval; private human review is still required.
