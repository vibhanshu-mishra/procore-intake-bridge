# Example GC/Owner Private App Installation Packet

> Static fake example. All organizations, contacts, project IDs, and references are placeholders.

## A. Title and purpose

- Request read-only Procore access for Procore Intake Bridge.

## B. Who this packet is for

- Procore Company Admins at Example GC Company.

## C. What Procore Intake Bridge does

- Copies permitted RFI and Submittal metadata into Example Engineering Firm's tracking workflow.

## D. Why DMSA/private app access is needed

- A dedicated service identity keeps access reviewable and independent of employee accounts.

## E. Requested Procore access

- RFIs and Submittals, Read Only, for explicitly approved projects.

## F. Requested projects

- `111111`
- `222222`

## G. Requested permissions

- RFIs: Read Only
- Submittals: Read Only
- Attachments: visible through permitted RFIs/Submittals only

## H. What data is read

- RFI/Submittal metadata, dates, status, and visible attachment metadata.

## I. What the app does not do

- No Procore writes, approvals, submissions, deletes, uploads, financial access, or AI/model calls.

## J. Attachment handling

- Raw signed URLs are never stored.

## K. Webhook and polling behavior

- Webhooks queue events; read-only polling remains the fallback.

## L. Security and secret handling

- Credentials and installation keys are not embedded in this packet.

## M. GC/Owner control and revocation

- Example GC Company controls projects/tools and may revoke access at any time.

## N. Installation checklist

- Verify current Procore documentation and company policy.
- Use `APP_VERSION_KEY_PLACEHOLDER` only as a reference to a separate secure handoff.

## O. Permission checklist

- Grant minimum Read Only access; do not grant writes or financial/admin tools.

## P. Health-check checklist

- Confirm project, RFI, Submittal, and attachment visibility.

## Q. Troubleshooting

- Check DMSA assignment, project allowlist, tool enablement, and environment match.

## R. Support/contact placeholder

- `SUPPORT_CONTACT_PLACEHOLDER`

## S. Independent-tool disclaimer

- Procore Intake Bridge is an independent tool and is not affiliated with, endorsed by, or officially supported by Procore.
