# Cloud platform hosting templates

AWS ECS-style, Azure Container Apps-style, and Google Cloud Run-style profiles describe common
planning categories without using cloud APIs or including provider IDs. They contain no account,
subscription, tenant, project, resource, cluster, service, task, registry, or infrastructure
identifier.

No Terraform, Pulumi, Kubernetes, Helm, or GitHub Actions automation is included. A private
operator must independently review identity, networking, ingress, HTTPS, secret management,
storage, PostgreSQL, scaling, observability, recovery, cost, and release procedures. These
templates neither certify production security nor approve a Pilot.
