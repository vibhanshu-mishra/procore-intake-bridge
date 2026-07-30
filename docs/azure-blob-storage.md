# Azure Blob storage

Azure Blob support is optional and dynamically imports `azure-identity` and
`azure-storage-blob`. Use private account/container environment references and safe relative blob
names. Blob URLs are blocked by default.

`DefaultAzureCredential` is created only inside a fully gated operation. Upload, download, and
property checks are supported; delete and list require separate gates, and overwrite defaults
off. Errors are sanitized without account/container names, URLs, blob names, credentials, paths,
or contents.

Default checks make no Azure call. G2 provides no presigned URLs.
