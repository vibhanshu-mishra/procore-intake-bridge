# Release Candidate Gap Register

The public checklist cannot resolve private release decisions. The following categories remain for
maintainer or authorized private review:

| Gap | Why it remains private | Closeout evidence |
| --- | --- | --- |
| Security and infrastructure | Live provider permissions and hosted controls are not inspected | Authorized private review |
| Legal, license, and ownership | Public automation cannot make legal determinations | Maintainer/legal decision |
| Artifact contents and reproducibility | J7 builds no package or image | Later controlled artifact review |
| Registry, signing, and credentials | Secret values must remain outside Git | Private publication procedure |
| Release notes and support scope | Human editorial and ownership decisions remain | Maintainer sign-off |
| Rollback and deployment authorization | No live release/deployment occurs | Authorized operational decision |

Do not put private findings, identities, credentials, signing material, infrastructure values,
reports, or approval records in this repository. `needs_review` is an honest boundary, not a failed
release and not permission to publish.
