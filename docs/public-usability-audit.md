# Public usability audit

The audit verifies I5 docs, scripts, examples, targets, ignored outputs, offline guidance, and certification/approval disclaimers.

The audit verifies I4 docs, commands, examples, ignored outputs, offline guidance, non-destructive boundaries, and certification/approval disclaimers.

H3 checks require the Intake Review Workspace documentation, local summary/check scripts, Make
targets, GET-only routes, docs navigation, and explicit no-Procore-write/no-lifecycle-transition
language. Safety checks also guard against workspace examples exposing raw payloads, source URLs,
private paths, raw source IDs, secrets, or attachment contents.

H4 checks require lifecycle docs, read-only summary/check scripts, Make targets, the reversible
migration, exact local POST allowlisting, and explicit local-only/no-Procore-write language.
They also require clear statements that statuses are not approvals, compliance determinations,
or communications and that every change is audited locally with bounded reasons.

G2 requires four cloud-storage docs, three offline scripts, placeholder-only examples, Make
targets, disabled-by-default guidance, and explicit no-presigned-URL guidance.

G1 requires four cloud-provider docs, three offline scripts, placeholder-only examples, Make
targets, disabled-by-default guidance, and no-cloud-call guidance.

Phase E1 checks whether a new user can find the safe Demo, private Sandbox, and private Pilot
paths. It verifies required docs, scripts, examples, Make targets, ignore rules, next-command
guidance, and tracked-file safety patterns.

E2 also verifies the friendly `make start`, `make commands`, `make next`, `make try-demo`,
`make prepare-sandbox`, and `make prepare-pilot` surface and ensures beginner docs never default
to live smoke or deployment.

E3 verifies the linked Demo/Sandbox/Pilot walkthroughs, placeholder-only expected output, friendly
command order, internal links, and no-live/no-deploy defaults. Run `make walkthroughs-check`.

F1 verifies sandbox smoke UX/evidence docs, offline preflight/explanation/template commands, and
the continued separation of the manually gated live runner.

E4 verifies release-readiness docs and local advisory commands, plus explicit language that
publication and final maintainer approval remain manual.

E5 verifies the local-only MkDocs navigation config, docs-site guide and map, non-writing checker,
optional preview guidance, ignored site output, and the absence of active GitHub Pages,
publication, analytics, or Demo-mode requirements.

F2 verifies the Sandbox read-validation/evidence docs, offline planning commands, separate live
target, placeholder examples, private-report boundary, and absence of live validation from
quality, prepare-sandbox, walkthrough execution, release checks, and docs checks.

F3 verifies linkage docs, fake profiles, local-only commands, Pilot mappings, ignored artifacts,
and explicit language that reports remain private and linkage does not approve a Pilot.

Run:

```bash
make public-usability-audit
```

- `PASS` means required public guidance or structure is present.
- `WARN` means a non-blocking check could not be completed.
- `FAIL` means a required usability or public-safety condition is missing; the command exits
  nonzero.

The output never prints file contents, secret values, raw environment values, private output, or
absolute local paths. Fix failures by restoring the named public file/link/target, removing a
tracked generated artifact, or extending `.gitignore`, then rerun the audit.

This is a public-repository guardrail, not a security certification or pilot approval. What to run
next: `make safety-check`, then `make quality`.

G3 checks require the four PostgreSQL runtime docs, six commands, six Make targets,
placeholder-only examples, ignored operation outputs, explicit no-connect defaults, manually
gated live checks, no migration execution in the plan, and no dump inspection in recovery plans.

G4 checks require five hosted-template docs, four offline scripts and Make targets, nine example
profiles, placeholder-only conceptual snippets, ignored outputs, navigation links, and explicit
language that no deployment automation or cloud call occurs.

G5 checks require four planning docs, five scripts and Make targets, placeholder-only examples,
ignored outputs, navigation links, no DNS/TLS/ACME/public URL/Procore calls, no registration, no
certificate generation, private evidence refs, and a required disable/rollback boundary.
## G6 coverage

The audit requires hosted pilot dry-run docs, scripts, examples, Make targets, ignored outputs,
and explicit language that refs only are checked, no live operation occurs, and no launch or pilot
approval is granted.
## H1 coverage

The public usability audit requires final readiness docs, scripts, examples, Make targets, and
clear language that H1 performs no live operation, keeps private values outside Git, and grants no
release, production, or pilot approval.
H5 adds `operator-triage-check` and `operator-triage-summary` to `make quality`. The usability,
route, documentation, and public-safety audits cover its required files, GET-only routes,
navigation, local sorting disclaimer, and prohibited-action boundary.

H6 adds `attachment-review-check` and `attachment-review-summary` to `make quality`. Audits cover
the required docs/scripts, GET-only route set, absence of file-serving routes, and metadata-only
safety boundary.

H7 adds non-writing `operator-export-check` and `operator-export-summary` quality gates. Audits
verify ignored output patterns, documentation, command discovery, lack of export routes, and
summary-claim safety.
# H8 coverage

The audit checks Product Dashboard documentation, scripts, Make targets, GET-only routes, docs
navigation, local/read-oriented wording, and the absence of export-download or file-serving
behavior.

H9 coverage checks walkthrough/checklist docs, examples, commands, ignore rules, fake-data-only
language, no-live boundaries, and decision disclaimers.

I1 coverage verifies threat-model docs, scripts, examples, commands, ignore patterns, and
offline/no-certification/no-authorization language.

I2 coverage verifies auth-boundary docs, scripts, placeholder examples, commands, ignore
patterns, offline-only behavior, and the absence of new auth-provider or approval claims.

I3 coverage verifies webhook-hardening docs, scripts, fake fixtures, commands, ignore patterns,
no-live-replay/registration language, and the absence of certification or approval claims.
