# Command reference

## Phase J8 versioned 0.1.0 release handoff

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make versioned-release-handoff` | Print the sanitized offline handoff review. | No |
| `make release-notes-draft` | Print the release-notes draft. | No |
| `make release-scope-summary` | Print included scope and known limitations. | No |
| `make maintainer-release-decision-checklist` | Print the human decision checklist. | No |
| `make post-release-checklist` | Print the conditional post-release checklist. | No |
| `make versioned-release-artifact-check` | Validate disposable handoff artifacts in temporary output. | Temporary only |

These commands do not build packages or Docker images, publish or upload artifacts, create tags or
releases, deploy documentation or the application, call GitHub/registries, or change workflows.
`0.1.0` remains prepared metadata; maintainer authorization and private security/legal/
infrastructure review are required, and no production, Pilot, hosted, release, or deployment
approval is granted.

## Phase J7 release-candidate checklist

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make release-candidate-review` | Aggregate public release-candidate readiness inputs. | No |
| `make release-candidate-checklist` | Print gates for prepared `0.1.0` metadata. | No |
| `make release-candidate-gap-register` | Print private/maintainer review gaps. | No |
| `make release-candidate-command-plan` | Print an ordered plan of existing non-writing checks. | No |
| `make release-candidate-artifact-check` | Validate sanitized artifacts in temporary storage. | Temporary only |

J7 adds no build, publish, tag, release, or deployment target. Maintainer review comes later, and
these commands grant no approval.

## Phase J6 version and package metadata preparation

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make version-prep-review` | Check prepared target/version/package consistency offline. | No |
| `make package-metadata-summary` | Print existing and review-needed package metadata. | No |
| `make version-source-map` | Print canonical version ownership and descriptive consumers. | No |
| `make release-boundary-checklist` | Print later release-candidate review boundaries. | No |
| `make version-prep-artifact-check` | Validate sanitized artifacts in temporary storage. | Temporary only |

J6 adds no Make target that builds, publishes, tags, releases, or deploys. These checks make no
GitHub/package-registry call, change no workflow, and grant no approval.

## Phase J5 documentation-site polish

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make docs-site-polish-review` | Inspect local docs, reader paths, navigation, and safety. | No |
| `make docs-reader-paths` | Print canonical audience reading paths. | No |
| `make docs-navigation-map` | Print topic groups and primary page ownership. | No |
| `make docs-site-checklist` | Print local documentation-readiness checks. | No |
| `make docs-site-polish-artifact-check` | Validate sanitized artifacts in temporary storage. | Temporary only |

`make docs-serve` is an optional loopback preview, not deployment. J5 adds no GitHub Pages workflow,
external analytics, tracking, search, CDN asset, build/publish step, or approval.

## Phase J4 hosted UI preparation

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make hosted-ui-review` | Inspect existing routes, templates, and guidance offline. | No |
| `make hosted-ui-page-inventory` | Print page class, protection, and mode readiness. | No |
| `make hosted-ui-readiness-checklist` | Print public-safe hosted-evaluation checks. | No |
| `make hosted-ui-private-gates` | Print the private infrastructure/security gates. | No |
| `make hosted-ui-artifact-check` | Validate sanitized artifacts in temporary storage. | Temporary only |

These commands deploy nothing, run no frontend build, load no external assets, analytics, or
telemetry, and grant no production, Pilot, release, or deployment approval.

## Phase J3 API documentation

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make api-docs-review` | Inspect and validate all 81 local FastAPI routes offline. | No |
| `make api-route-reference` | Print route method, class, protection, risk, and purpose. | No |
| `make api-usage-examples` | Print fake/local Demo-safe usage guidance. | No |
| `make openapi-local-guide` | Print guidance for viewing OpenAPI after starting the local app. | No |
| `make api-docs-artifact-check` | Validate sanitized artifacts in temporary storage. | Temporary only |

These commands make no live API or Procore call and use no external OpenAPI tooling. They add no
route and grant no production, Pilot, release, or deployment approval. Generated outputs belong
only in ignored roots.

## Phase J2 local Demo data

