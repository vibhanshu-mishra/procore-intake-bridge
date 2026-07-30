# Demo walkthrough

## Who this is for

Use this path if you just cloned the repository or want to understand it without a Procore
account. Demo needs no Procore credentials, no secrets, no external database, and no external
services.

## Prerequisites

- Python 3.12 or newer
- Git and Make
- A shell in the repository root

Create the local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run the walkthrough

```bash
make start
make try-demo
make doctor
make commands
make next
```

Expected safe behavior:

- `make start` explains the three separate paths.
- `make try-demo` checks fixture settings and performs a dry-run local poll.
- `make doctor` reports Demo as ready; missing Sandbox/Pilot configuration is informational.
- `make commands` lists friendly commands before advanced scripts.
- `make next` recommends Demo unless a mode is explicitly selected.

See the short [illustrative output](../examples/walkthrough-output/demo_expected_output.md).

## How to tell it passed

The local check says `ready`, the demo reports `dry_run` as true, and no command asks for a
credential. Empty fixture counts are valid. No live Procore client or external service is used.

## Common problems

- Command not found: activate `.venv` and reinstall the editable development dependencies.
- Import error: confirm the active Python belongs to `.venv`.
- Pending local migration: use the isolated migration safety checks described in
  [Troubleshooting](troubleshooting.md); do not connect to an external database.
- The known Starlette/httpx deprecation warning is non-blocking.

## Cleanup

The basic dry-run writes no generated report. Local SQLite, caches, or ignored output created by
other commands can be removed with normal local file tools after confirming they are ignored.
Never delete or force-add private data blindly.

## What to run next

Stay in Demo with `make doctor`, or read the optional
[Sandbox walkthrough](walkthrough-sandbox.md) or [Pilot walkthrough](walkthrough-pilot.md).
