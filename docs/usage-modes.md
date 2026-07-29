# Three usage modes

For the ordered transition and local checks, see [Demo → Sandbox → Pilot](sandbox-to-pilot-flow.md).

Procore Intake Bridge has three explicit modes. Start with `make modes` and `make doctor`;
both commands are local-only and print configuration posture rather than private values.

| Mode | Purpose | Private inputs | Starting command |
| --- | --- | --- | --- |
| Demo | Local fixture walkthrough | None | `make demo` |
| Sandbox | Read-only checks against your own sandbox | Ignored DMSA references and scope | `make sandbox-check` |
| Pilot | Controlled private-pilot preparation | Private evidence, review, approval, and rollback records | `make pilot-check` |

The public repository contains synthetic examples only. The doctor never resolves secrets, reads
private artifact contents, contacts Procore, or contacts external providers. Its status is guidance,
not production approval, security certification, or Procore endorsement.

Choose demo to evaluate the workflow locally. Choose sandbox only when you control an appropriate
Procore sandbox and can keep its credentials in ignored private configuration. Choose pilot after
the sandbox posture is understood and an authorized private workspace is available.

C5 provides `make init-private-workspace` for Sandbox and Pilot placeholder scaffolds. Generated
files are ignored; real values and evidence remain local/private. Demo does not require it.

Demo requires no secret provider. Sandbox can use private env refs or contained file refs. Pilot
requires a real provider posture; `external_placeholder` is not sufficient for a real pilot.
Optional cloud kinds remain disabled and make no calls during doctor/readiness checks.

Database posture follows the same progression: Demo uses SQLite, local Sandbox may simulate with
SQLite, and Pilot requires PostgreSQL through a private URL reference plus reviewed migration,
backup, restore, and rollback plans. Mode checks never connect externally.

Deployment is not required for Demo. Hosted Sandbox should review an appropriate D4 recipe, and
Pilot should complete deployment, HTTPS/ingress, backup, rollback, and operator runbooks privately.
Repository checks never execute deployment.
