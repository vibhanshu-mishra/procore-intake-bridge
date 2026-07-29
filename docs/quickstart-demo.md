# Demo mode quickstart

Demo mode requires no Procore credentials, no secrets, no cloud, no external database, and no
external services. It uses committed synthetic fixtures and local SQLite state.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
make setup-demo
make check-local
make demo
```

`make demo` is a dry-run fixture sync. It does not call Procore. Local database and generated
output files are ignored. Demo readiness does not mean production readiness.

Demo mode does not need or read the C5 private workspace.
