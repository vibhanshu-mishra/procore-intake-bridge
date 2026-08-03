# Changelog

## Phase J8 — versioned 0.1.0 release handoff

- Added offline release handoff documentation, a release notes draft, included-scope and known-
  limitations guidance, maintainer decision checklist, post-release checklist, evidence-matrix
  shape, and placeholder-only examples.
- `0.1.0` is prepared as release metadata only. J8 performs no package/Docker build, publish,
  upload, tag, release, docs deployment, application deployment, external call, or workflow change.
- Maintainer authorization remains required; no production, Pilot, hosted, release, deployment,
  legal, privacy, security, publication, or Procore approval is granted.

## Phase J7 — prepared 0.1.0 release-candidate checklist

- Added an offline release-candidate review, checklist, gap register, command plan, and
  placeholder-only examples that aggregate existing public readiness inputs.
- `0.1.0` remains prepared metadata, not a released version; the checklist may support later
  maintainer review but cannot create or approve a release candidate.
- J7 performs no package/Docker build, publish, tag, release, deployment, external call, or workflow
  change and grants no production, Pilot, release, deployment, publication, or Procore approval.

## Prepared target 0.1.0 — Phase J6

- Prepared release-candidate metadata, a package summary, version source map, release boundary
  checklist, and placeholder-only examples for later maintainer review.
- The `0.1.0` target is prepared/unreleased metadata. J6 performs no package or Docker build,
  publish, upload, tag, release, deployment, registry/GitHub call, or workflow change.
- No production, Pilot, release, deployment, publication, certification, or Procore approval is
  granted; release-candidate review remains a later maintainer action.

## Phase J5

- Added canonical reader paths, a topic-owned navigation map, local preview guidance, and
  placeholder-only docs-site review examples.
- Improved handbook discovery for evaluator, Demo, Sandbox, Pilot, Hosted, security, operator,
  release-reviewer, and contributor journeys while retaining one command-reference owner.
- J5 performs no docs deployment and adds no GitHub Pages workflow, external analytics, tracking,
  search service, CDN asset, publication, or production/Pilot/release/deployment approval.

## Phase J4

- Added an offline hosted UI preparation guide, page inventory, readiness checklist, private-gate
  guide, and placeholder-only examples for future hosted evaluation.
- Documented protected admin/dashboard/review surfaces, local lifecycle controls, metadata-only
  attachments, command-only exports, fake-local Demo dependencies, and private review gates.
- J4 performs no deployment and adds no frontend build system, external assets, analytics,
  telemetry, public download, file serving, or production/Pilot/release/deployment approval.

## Phase J3

- Added a complete offline reference for all 81 current FastAPI application routes, Demo-safe API
  examples, local OpenAPI viewing guidance, and placeholder-only public examples.
- Documented deliberately public health/readiness routes, protected admin/dashboard/review and
  deployment surfaces, local-only lifecycle mutations, signature-bound webhook routes, and
  Demo/intake/sync and metadata-only attachment boundaries.
- J3 adds no product route, live call, external OpenAPI tooling, public export download,
  attachment file serving, Procore write-back, or production/Pilot/release/deployment approval.

## Phase J2

- Added local Demo Mode seed/reset guidance, a non-writing seed plan, a fail-closed reset guide,
  and placeholder-only examples for deterministic fake data in local SQLite.
- Documented idempotent seeding, non-destructive `make try-demo`, inventory checking, and reset
  limited to demo-marked records after the exact `RESET DEMO DATA` confirmation.
- J2 performs no Procore, cloud, or external-database call; touches no private workspace,
  Sandbox, Pilot, Hosted, cloud, or customer data; and grants no production, Pilot, release,
  deployment, or Procore approval.

## Phase J1

- Added a local installer guide, canonical first-run checklist, setup troubleshooting guide, and
  offline setup experience review for Git, Python 3.12+, pip, Make, virtual environments, local
  dependency installation, Demo safety, and next-command guidance.
