# Optional cloud secret providers

Use the `env` or `file` provider first. AWS Secrets Manager, Azure Key Vault, and GCP Secret
Manager are optional boundaries for a privately operated Sandbox or Pilot; Demo Mode requires
none of them.

All cloud providers are disabled by default. A resolution is allowed only after the provider is
selected and enabled, cloud use and cloud network use are enabled, the exact operator
confirmation is set privately, required configuration references resolve, and the matching
optional dependency is installed. Missing dependencies report `dependency_missing` without a
traceback.

`make cloud-secret-check`, health, inventory, doctor, quality, documentation, and release checks
never contact cloud services or resolve values. Health network checks are off by default.

Optional installs:

```text
pip install -e '.[aws-secrets]'
pip install -e '.[azure-secrets]'
pip install -e '.[gcp-secrets]'
pip install -e '.[cloud-secrets]'
```

Install these only in the private runtime that needs them. Never commit credentials, credential
files, account identifiers, resource names, vault URLs, project identifiers, or resolved values.
Provider readiness is not production security approval.

Useful offline commands:

```text
make cloud-secret-template
make cloud-secret-check
make cloud-secret-explain
```

See the provider-specific pages for configuration-reference rules. The exact confirmation phrase
is documented in `.env.example`; leave it empty for all default workflows.
