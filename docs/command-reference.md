# Command reference

Most users should use the friendly Make targets first. Run `make commands` for a concise guide.
All friendly targets are local-only: no Procore calls, external connections, deployment, or pilot
approval.

Prefer a guided sequence? See the [Demo walkthrough](walkthrough-demo.md),
[Sandbox walkthrough](walkthrough-sandbox.md), or [Pilot walkthrough](walkthrough-pilot.md).
For documentation navigation and optional local preview guidance, see the
[docs-site guide](docs-site.md).

## Friendly commands

| Difficulty | Command | Purpose | Writes | Procore | External | Private config | Demo-safe |
|---|---|---|---:|---:|---:|---:|---:|
| Beginner | `make help` | Show grouped primary commands. | No | No | No | No | Yes |
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
