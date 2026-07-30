# S3 storage

S3 support is optional and dynamically imports `boto3`. Use a private bucket environment
reference, region reference, and safe relative object keys. Bucket resource identifiers and S3
URLs are blocked by default.

Fully gated operations support `put_object`, `get_object`, and `head_object`. Writes use a
no-overwrite precondition unless overwrite is separately enabled. Delete and list require their
own gates. SDK errors are sanitized without bucket names, keys, credentials, or contents.

Default checks make no AWS call. G2 provides no presigned URLs, and readiness is not production
security approval.
