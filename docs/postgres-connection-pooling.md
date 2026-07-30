# PostgreSQL connection pooling

The pool settings are configuration guidance, not an external connectivity test. The offline
runtime report summarizes pool size, overflow, wait timeout, recycle interval, pre-ping,
connection timeout, statement timeout, and SSL requirement.

Defaults are deliberately modest: pool size 5, maximum overflow 5, pool wait 30 seconds, recycle
after 1800 seconds, pre-ping enabled, connection timeout 20 seconds, and statement timeout 10
seconds. A private operator must tune these against the managed database limits and application
concurrency. No database host, name, user, password, or URL appears in the summary.

SSL is required by default. A configuration summary is not evidence that transport controls,
capacity, failover, or production security have been validated.
