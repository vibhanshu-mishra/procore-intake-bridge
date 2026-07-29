# Secret providers

Phase D1 keeps Demo mode secret-free while adding real, optional secret resolution for Sandbox and
Pilot modes. Secret values flow only to internal authentication callers. Reports, diagnostics,
doctor output, exceptions, and CLI tools expose masked refs and presence status only.

## Provider choices

- `disabled` intentionally fails closed.
- `env` resolves an environment variable whose name is the secret ref. It is the simplest Sandbox
  setup; inject values privately at runtime and never commit `.env`.
- `file` resolves a safe relative file under the configured ignored secret root. It is suitable
  for a local private pilot without cloud dependencies.
- `external_placeholder` remains unavailable and is not a real provider.
- `aws_secrets_manager`, `azure_key_vault`, and `gcp_secret_manager` are optional, disabled by
  default, and fail closed when their opt-in, dependency, or private configuration is missing.
  Health checks make no cloud calls.

Demo mode needs no secrets. Sandbox normally needs DMSA refs and may need admin/webhook refs.
Pilot mode must use a real provider rather than `disabled`, `test`, or `external_placeholder`.

## Environment provider

The env provider is the smallest real setup for a privately configured sandbox.

Set `PROCORE_INTAKE_SECRET_PROVIDER=env`, then privately inject variables named by the DMSA,
admin, and webhook refs. References use the `PROCORE_INTAKE_SECRET_` prefix. Run
`make secret-provider-check` to see masked present/missing status. The checker never dumps the
environment or prints values.

## File provider

The file provider is a local-only option for an ignored private workspace.

Set `PROCORE_INTAKE_SECRET_PROVIDER=file` and keep the default ignored root
`private-workspace/environment/secrets`, or choose another explicitly private/ignored directory.
Configure relative refs such as `dmsa/client_secret.secret`. The provider rejects absolute paths,
traversal, escaped symlinks, oversized/binary files, databases, documents, images, archives, and
generated reports. It reads small UTF-8 text files only and strips trailing newlines.

Use `make init-private-workspace` to create reference-only templates. Secret files themselves are
never generated. Secrets must not be committed.

## Verification and troubleshooting

```bash
make secret-provider-template
make secret-provider-check
make secret-refs-check
make file-secret-provider-check
```

Missing refs are shown only in masked form. A disabled provider, unsafe file root, missing optional
SDK, or incomplete cloud configuration fails closed with sanitized errors. DMSA authentication,
admin token verification, webhook signature verification, and the gated sandbox smoke path all
consume the same provider interface.

Cloud-provider production verification remains future private work. D1 does not contact cloud
providers during doctor, diagnostics, quality checks, tests, or mode readiness and does not claim
production secret management is complete.