- Added five placeholder-only setup examples and documented separate gated Sandbox, Pilot, and
  Hosted paths. Demo requires no Procore credentials, other secrets, cloud services, or external
  database.
- J1 performs no package or Docker build, publish, tag, release, deployment, or live external
  operation and grants no production, Pilot, release, deployment, or Procore approval.

## Phase I9

- Added an offline security gap closeout, policy-versus-implementation guidance, privacy review
  template, encryption-at-rest guidance, private security action register, known-limitations
  closeout, and placeholder-only examples.
- I9 adds no live scanner, external or Procore call, encryption, retention enforcement,
  deletion/purge, notification, legal workflow, release, or deployment behavior.
- The pack grants no compliance, certification, production, pilot, release, deployment, or
  Procore approval; private security, legal, privacy, and infrastructure review remains required.

- Added Phase I7 offline incident-response, audit-log, and forensics readiness pack.

- Added Phase I6 offline dependency and supply-chain review, maps, checklist, examples, and sanitized artifacts.

- Added Phase I5 offline secrets/storage/database security review, maps, checklist, provider matrix, examples, audits, and sanitized artifacts.

- Added Phase I4 offline Data Retention and Redaction Policy schemas, checks, maps, examples, documentation, audits, and sanitized temporary artifacts.

## Unreleased

- Phase I3 adds an offline webhook replay/signature hardening review, public-safe artifacts,
  fixture matrix, documentation, audits, and regression coverage without live replay or
  registration.

- Phase I2 adds an offline auth/permission boundary audit, route protection map, checklist,
  sanitized CSV artifact, audit integration, documentation, examples, and regression coverage.

- Phase I1 adds an offline public-safe security threat model, trust-boundary map, checklist,
  placeholder examples, audits, and tests. It runs no scanner/external operation and grants no
  certification or production authorization.

- Phase H9 adds a fake-data-only Demo Product Walkthrough Pack, offline evaluator, optional
  ignored artifacts, examples, documentation, audits, and tests. It adds no route, integration,
  live validation, deployment, release, private-report access, or external decision claim.

- Phase G2 adds optional S3, Azure Blob, and GCS adapters, fail-closed operation gates, offline
  readiness commands, placeholder examples, audits, and mocked tests.

- Phase G1 adds optional AWS Secrets Manager, Azure Key Vault, and GCP Secret Manager adapters,
  fail-closed gates, offline readiness commands, placeholder examples, audits, and mocked tests.

- F3 adds placeholder-only Sandbox evidence linkage, C1/C2/B9/C3/D5 mapping templates, local
  validators, ignored artifacts, and private-report safety rules. It reads no reports and grants
  no Pilot approval.

- F2 adds offline Sandbox read-validation planning, a separately gated bounded RFI/Submittal live
  command, sanitized count/hash-only reporting, private evidence refs, and fail-closed safety
  checks. Live calls remain absent from quality and default workflows.

- E5 adds a local-only MkDocs navigation foundation, user-journey documentation map, offline
  checker, optional preview guidance, and generated-site safety rules. It does not build,
  publish, host, deploy, or enable GitHub Pages.

- E4 adds public-safe release-readiness checklists, advisory status reporting, placeholder release
  notes, ignored local artifacts, and manual maintainer-review guidance. It publishes nothing.

- F1 adds offline sandbox smoke preflight, command explanation, placeholder evidence-ref tooling,
  clearer manual-run refusals, and documentation for the private evidence lifecycle. Live smoke
  remains separate and manually gated.

- E3 adds guided Demo, Sandbox, and Pilot walkthroughs, short placeholder-only expected output,
  local walkthrough Make targets, navigation updates, and an offline safety/link verifier.

- E2 adds a typed public command catalog, grouped command and next-step CLIs, onboarding summary,
  consolidated friendly Make targets, compact doctor output, and beginner-first documentation.
  Existing advanced commands remain available and no friendly target makes external calls.

