# AWS Secrets Manager

AWS Secrets Manager support is optional and dynamically imports `boto3`. The default installation
does not include it, and Demo Mode does not need it.

Use simple secret names. Resource identifiers are blocked unless the private operator deliberately
enables their use. A region is required by default and is obtained through the configured
environment reference; an optional profile is also reference-only. Neither is shown in reports.

`get_secret_value` can run only after every common cloud gate passes. Only text secrets are
accepted; binary results fail closed. SDK authentication, permission, not-found, and service
errors are converted to sanitized provider errors without resource names or values.

Run `make cloud-secret-check` for offline dependency and configuration posture. It makes no AWS
call. Never put account identifiers, resource identifiers, credentials, or provider output in
public files.
