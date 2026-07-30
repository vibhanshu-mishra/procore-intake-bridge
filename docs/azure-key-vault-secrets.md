# Azure Key Vault secrets

Azure Key Vault support is optional and dynamically imports `azure-identity` and
`azure-keyvault-secrets`. The default installation remains lightweight.

Use a vault-name environment reference and simple secret names. Vault URLs are blocked by default.
`DefaultAzureCredential` is constructed only inside a fully gated resolution. Tenant and vault
configuration remain private and are never emitted.

`get_secret` can run only after every common cloud gate passes. Authentication, permission,
not-found, and service errors are sanitized without exposing vault URLs, credential paths,
resource names, or secret values.

The default health and inventory paths make no Azure call. Readiness does not establish production
security approval.