- E1 adds a public usability audit, five-minute quickstart, command reference, first-run
  checklist, troubleshooting guide, friendly Make targets, mode/doctor output polish, navigation
  cleanup, and expanded generated-output safety rules. All checks remain offline and fixture-safe.

- D5 adds a placeholder-only, local sandbox-to-pilot flow, readiness CLIs, private-workspace
  scaffolds, ignored artifacts, diagnostics posture, and explicit launch hold.

- Added D3 PostgreSQL posture, masked database references, offline migration and recovery plans,
  private workspace database templates, and an opt-in manually confirmed read-only connectivity
  boundary.
- Added D4 placeholder deployment recipes, HTTPS/webhook ingress checks, cutover and recovery
  runbooks, private-workspace scaffolds, and offline safety validation.

- Added Phase D1 real environment and contained file secret providers, optional fail-closed cloud
  contracts, masked readiness checks, and private ref templates.
- Added Phase C5 Private Workspace Bootstrap with ignored placeholder scaffolds, validators, and
  Git safety checks.
- Added Phase C4 Three-Mode Quickstart and Doctor for safe local demo, sandbox readiness, and
  private-pilot preparation.

## Unreleased

- C3: placeholder-only private pilot approval packets, launch/rollback conditions, limitation and
  risk templates, local safety checking, and ignored sanitized artifacts. No real approval,
  reviewer contact, notification, or deployment is performed.

- C2: placeholder-only evidence review statuses, bounded local expiry evaluation, renewal
  checklists, fake examples, and ignored sanitized review artifacts. No real review, signoff,
  notification, or approval is performed.

- C1: placeholder-only private pilot evidence schemas, offline redaction validation, fake examples,
  and local ignored workspace scaffolds. No evidence collection, external calls, or pilot approval
  is performed.

- B9: local-only pilot readiness profiles, evidence gates, fail-closed go/no-go decisions,
  sanitized readiness packets, fake examples, and operator documentation. No pilot execution or
  deployment is performed.

- B8: strict local diagnostics, aggregate route/database/queue/readiness summaries, an
  operator-protected read-only endpoint, and sanitized CLI-only support bundles. No external
  observability or telemetry is added.

- B7: placeholder-only customer deployment planning profiles, offline validation, sanitized local
  artifact generation, production planning blockers, and operator documentation. No deployment or
  external integration is performed.

- A1–A8: initial public foundation for fixture intake, guarded DMSA configuration, polling,
  webhooks, attachment manifests, onboarding, local admin, and deployment hardening.
- A9: repository documentation, examples, community files, and public safety audits.
- B1: manually gated sandbox-only DMSA smoke harness.
- B2: production-shaped secret-provider contract and fail-closed adapters.
- B3: deterministic initial schema migration, status, and temporary-SQLite safety checks.
- B4: secret-backed admin/deployment operator guard, rotation, and security headers.
- B5: production-shaped attachment storage contract, safe keys, fail-closed providers, sanitized
  health, and manifest consistency checks.

No release tag or package publication is claimed.
- Added Phase B6: a disabled-by-default, documentation-gated synthetic webhook production
  verification harness, sanitized reports, readiness checks, fixtures, CLI tools, and
  operator guidance. It performs no Procore calls or webhook registration.

- Added Phase G3 PostgreSQL runtime operations polish: optional driver extras, offline pool and
  operational planning, placeholder examples, sanitized reports, and separate disabled-by-default
  connectivity and migration-status checks. No migration, backup, or restore is automated.

- Added Phase G4 hosted deployment template packs for nine common platform styles, with
  placeholder-only snippets, offline validation, contained local artifacts, documentation, and
  public safety checks. No cloud resource, image, release, or deployment is created.

