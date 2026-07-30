# Optional cloud storage providers

Use the local provider first. S3, Azure Blob, and GCS are optional for a privately operated
Sandbox or Pilot; Demo Mode requires none of them.

All cloud storage providers are disabled by default. An object operation requires provider
selection and enablement, global cloud permission, cloud network enablement, the exact private
operator confirmation, resolved private configuration references, and the matching optional SDK.
Missing dependencies report `dependency_missing` without a traceback.

`make cloud-storage-check`, health, inventory, doctor, quality, documentation, and release checks
never contact cloud services or perform object operations. Health network checks are off.

Optional private-runtime installs:

```text
pip install -e '.[s3-storage]'
pip install -e '.[azure-blob-storage]'
pip install -e '.[gcs-storage]'
pip install -e '.[cloud-storage]'
```

List, delete, and overwrite have separate default-off gates. G2 has no presigned URL generation.
Never commit credentials, resource identifiers, bucket/container/project/account names, object
keys from live data, private paths, URLs, or object contents. Readiness is not production security
approval.

Offline commands:

```text
make cloud-storage-template
make cloud-storage-check
make cloud-storage-explain
```

The exact confirmation phrase is documented in `.env.example`; leave it empty in default
workflows.