| Command | Purpose | Writes? |
| --- | --- | --- |
| `make demo-seed-plan` | Preview deterministic fake datasets for local SQLite. | No |
| `make demo-seed` | Idempotently seed demo-marked fake records in local Demo Mode SQLite. | Local demo DB only |
| `make demo-data-check` | Validate fake-only inventory and safe boundaries. | No |
| `make demo-reset-plan` | Preview only the demo-marked records eligible for reset. | No |
| `make demo-reset DEMO_RESET_CONFIRMATION="RESET DEMO DATA"` | Remove only demo-marked local records after exact confirmation. | Local demo DB only |
| `make demo-data-artifact-check` | Generate and validate sanitized artifacts in temporary storage. | Temporary output only |

`make try-demo` and `make first-run` never reset data. J2 uses no Procore call, cloud service, or
external database. Reset cannot touch private workspace, Sandbox, Pilot, Hosted, cloud, or
customer data. These commands imply no production, Pilot, release, deployment, or Procore
approval.

## Phase J1 local setup experience

For a new clone, first create `.venv`, second activate it, and third install local development
dependencies as shown in the [local installer guide](local-installer-guide.md). Demo Mode needs no
Procore credentials, other secrets, cloud service, or external database. Sandbox, Pilot, and
Hosted remain separate private, gated paths.

| Command | Purpose |
| --- | --- |
| `make setup-experience-review` | Run the offline, non-writing public setup review. |
| `make first-run-checklist` | Print the sanitized first-run checklist. |
| `make local-installer-guide` | Print the sanitized local installer guide. |
| `make setup-troubleshooting-guide` | Print missing Git/Python/pip/Make/PATH guidance. |
| `make setup-experience-artifact-check` | Generate only temporary, ignored artifacts and check them. |

These commands make no Procore, cloud, external database, registry, release, or deployment call.
They perform no package or Docker build, publish, tag, release, or deployment and imply no
production, Pilot, release, deployment, or Procore approval.

## Phase I9 security gap closeout

```bash
make security-gap-closeout
make privacy-review-template
make encryption-at-rest-guidance
make private-security-action-register
make known-limitations-closeout
make security-gap-artifact-check
```

The first five commands print sanitized offline review material. Artifact generation is a
separate contained check. None runs a live scanner, calls an external service or Procore,
implements encryption or retention enforcement, deletes/purges data, or sends notifications.
Outputs are guidance and maintainer-review aids, not compliance, certification, production,
pilot, release, or deployment approval. Private review remains required.

I7 provides `make incident-response-review`, `make incident-runbook`, `make audit-log-boundary-map`, and `make forensics-evidence-checklist`; artifact generation is separate and temporary.

## Phase I8 final security review

- `make final-security-review` — aggregate I1–I7 and public repository boundaries offline.
- `make security-readiness-summary` — print the sanitized readiness summary without writing.
- `make security-gap-register` — print sanitized public/private review gaps without writing.
- `make private-security-review-checklist` — print the private-review handoff checklist.
- `make final-security-artifact-check` — generate and clean contained temporary artifacts.

I8 runs no live scanner, external or Procore call, deployment, release, or build. Its output is
maintainer-review input only; it grants no production, pilot, release, legal, compliance, or
security-certification approval, and private security review remains required.

I6 commands are `make supply-chain-review`, `make dependency-boundary-map`, `make package-surface-map`, and `make supply-chain-checklist`. Artifact generation is separate and temporary.

## Phase I5 infrastructure review

`make infra-security-review`, `make secret-boundary-map`, `make storage-boundary-map`, `make database-boundary-map`, and `make infra-security-checklist` are offline and non-writing. `make infra-security-artifact-check` uses an automatically cleaned temporary directory.

## Phase I4 data policy commands

| Command | Safety | Output |
| --- | --- | --- |
| `make data-policy-review` | Offline, no live scan or external call | Sanitized review on stdout |
| `make data-retention-map` | Offline and non-writing | Retention boundary map |
| `make redaction-boundary-map` | Offline and non-writing | Redaction boundary map |
| `make data-handling-checklist` | Offline and non-writing | Public handling checklist |
| `make data-policy-artifact-check` | Temporary local output only | Seven sanitized files, automatically cleaned |

Optional cloud-storage commands are `make cloud-storage-template`,
`make cloud-storage-check`, and `make cloud-storage-explain`. They perform no object or network
operation. See [Optional cloud storage providers](cloud-storage-providers.md).

