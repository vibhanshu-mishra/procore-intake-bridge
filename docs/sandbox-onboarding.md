# Sandbox onboarding

Run the fixture demo first, initialize the ignored private workspace, and configure private DMSA
secret references, allowed company/project scope, secret-backed admin authentication, and
read-only permission review. Then run:

```bash
make sandbox-onboarding-check
```

The result may remain `sandbox_needs_configuration`; it reports missing items without resolving
or printing private values. Webhook posture is reviewed without registration. The B1 smoke test
is a later, separately authorized and manually gated action—this check never calls Procore or
runs that harness automatically. Record only its reference privately.
