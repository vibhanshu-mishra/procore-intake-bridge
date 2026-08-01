# Secrets / Storage / Database Security Review

I7 maps exposure and provider-failure scenarios without retrieving secrets or accessing infrastructure.

I6 never sends dependency or provider metadata to an external scanner or registry.

Phase I5 is an offline secrets/storage/DB security review. It inspects curated public repository code, documentation, tests, and ignore rules only. It performs no secret retrieval, no storage access, no database connection, no migration, no backup, no restore, no DB dump inspection, no external call, and no Procore call.

Secret references are allowed; secret values are not. Storage metadata and placeholder references are allowed; object keys, presigned URLs, private paths, original filenames, and contents are not. Database URL references are allowed; database URLs and live database calls are not.

Cloud providers remain optional, disabled by default, and separately gated. Generated review output is ignored. Provider permissions, network controls, resource policies, database roles, operational migration evidence, and backup/restore evidence remain for authorized private infrastructure and security review.

This review is not legal, security, or compliance certification. It makes no GDPR, CCPA, HIPAA, SOC 2, or ISO certification claim and grants no production, launch, or pilot approval. It is not Procore endorsement, partnership, certification, or official support.

Run `make infra-security-review`. The map and checklist targets are non-writing; artifact generation is separate and temporary.

I8 aggregates this review in the [offline final security review](final-security-readiness-review.md).
It retrieves no real credential, calls no provider, Procore, cloud, or database service, and runs
no deployment, release, build, migration, backup, or restore. Real provider permissions and
operational controls remain private-review work; no approval or certification is granted.
