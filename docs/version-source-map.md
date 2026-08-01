# Version Source Map

The prepared target version is `0.1.0`. The canonical source is the repository's version source as
identified by the J6 local review, with `pyproject.toml` package metadata kept consistent. README,
QUICKSTART, changelog, project status, and readiness guides describe the target; they do not own it.

| Surface | Responsibility |
| --- | --- |
| Canonical application/package version source | Own the prepared target version |
| `pyproject.toml` | Declare consistent package metadata |
| `CHANGELOG.md` | Record the target as prepared/unreleased metadata |
| Project status and roadmap | Explain current preparation scope |
| Release readiness | Define later human review and release boundaries |
| Generated J6 report | Inspect consistency only; never become a version source |

Do not infer a tag, release, package, image, publication, deployment, or approval from a matching
version string. J6 performs none of those operations and adds no workflow automation.
