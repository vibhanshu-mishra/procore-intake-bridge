# Private Security Review Checklist

Use this checklist only as a public-safe handoff to authorized private reviewers. Run
`make private-security-review-checklist` for the sanitized offline version.

- [ ] Review live infrastructure and network exposure.
- [ ] Review real credentials, rotation, and access controls without copying values into Git.
- [ ] Review real customer data handling and retention in the applicable private environment.
- [ ] Determine actual legal and regulatory obligations with qualified reviewers.
- [ ] Review cloud, storage, secret-provider, database, and Procore provider permissions.
- [ ] Review the private release and deployment process, including separation of duties.
- [ ] Confirm private incident contacts, authority, escalation, and notification decisions.
- [ ] Confirm evidence custody, access, retention, and disposition procedures.
- [ ] Validate monitoring, recovery, backup, restore, and other operational controls privately.
- [ ] Record risk acceptance and approvals only in the authorized private system of record.

I8 does not perform these activities. It is offline, uses local public files, runs no live security
scanner, and makes no external or Procore call. It performs no deployment, release, or package
build. Completing this checklist does not itself grant production, pilot, hosted-pilot, release,
deployment, launch, legal, compliance, security-certification, or Procore approval.
