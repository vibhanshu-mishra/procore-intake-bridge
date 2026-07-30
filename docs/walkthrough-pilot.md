# Pilot walkthrough

## Who this is for

Use this optional path to prepare a controlled private pilot after Demo and authorized Sandbox
work. It does not approve a real pilot, establish production security, or deploy anything.
The journey requires a private workspace, evidence refs and review, and a private approval packet.

## Command sequence

```bash
make start
make init-private-workspace
make prepare-pilot
python scripts/check_database_readiness.py
python scripts/check_attachment_storage.py
python scripts/check_secret_provider.py
python scripts/check_pilot_preflight.py examples/sandbox-pilot-flow/example_pilot_flow.json
python scripts/validate_pilot_readiness.py examples/pilot-readiness/example_pilot_profile.json
python scripts/validate_pilot_approval_packet.py examples/pilot-approval/example_pilot_approval_packet.json
```

These commands use configuration posture or fake examples. They make no external connection,
read no real evidence contents, execute no production migration, and create no approval.

## Private preparation order

1. **Workspace:** initialize ignored sections for environment, storage, database, deployment,
   evidence, approval, diagnostics, rollback, and launch.
2. **Secrets:** keep DMSA, admin, and webhook values in an approved private provider; store refs
   only.
3. **Storage:** validate a contained private root or reviewed provider posture.
4. **Database:** prepare a private PostgreSQL ref, SSL posture, isolated migration evidence,
   backup, restore, and rollback plans. Routine readiness does not connect.
5. **Deployment recipe:** validate placeholder recipes privately; this repository does not
   provision, change DNS/TLS, register webhooks, or deploy.
6. **Diagnostics:** review sanitized diagnostics and support-bundle posture. Keep any actual
   support bundle private and ignored.
7. **Evidence manifest:** record refs only; never copy evidence contents into Git.
8. **Review and expiry:** record private review status, expiry, renewal, and limitations.
9. **Readiness gate:** review the local `GO`, `NO_GO`, `NEEDS_REVIEW`, or `BLOCKED` planning
   result. A public example result has no approval meaning.
10. **Approval packet:** prepare placeholder refs, launch conditions, rollback conditions, risks,
    and private signoffs.
11. **Sandbox-to-pilot flow:** reconcile every milestone and unresolved finding.
12. **Launch hold:** keep launch blocked until authorized humans review private evidence,
    security, legal/privacy, operations, backup/restore, rollback, and customer authorization.

See the short [illustrative output](../examples/walkthrough-output/pilot_expected_output.md).

## Required human review

Authorized reviewers must privately validate real identity and access controls, DMSA scope,
evidence authenticity, secret/storage/database posture, migration and recovery testing,
monitoring/incident response, limitations, legal/privacy obligations, approval authority, and the
launch/rollback decision.

## What remains private

All customer data, credentials, IDs, contacts, domains, infrastructure details, database
configuration, evidence, reviews, approvals, diagnostics, reports, backups, and generated output
remain outside Git.

## What to run next

Run `make safety-check`, resolve private findings, and keep launch on hold. A passing public
validator does not approve a real pilot.
