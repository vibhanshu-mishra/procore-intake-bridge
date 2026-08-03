# What Is Included in 0.1.0

`0.1.0` is prepared release metadata only. This scope summary helps a maintainer review what the
public repository contains; it is not a release approval, production approval, Pilot approval, or
deployment approval.

## Included

| Area | Public handoff coverage |
| --- | --- |
| Local setup and Demo | J1 setup guidance, deterministic local Demo seed/reset, and troubleshooting. |
| API documentation | J3 route reference, boundary notes, and local OpenAPI viewing guidance. |
| Hosted preparation | J4 offline page inventory and private infrastructure/security gates. |
| Documentation site | J5 reader paths, navigation map, and local-only preview guidance. |
| Version metadata | J6 prepared target/package metadata and J7 release-candidate review inputs. |
| Security and safety | I-series offline threat, privacy, supply-chain, incident, and public-safety material. |
| Operator review | H-series local review, lifecycle, triage, attachment metadata, and sanitized summaries. |
| Release handoff | J8 notes draft, decision checklist, evidence matrix, known limitations, and post-release aid. |

## Boundary of the included scope

The handoff reads local repository evidence only. It does not include private customer records,
reports, credentials, logs, infrastructure identifiers, or approval records. It adds no route,
write-back behavior, file serving, export-download endpoint, external analytics, or telemetry.

No package build, Docker build, publish, upload, tag, release, docs deployment, application
deployment, or workflow automation happened in J8. Actual release work remains outside J8 and
requires explicit maintainer authorization.

## Known limitations not included

- Private review remains required; no production approval is granted.
- No hosted deployment or notification system is included.
- No full audit log or retention enforcement is included.
- No app-level encryption is implemented by this handoff.
- No privacy/legal compliance claim is made.