Optional cloud commands are `make cloud-secret-template`, `make cloud-secret-check`, and
`make cloud-secret-explain`. All three are offline and resolve no values. See
[Optional cloud secret providers](cloud-secret-providers.md).

Most users should use the friendly Make targets first. Run `make commands` for a concise guide.
All friendly targets are local-only: no Procore calls, external connections, deployment, or pilot
approval.

Prefer a guided sequence? See the [Demo walkthrough](walkthrough-demo.md),
[Sandbox walkthrough](walkthrough-sandbox.md), or [Pilot walkthrough](walkthrough-pilot.md).
For documentation navigation and optional local preview guidance, see the
[docs-site guide](docs-site.md).

## Friendly commands

### Intake Review Workspace

- `make review-workspace-summary` prints a sanitized summary of local intake records.
- `make review-workspace-check` validates bounded, read-only workspace behavior.

Both are empty-database safe and make no Procore or external call. Run `make try-demo` first for
fake records, then open `/review`. No lifecycle transition or mutation command exists in H3.

### Intake lifecycle

- `make intake-lifecycle-summary` reads sanitized counts from the local database.
- `make intake-lifecycle-check` validates transition rules without changing persistent state.

H4 status changes are available through guarded local workspace routes. CLI checks perform no
mutation or external call. Statuses do not update Procore and are not approvals or compliance
determinations.

| Difficulty | Command | Purpose | Writes | Procore | External | Private config | Demo-safe |
|---|---|---|---:|---:|---:|---:|---:|
| Beginner | `make help` | Show grouped primary commands. | No | No | No | No | Yes |
| Beginner | `make first-run` | Compatibility alias for the safe onboarding summary. | No | No | No | No | Yes |
| Beginner | `make start` | Show onboarding, doctor, and the best next command. | No | No | No | No | Yes |
| Beginner | `make commands` | Print the grouped public command guide. | No | No | No | No | Yes |
| Beginner | `make next` | Recommend Demo Mode as the default next step. | No | No | No | No | Yes |
| Beginner | `make doctor` | Summarize selected-mode posture safely. | No | No | No | No | Yes |
| Beginner | `make try-demo` | Set up and run synthetic fixtures with local SQLite. | Local DB | No | No | No | Yes |
| Intermediate | `make prepare-sandbox` | Run safe planning and onboarding checks. | No | No | No | Yes | Yes |
| Intermediate | `make prepare-pilot` | Validate fake pilot planning and preflight inputs. | No | No | No | Yes | Yes |
| Intermediate | `make init-private-workspace` | Create ignored placeholder scaffolds. | Yes | No | No | Yes | Not needed |
| Beginner | `make safety-check` | Run usability, public-data, and route audits. | No | No | No | No | Yes |
| Intermediate | `make quality` | Run the complete offline developer suite. | Temporary | No | No | No | Yes |
| Beginner | `make walkthroughs` | List all guided walkthrough documents. | No | No | No | No | Yes |
| Beginner | `make walkthroughs-check` | Verify walkthrough safety and links. | No | No | No | No | Yes |
| Intermediate | `make sandbox-smoke-explain` | Explain the separate manual read-only smoke command. | No | No | No | No | Yes |
| Intermediate | `make sandbox-smoke-preflight` | Check sanitized configuration posture offline. | No | No | No | Yes | Yes |
| Intermediate | `make sandbox-smoke-evidence-template` | Print placeholder-only private evidence-ref metadata. | No | No | No | No | Yes |
| Advanced | `make release-checklist` | Print the future-release maintainer checklist. | No | No | No | No | Yes |
| Advanced | `make release-readiness` | Run local advisory release checks. | No | No | No | No | Yes |
| Advanced | `make release-notes-draft` | Print draft public notes without publishing. | No | No | No | No | Yes |
| Advanced | `make release-readiness-artifact-check` | Generate and remove disposable sanitized drafts. | Temporary | No | No | No | Yes |
| Advanced | `make final-readiness` | Inspect the public repository for maintainer review. | No | No | No | No | Yes |
| Advanced | `make final-readiness-checklist` | Print the final public checklist. | No | No | No | No | Yes |
| Advanced | `make public-handoff-summary` | Print the public/private handoff boundary. | No | No | No | No | Yes |

`make prepare-sandbox` never runs live smoke or resolves secret values.
`make prepare-pilot` never reads real evidence, approves a pilot, connects externally, or deploys.

## Intermediate checks

