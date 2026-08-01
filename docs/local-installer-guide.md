# Local Installer Guide

Phase J1 improves the local setup experience for maintainers. It does not install a cloud
service, build or publish a package or image, create a release, deploy the application, or imply
production, Pilot, release, or Procore approval.

## Prerequisites

Install Git, Python 3.12 or newer, pip, and Make using your operating system's trusted package
manager. Confirm they are discoverable before cloning:

```bash
git --version
python3 --version
python3 -m pip --version
make --version
```

If a command is missing, use the [setup troubleshooting guide](setup-troubleshooting-guide.md).
Do not place credentials, tokens, database URLs, or private reports in the repository.

## Run these three commands in order

From the repository root after cloning:

```bash
# First: create the isolated local environment
python3 -m venv .venv

# Second: activate it (Windows PowerShell: .venv\Scripts\Activate.ps1)
source .venv/bin/activate

# Third: install local development dependencies
python -m pip install -e ".[dev]"
```

Then run `make start`. Follow its next-command guidance and run `make try-demo` for the safe,
fixture-only Demo path. `make quality` performs the full local developer check.

## Demo safety boundary

Demo Mode uses local synthetic fixtures and local SQLite. It requires no Procore credentials,
other secrets, cloud services, or external database. Setup performs no Procore, cloud, external
database, package-registry, deployment, release, or publishing operation. Generated setup
artifacts belong only in ignored output directories.

## Separate gated paths

- **Sandbox:** optional, private, credentialed, and manually gated; begin with its private guide
  only after Demo.
- **Pilot:** optional, private, evidence-backed, and manually reviewed; setup does not approve it.
- **Hosted:** optional private planning that requires separate infrastructure and security review;
  J1 does not provision or deploy it.

Continue with the [first-run checklist](first-run-checklist.md), then consult the
[setup experience review](setup-experience-review.md).
