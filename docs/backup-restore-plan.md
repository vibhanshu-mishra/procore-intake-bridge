# Backup and restore plan

Run `make backup-restore-plan` for provider-neutral offline checklists. The planner does not locate,
read, create, restore, or inspect backup files or dumps. Pilot operators must privately identify
the backup service, retention, restore environment, recovery objectives, ownership, verification,
and rollback decision process.

Only masked evidence references belong in readiness or approval records. Backup filenames, paths,
contents, database hostnames, and provider logs stay outside the public repository.

G3 adds `make postgres-backup-restore-plan`. It does not contact a database, inspect dumps or
backup files, or restore anything. Managed-backup and restore-drill evidence references stay in
the private workspace; the public checklist grants no recovery or production approval.