- Added Phase G5 HTTPS/webhook production setup planning with placeholder-only profiles, offline
  validation, ingress/TLS/DNS/disable/rollback plans, contained artifacts, docs, and safety checks.
  No public endpoint is verified and no webhook is registered.
## Phase G6

- Added a public-safe hosted pilot operations dry-run pack with placeholder-only schemas,
  validation, artifact rendering, examples, commands, documentation, and audits.
- The pack performs no live operation, reads no private report contents, and does not represent
  launch or pilot approval.
## Phase H1

- Added the final offline public repository readiness audit, maintainer checklist, handoff summary,
  placeholder examples, documentation, audits, and tests.
- H1 performs no live operation and grants no release, production, or pilot approval.

## Phase H2

- Cleaned stale phase/roadmap language, maintainer command discovery, and G6/H1 example links.
- Strengthened final-readiness ignore coverage and concept-based regression tests.
- Added no product feature, route, external integration, deployment, release, or live operation.

## Phase H3

- Added a GET-only Intake Review Workspace for sanitized local RFI/Submittal records.
- Added bounded pagination, deterministic sorting, masked/hashed source context, attachment
  manifest summaries, and informational priority signals.
- Added local, empty-database-safe CLI/Make checks plus documentation, audits, and tests.
- Added no Procore call or write, lifecycle transition, assignment, comment, approval,
  notification, attachment-content read, or external integration.

## Phase H4

- Added local lifecycle state and append-only event history with a reversible Alembic migration.
- Added five local statuses, a fixed transition graph, bounded reason codes, masked/hashed actor
  labels, transactional updates, and sanitized history.
- Added guarded local HTML/JSON lifecycle routes and integrated state/history into H3.
- Added non-writing CLI/Make checks, documentation, audits, and regression tests.
- Added no Procore/external call, approval, compliance decision, assignment, comment,
  communication, attachment read, or notification integration.

## Phase H5

- Added a GET-only Operator Triage Queue over sanitized H3 records and local H4 lifecycle state.
- Added bounded filters, stable sorting, local signal buckets, summary/page JSON, HTML, CLI/Make
  checks, documentation, audits, and regressions.
- Priority is a deterministic local sorting helper only. H5 adds no mutation, Procore/external
  call, assignment, comment, approval, compliance decision, communication, or notification.

## Phase H6

- Added GET-only attachment manifest summary/detail views over local database metadata.
- Added safe categories, size/count summaries, checksum presence, storage-status labels,
  source-availability signals, CLI/Make checks, documentation, audits, and regressions.
- H6 performs no attachment download, file serving/opening, storage-provider call, mutation,
  Procore/external call, document approval, or compliance determination.

## Phase H7

- Added local JSON, Markdown, and CSV summaries for intake, lifecycle, triage, attachment
  metadata, bounded lifecycle events, and a combined operator packet.
- Added strict output-root validation, ignored artifact patterns, CSV formula neutralization,
  non-writing checks, temporary artifact validation, documentation, audits, and regressions.
- H7 adds no web/download route, Procore/external call, attachment access, mutation, approval,
  compliance certification, or customer-report claim.
# Phase H8 — Admin Dashboard Product Polish

- Added a protected GET-only `/dashboard` product cockpit and sanitized JSON overview.
- Added local, non-writing dashboard check and overview commands.
- Connected review, lifecycle, triage, attachment metadata, export-command, and safety guidance.
- Added no external calls, mutations, downloads, file serving, or new Procore behavior.

## Phase I8

- Added an offline final security readiness review that aggregates I1–I7 and the public safety,
  route, docs-site, Demo, Sandbox/Pilot, generated-output, final-readiness, and release boundaries.
- Added sanitized readiness, gap-register, private-review checklist, and domain-matrix artifacts
  with placeholder-only examples and ignored generated output.
- I8 runs no live scanner, external or Procore call, deployment, release, or build. It grants no
  production, pilot, release, legal, compliance, or security-certification approval; private
  security review remains required.
