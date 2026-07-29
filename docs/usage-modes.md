# Three usage modes

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
