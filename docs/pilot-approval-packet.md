# Private pilot approval packet

Phase C3 adds a local-only, placeholder approval packet pattern for a future controlled private
pilot. It combines B9 readiness references, C1 evidence references, C2 review/expiry posture,
launch and rollback conditions, known limitations, risk-acceptance placeholders, and unexecuted
signoff sections.

C3 performs no Procore calls, external calls, evidence collection, reviewer contact,
notifications, approval, deployment, or production enablement. No real approval belongs in this
public repo.

## Public and private boundary

Public content is limited to fake examples only, schemas, validators, renderers, tests, and
documentation. Real packets, identities, signoffs, decisions, evidence, customer data, contacts,
IDs, domains, URLs, paths, reports, screenshots, payloads, databases, attachments, and signatures
must remain in an approved private system outside GitHub.

Packets reference evidence; they never contain evidence contents. Acceptable placeholders include
`PILOT_READINESS_REF_PLACEHOLDER`, `PRIVATE_EVIDENCE_REF_PLACEHOLDER`,
`REVIEWER_PLACEHOLDER`, and `ROLLBACK_TRIGGER_PLACEHOLDER`.

Blocked content includes real names, emails, phone numbers, numeric Procore IDs, customer domains,
Authorization material, secrets, signed URLs, `.env` assignments, database or storage URLs,
absolute paths, raw evidence/support/smoke/webhook/review artifacts, and binary/generated packet
references.

## Status and conditions

- `draft_placeholder` and `needs_review` identify open private work.
- `ready_for_private_review` means the fake packet is structurally complete and safe to hand off
  privately; it is not approval.
- `blocked` indicates unsafe content or configuration.
- `approved_placeholder` and `rejected_placeholder` are template outcomes only.
- `not_applicable` marks a condition that is not required.

Launch conditions are prerequisites that must remain true before a private pilot could begin.
Rollback conditions pair placeholder triggers with placeholder responses for stopping or
reversing a future pilot. Known limitations must remain explicit. Their risk-acceptance entries
are planning placeholders only: risk acceptance is not legal or compliance approval, security
certification, customer authorization, or production approval.

## Local workflow

```bash
python scripts/print_pilot_approval_template.py
python scripts/validate_pilot_approval_packet.py \
  examples/pilot-approval/example_pilot_approval_packet.json
python scripts/check_pilot_approval_safety.py \
  examples/pilot-approval/example_pilot_approval_packet.json
python scripts/generate_pilot_approval_packet.py \
  examples/pilot-approval/example_pilot_approval_packet.json \
  --output-root pilot-approval-output
```

Use `--strict` to fail on safety blockers and `--strict-review` to fail while safe review work
remains. The safety checker accepts either one packet JSON file or a generated local packet
directory.

Generated artifacts are ignored by Git. They include sanitized JSON/Markdown packet metadata,
summary, launch conditions, rollback conditions, risk-acceptance placeholders, an unexecuted
signoff template, and an artifact manifest. They exclude real identities, signatures, decisions,
evidence contents, private review artifacts, credentials, URLs, paths, raw reports, screenshots,
payloads, attachments, and database files.

For private handoff, validate and safety-check the placeholder packet, keep real supporting
material in the authorized private system, grant reviewers minimum access, and use an approved
private channel. Never copy real reviewer or approver details, signoffs, approval records, or
evidence into GitHub.

Future work may add separately authorized private reviewer authentication, access control,
approval history, legally reviewed risk handling, notifications, retention, and real pilot
authorization. C3 implements none of those capabilities.
