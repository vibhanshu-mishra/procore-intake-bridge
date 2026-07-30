# GCP Secret Manager

GCP Secret Manager support is optional and dynamically imports
`google-cloud-secret-manager`. Demo Mode and the default installation do not need it.

Use simple secret names and a private project-ID environment reference. Full resource names are
blocked by default. The provider uses the `latest` version only after all common gates pass.

`access_secret_version` errors are sanitized, and binary or undecodable results fail closed.
Reports never include project identifiers, resource names, credential paths, or secret values.

The default health and inventory paths make no GCP call. Cloud readiness remains an operator input,
not production security approval.