| Command | Purpose | Writes | Procore | External | Private config | Demo-safe |
|---|---|---:|---:|---:|---:|---:|
| `make private-workspace-check` | Validate ignored workspace structure and Git isolation. | No | No | No | Yes | Not needed |
| `make public-usability-audit` | Audit beginner navigation, commands, files, and safety. | No | No | No | No | Yes |
| `make diagnostics` | Print sanitized aggregate local posture. | No | No | No | No | Yes |
| `make migration-safety-check` | Exercise migrations on disposable SQLite. | Temporary | No | No | No | Yes |

## Advanced planning and provider checks

| Command | Purpose | Writes | Procore | External | Private config | Demo-safe |
|---|---|---:|---:|---:|---:|---:|
| `make secret-provider-check` | Inspect provider posture without resolving values. | No | No | No | Yes | Yes |
| `make secret-refs-check` | Validate reference shape without reading values. | No | No | No | Yes | Yes |
| `make storage-provider-check` | Inspect configured storage posture. | No | No | No | Yes | Yes |
| `make database-check` | Inspect database readiness without connecting. | No | No | No | Yes | Yes |
| `make deployment-check` | Validate fake recipes without deploying. | No | No | No | Yes | Yes |
| `make deployment-safety-check` | Confirm recipe safety boundaries. | No | No | No | Yes | Yes |
| `make support-bundle` | Write an ignored sanitized support bundle. | Yes | No | No | Yes | Yes |

## Manual gated live check

`python scripts/run_sandbox_dmsa_smoke.py ...` is **Advanced**, makes bounded read-only Procore
calls, requires private configuration and explicit gates, and is not safe for first run. It is
never invoked by `make start`, `make try-demo`, `make prepare-sandbox`, or `make prepare-pilot`.
Read [the sandbox smoke guide](sandbox-smoke-tests.md) before considering it.
For the operator-facing boundary and evidence workflow, see
[Sandbox smoke UX](sandbox-smoke-ux.md) and
[Sandbox smoke evidence](sandbox-smoke-evidence.md).

Database connectivity, production migrations, webhook registration, cloud/DNS/TLS operations, and
deployment are not onboarding commands and are never run by friendly targets.

Release commands create no tags, releases, packages, images, publication, or deployment. See
[Release readiness](release-readiness.md).

Documentation commands are also local-only:

| Command | Purpose |
|---|---|
| `make docs-site-check` | Validate navigation targets and docs-site safety without building. |
| `make docs-preview-instructions` | Print optional local preview guidance. |
| `make docs-map` | Point to the user-journey navigation map. |

They do not build, publish, deploy, or enable GitHub Pages. MkDocs is optional.

## Sandbox read validation

| Command | Safety boundary |
|---|---|
| `make sandbox-read-plan` | Offline bounded RFI/Submittal plan; no credentials or calls. |
| `make sandbox-read-preflight` | Offline gate posture; no private reads or calls. |
| `make sandbox-read-evidence-template` | Offline placeholder reference only. |
| `make sandbox-read-validation` | Separate manually gated live Sandbox reads; never a default. |

The live command requires exact confirmation and private DMSA/allowlist configuration. It makes
no Procore writes, registers no webhooks, downloads no attachments by default, and stores no raw
payloads. See [Sandbox read validation](sandbox-read-validation.md).

## Sandbox evidence linkage

| Command | Purpose |
|---|---|
| `make sandbox-evidence-template` | Print a placeholder-only linkage profile. |
| `make sandbox-evidence-check` | Validate the fake example without reading reports. |
| `make sandbox-evidence-mapping` | Print C1/C2/B9/C3/D5 placeholder mappings. |
| `make sandbox-evidence-artifact-check` | Generate and clean temporary safe artifacts. |

All are local-only: no Procore calls, private evidence reads, secret resolution, or approval.

Best next command for a new user: `make start`.

## PostgreSQL runtime commands

- `make postgres-runtime-template` — placeholder private-reference template.
- `make postgres-runtime-check` — offline posture and pool summary.
- `make postgres-migration-plan` — offline checklist; no migration.
- `make postgres-backup-restore-plan` — offline checklist; no dump inspection.
- `make postgres-connectivity-check` — manually gated live read-only probe; refuses by default.
- `make postgres-migration-status-check` — manually gated status-only check; refuses by default.

