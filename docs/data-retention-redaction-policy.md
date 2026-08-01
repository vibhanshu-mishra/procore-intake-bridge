# Data Retention and Redaction Policy

## I9 policy-versus-enforcement clarification

This document is policy and review guidance. Phase I9 does not add general retention enforcement,
deletion endpoints, or purge jobs. Any private retention schedule, legal obligation, execution
mechanism, and evidence requires authorized private legal, privacy, security, and infrastructure
review. No compliance, certification, or operational approval is granted.

I7 excludes raw logs, payloads, evidence contents, notices, dumps, captures, and forensic images from public outputs.

I6 generated reports follow the ignored-output and private-content exclusion policy.

I5 applies these redaction requirements to secret, storage, database, migration, backup, and provider-review output.

Phase I4 is an offline data policy/redaction review for the public repository. It inspects a curated set of local source, documentation, test, and ignore-rule files. It performs no live scan, no external call, no Procore call, no cloud call, and no database connection.

## Policy boundary

The review classifies public placeholders, local demo and runtime metadata, private configuration and evidence references, webhook payload boundaries, attachment metadata, export and diagnostic summaries, and generated output. Raw payloads, headers, secrets, URLs, signed URLs, private paths, storage keys, original filenames, attachment contents, and private report contents are excluded from public outputs.

Public examples remain placeholder-only. Sandbox and pilot evidence, provider configuration, and private workspace material remain reference-only. Generated review output is ignored by Git.

## Retention and deletion

This public layer documents boundaries; it implements no destructive deletion and no purge jobs. It does not add deletion endpoints, background retention workers, database cleanup, or cloud object deletion. Retention periods and operational deletion procedures remain decisions for private legal and security review.

## Claims and limitations

This review is not legal compliance certification. It makes no GDPR, CCPA, HIPAA, SOC 2, or ISO certification claim and provides no production, launch, hosted-pilot, or security approval. It is not Procore endorsement, partnership, certification, or official support.

Run the non-writing review with `make data-policy-review`. The map and checklist commands are also non-writing. `make data-policy-artifact-check` is separate and writes only to an automatically cleaned temporary directory.

See the [retention map](data-retention-map.md), [redaction boundary map](redaction-boundary-map.md), and [data handling checklist](data-handling-checklist.md).

I8 carries these boundaries into the [offline final security review](final-security-readiness-review.md).
No live scanner, external/Procore call, deletion, deployment, release, or build occurs. Actual
legal obligations and real customer-data handling require private review; the public summary is
not legal compliance, certification, or production/pilot/release approval.
