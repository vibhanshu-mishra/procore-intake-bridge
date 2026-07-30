# GCS storage

GCS support is optional and dynamically imports `google-cloud-storage`. Use private project and
bucket environment references plus safe relative object keys. Full resource names and GCS URLs
are blocked by default.

Fully gated operations support upload, download, and existence checks. New writes use a generation
precondition unless overwrite is separately enabled. Delete and list require separate gates.
Errors are sanitized without project/bucket names, keys, credentials, paths, or contents.

Default checks make no GCP call. G2 provides no presigned URLs, and readiness is not production
security approval.
