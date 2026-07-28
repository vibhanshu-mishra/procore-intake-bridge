# GC/Owner onboarding packets

The onboarding packet generator creates a reviewable installation and permission request for a
GC/Owner-owned Procore account. It helps a Procore Company Admin understand why a private app and
DMSA are requested, which projects and tools are in scope, what data is read, and how access remains
under GC/Owner control.

## Generated content

Packets contain Markdown and structured JSON with sections A–S: purpose, audience, product
description, DMSA rationale, requested access/projects/permissions, data read, excluded behavior,
attachment handling, webhook/polling behavior, secret handling, GC/Owner revocation control,
installation and permission checklists, health checks, troubleshooting, support placeholder, and
an independent-tool disclaimer.

The canonical permission checklist requests RFIs and Submittals as Read Only, explicit project
access, and attachment visibility only through parent items. Webhooks are optional. Financial,
directory-admin, write, upload, approval, submission, delete, and unrelated administrative access
are not requested by default.

## Preview, generate, and export

`POST /onboarding/preview` renders Markdown/JSON without database persistence. `POST
/onboarding/generate` stores a review copy in `OnboardingPacket`. The connection-specific route
merges the connection's permitted project IDs and local sync-profile tools; it does not contact
Procore.

`POST /onboarding-packets/{id}/export-local` writes deterministic sanitized `.md` and `.json`
files beneath `PROCORE_INTAKE_PACKET_OUTPUT_ROOT`. It returns relative filenames, prevents path
traversal, and uses a gitignored local directory. No PDF, DOCX, email, external storage, hosted
public link, or automatic send is generated in A6.

## Placeholders and customization

Use recipient/requester organization and contact fields to customize a packet. Project identifiers
and `app_version_key_ref` should be placeholders in public examples and tests. A reference is not
the App Version Key itself; any real installation material belongs in a separate approved secure
handoff and must not be pasted into logs, issues, fixtures, or public artifacts.

The included `examples/onboarding/` files use only Example GC Company, Example Engineering Firm,
project IDs `111111` and `222222`, and `APP_VERSION_KEY_PLACEHOLDER`.

## Working with a GC/Owner admin

Provide the reviewed packet to the authorized admin through the organization's approved channel.
The admin should verify current Procore documentation and internal policy because UI labels and
installation workflows can change. The packet does not grant access by itself. The GC/Owner
chooses installation, DMSA assignment, project/tool permissions, and can reduce or revoke access
at any time.

Packets contain no credentials, tokens, webhook secrets, or raw installation keys. The generator
makes no Procore call and sends no email. Procore Intake Bridge is an independent tool and does not
claim Procore affiliation, endorsement, certification, partnership, or official support.
