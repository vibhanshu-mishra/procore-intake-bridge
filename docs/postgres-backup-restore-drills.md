# PostgreSQL backup and restore drills

`make postgres-backup-restore-plan` is an offline planning command. It does not contact a database,
invoke a backup service, inspect dump or backup files, read backup names, or perform a restore.

Managed-backup and restore-drill evidence references remain private. Operators should validate
retention and recovery objectives with the database owner, conduct restores only in an approved
isolated environment, verify application and migration posture, and retain sanitized evidence.
Raw logs, archives, filenames, contents, and private paths must not enter the public repository.

The plan connects D3 database readiness to D4 backup and rollback planning. It is not proof of a
successful restore and grants no production or Pilot approval.
