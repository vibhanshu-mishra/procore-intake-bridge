# Deployment backup and rollback

D4 connects the D3 database recovery posture to deployment cutover planning. Backup and rollback
runbooks contain references and review prompts only; they do not create, locate, inspect, restore,
or delete backups.

Private operators must define recovery objectives, retention, restore verification, rollback
triggers, ownership, communications, and post-rollback checks. Backup files, dump paths, logs,
infrastructure state, and decisions stay outside the public repository.

# G4 hosted-template boundary

Hosted profiles reference backup and rollback placeholders only. They do not invoke provider
backup features, inspect archives, restore data, or perform rollback. Evidence and provider
configuration remain private.
