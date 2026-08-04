# Intake record lifecycle and status flow

Phase H4 adds an audited workflow state for records stored in this app. The five local statuses
are `new`, `in_review`, `reviewed`, `needs_follow_up`, and `ignored`.

These statuses are local labels only. They do not update Procore, represent an approval or
compliance determination, assign work, create comments, or communicate with a customer, broker,
or other person. No notification or external call occurs.

## Changing local status

Use the controls on `/review/intake/{record_id}`. The form submits only to the guarded local
`/review/intake/{record_id}/lifecycle` route. JSON clients may use the matching guarded lifecycle
API. Every accepted transition:

1. validates the fixed transition graph and reason code;
2. masks and hashes the placeholder actor label;
3. updates the local state row transactionally; and
4. appends a sanitized local audit event.

Reason codes are fixed and summaries are bounded. Free-text notes are disabled by default.
Lifecycle tables contain internal intake-record IDs only—never Procore source IDs or payloads.

## Legacy local data repair

The canonical lifecycle values are `new`, `in_review`, `reviewed`, `needs_follow_up`, and
`ignored`. Earlier deterministic Demo rows used `blocked` and `completed`; migration
`0003_normalize_intake_lifecycle_statuses` maps those labels to `needs_follow_up` and
`reviewed`, and maps the old Demo reason marker to `demo_placeholder_reason`. Read paths also
represent an un-migrated known value safely while the migration is pending. Unexpected values
are shown only as a generic needs-review finding; raw stored text is never exposed.

## Safety and operations

The lifecycle service reads no attachment contents and exposes no raw payload, source URL, signed
URL, private path, secret, or raw source identifier. The two CLI commands are read-only:

```bash
make intake-lifecycle-summary
make intake-lifecycle-check
```

The reversible `0002_intake_lifecycle` migration creates one current-state table and one event
history table; `0003_normalize_intake_lifecycle_statuses` repairs the allow-listed legacy labels.
Sandbox and Pilot configuration remains private and gated. H5 may add an operator triage queue
later; H4 adds no queue, assignment, message, or notification integration.
## H5 triage projection

The [Operator Triage Queue](operator-triage-queue.md) reads H4 state without lazily creating or
changing it. H5 adds no lifecycle transition; the existing two guarded H4 POST routes remain the
only review mutations.

H7 exports aggregate local status and bounded event metadata only. It excludes actor identity
fields and does not turn lifecycle labels into approval, compliance, or Procore status.
# Product dashboard navigation

H8 shows the aggregate local lifecycle distribution without adding a mutation. Lifecycle labels
do not indicate authorization, compliance, or external system status.

H9 evaluates these local labels without representing production or Pilot authorization.
