# Deployment backup and rollback

D4 connects the D3 database recovery posture to deployment cutover planning. Backup and rollback
runbooks contain references and review prompts only; they do not create, locate, inspect, restore,
or delete backups.

Private operators must define recovery objectives, retention, restore verification, rollback
triggers, ownership, communications, and post-rollback checks. Backup files, dump paths, logs,
infrastructure state, and decisions stay outside the public repository.
