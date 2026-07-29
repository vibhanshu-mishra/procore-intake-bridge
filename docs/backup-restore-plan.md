# Backup and restore plan

Run `make backup-restore-plan` for provider-neutral offline checklists. The planner does not locate,
read, create, restore, or inspect backup files or dumps. Pilot operators must privately identify
the backup service, retention, restore environment, recovery objectives, ownership, verification,
and rollback decision process.

Only masked evidence references belong in readiness or approval records. Backup filenames, paths,
contents, database hostnames, and provider logs stay outside the public repository.