The two live commands are excluded from quality, preparation, release, and docs checks.

## Hosted deployment template commands

- `make hosted-deployment-template` — print a Docker VPS placeholder profile.
- `make hosted-deployment-check` — validate the example profile offline.
- `make hosted-deployment-matrix` — compare nine conceptual platform styles.
- `make hosted-deployment-artifact-check` — generate and remove temporary local artifacts.

These commands never deploy, contact a cloud or registry, build or push an image, or publish.

## HTTPS webhook planning commands

- `make https-webhook-template` — print the placeholder profile.
- `make https-webhook-check` — validate planning references offline.
- `make https-webhook-matrix` — compare conceptual ingress styles.
- `make webhook-disable-plan` — print the required disable checklist.
- `make https-webhook-artifact-check` — generate and remove temporary planning artifacts.

None calls DNS, TLS, ACME, a public URL, Procore, or webhook registration.

## Hosted pilot operations dry-run commands

- `make hosted-pilot-dry-run-template` — print the placeholder-only profile.
- `make hosted-pilot-dry-run-check` — validate opaque references without opening linked content.
- `make hosted-pilot-dry-run-matrix` — show how G1–G5 and pilot operations fit together.
- `make hosted-pilot-dry-run-artifact-check` — generate and clean temporary safe artifacts.

These commands perform no live operation or deployment and read no private report contents. Their
output is not a launch or pilot approval; private human review remains required.

## Final public readiness commands

- `make final-readiness` — inspect all 23 public readiness categories offline.
- `make final-readiness-checklist` — print the maintainer checklist.
- `make public-handoff-summary` — print the public/private handoff boundary.
- `make final-readiness-artifact-check` — generate and clean temporary artifacts.

These commands make no live calls or private report reads. H1 is not release, production, or pilot
approval; private values and real reports stay outside Git.
## Operator Triage Queue

- `make operator-triage-check` validates the bounded, sanitized, read-only projection.
- `make operator-triage-summary` prints an empty-database-safe local summary.

Neither command changes persistent state or calls Procore or another external system.

## Attachment Review

- `make attachment-review-check` validates the bounded metadata-only projection.
- `make attachment-review-summary` prints an empty-database-safe local summary.

Neither command opens a file, contacts attachment storage, changes state, or makes an external
call.

## Operator Export Pack

- `make operator-export-check` validates JSON, Markdown, and CSV rendering without writing.
- `make operator-export-summary` prints a sanitized combined summary without writing.
- `make operator-export-artifact-check` generates artifacts under temporary `/tmp` storage and
  cleans them automatically.
- `python scripts/generate_operator_export_pack.py` explicitly writes ignored local artifacts.

No command reads attachment files or calls Procore, storage providers, or external services.
# Product dashboard commands

- `make product-dashboard-check` validates the sanitized, non-writing local projection.
- `make product-dashboard-overview` prints the safe local cockpit summary.

Neither command calls Procore or external services, reads attachment files, generates exports,
or mutates persistent state.

## Demo product walkthrough

- `make demo-product-tour` prints the fake-data-only product journey.
- `make demo-product-check` validates all ten offline H9 groups.
- `make demo-evaluation-checklist` prints the maintainer checklist.
- `make demo-product-artifact-check` writes and removes temporary sanitized artifacts.

The first three commands are non-writing quality checks. None runs live Sandbox validation,
calls Procore or an external service, reads private reports, deploys, or releases.

## Offline security threat model

- `make security-threat-model`
- `make security-boundary-map`
- `make security-review-checklist`
- `make security-threat-model-artifact-check` (temporary and cleaned)

These commands run no live scanner/external call and claim no certification or authorization.

## Offline auth and permission boundary audit

- `make auth-boundary-audit`
- `make auth-boundary-map`
- `make permission-boundary-checklist`
- `make auth-boundary-artifact-check` (temporary and cleaned)

These commands inspect local code structure only. They add no auth provider and perform no live
permission, Procore, database, cloud, deployment, or external check.

## Offline webhook security review

- `make webhook-security-review`
- `make webhook-signature-boundary`
- `make webhook-replay-checklist`
- `make webhook-security-artifact-check` (temporary and cleaned)

These commands use local code and fake fixtures only. They perform no live replay, webhook
registration, Procore call, endpoint call, database write, or external operation.
