# Setup Troubleshooting Guide

## J2 demo-data troubleshooting

- Preview unexpected seed contents with `make demo-seed-plan`; planning does not write.
- Re-run `make demo-seed` safely: deterministic demo markers make seeding idempotent.
- Use `make demo-data-check` to verify fake-only, local-SQLite-only boundaries.
- Preview cleanup with `make demo-reset-plan`. Reset refuses a missing or inexact
  `RESET DEMO DATA` confirmation and refuses non-local databases.
- Never use reset for private workspace, Sandbox, Pilot, Hosted, cloud, external-database, or
  customer data; those scopes are intentionally untouched.

J2 makes no Procore call and grants no production, Pilot, release, deployment, or Procore
approval. `make try-demo` and `make first-run` remain non-destructive.

This Phase J1 guide covers local setup only. Its remedies do not contact Procore, cloud services,
or an external database, and they do not build, publish, release, or deploy anything.

## Git is missing

If `git --version` is not found, install Git using the trusted package manager for your operating
system, open a new terminal, and retry. Confirm the repository directory with `git status`.

## Python is missing or too old

Run `python3 --version`; this project requires Python 3.12 or newer. Install a supported Python,
open a new terminal, and recreate `.venv`. On systems where the launcher is named `python`, use
that name consistently.

## pip is missing

Use the selected interpreter rather than a standalone executable: `python3 -m pip --version`.
If that fails, repair the local Python installation using its official installer or operating
system package manager. Never paste registry credentials or tokens into setup files.

## Make is missing

Run `make --version`. Install Make using the trusted operating-system package manager. Until it
is available, do not guess at gated Sandbox, Pilot, or Hosted commands.

## A command is not on PATH

Close and reopen the terminal after installing a prerequisite. Check `command -v git`,
`command -v python3`, `command -v make`, and `python3 -m pip --version`. Update PATH only through
documented operating-system or toolchain configuration; never add a secret-bearing directory.

## Virtual environment or install problems

Confirm `.venv` is activated, then run `python -m pip --version`. The interpreter path should
belong to `.venv`. Retry the documented local dependency command from the repository root. Do not
run a package build, publish, Docker build, release, or deployment as a workaround.

## What to run next

After prerequisites work: first activate `.venv`, second run `make start`, and third run
`make try-demo`. Demo needs no credentials, cloud service, or external database. Use
`make doctor`, `make help`, and the [command reference](command-reference.md) for sanitized local
guidance. Sandbox, Pilot, and Hosted remain separate, private, gated paths.
