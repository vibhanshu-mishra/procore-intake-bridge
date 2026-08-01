# Redaction Boundary Map

I5 adds explicit exclusion of secret values, database URLs, object keys, presigned URLs, dump contents, backup contents, and live migration logs.

I4 maps raw-payload, secret, URL, signed-URL, private-path, storage-key, original-filename, attachment-content, source-identifier, actor-identity, diagnostic-error, and CSV-formula boundaries.

Public output contains placeholders, sanitized metadata, or references only. The map performs no live scan and reads no private report. It is not legal compliance certification or approval.

Run `make redaction-boundary-map` to print the sanitized map.
