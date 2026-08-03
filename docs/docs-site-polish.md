# Documentation Site Polish

## J8 relationship

J8 links the versioned release handoff into this local handbook. The target `0.1.0` is prepared
metadata only. No docs build, docs publication, docs deployment, package/Docker build, publish,
upload, tag, release, application deployment, external call, or workflow change occurs. A
maintainer must authorize any later release; documentation polish grants no hosting, production,
Pilot, release, or deployment approval.

J7 consumes the J5 local navigation audit as one release-candidate gate. It does not publish or
deploy documentation, add a workflow, or imply that prepared `0.1.0` has been released or approved.

J6 joins the Release and Maintenance reader path through four metadata-preparation pages. J5 keeps
navigation ownership here while version values remain owned by the canonical version source and
commands remain owned by the command reference. No build, publication, tag, release, deployment,
workflow, or approval is introduced.

Phase J5 organizes the repository documentation as a coherent local product handbook. It improves
the landing page, reader paths, navigation map, and safety checks without publishing or hosting the
site. This work is local-only: no docs deployment is performed.

J5 adds no GitHub Pages workflow, hosting automation, external documentation service, analytics,
tracking, search service, JavaScript, font, theme, or CDN asset. It runs no external call, package
build, release, or deployment.

## Read the handbook locally

Start with [reader paths](docs-reader-paths.md), then use the
[navigation map](docs-navigation-map.md) to move between setup, product, API, operations, hosted,
security, and release guidance. The existing [command reference](command-reference.md) remains the
single owner of executable command guidance.

To preview the MkDocs site locally, install the repository's local development dependencies in the
documented virtual environment, then run:

```bash
make docs-serve
```

Open only the loopback address printed by the local preview process and stop it when finished. A
preview is optional; the Markdown files remain directly readable without building or deploying a
site. Do not use external preview, analytics, tracking, search, or CDN services.

Generated review artifacts belong only in ignored output roots. Documentation polish is not
production approval, Pilot approval, release approval, deployment approval, docs-hosting approval,
certification, compliance, or Procore approval.
