# Documentation site foundation

Phase E5 provides a local-only navigation foundation for the existing Markdown documentation.
The repository does not publish a documentation site, enable GitHub Pages, include deployment
automation, or require a site build for Demo, Sandbox, Pilot, testing, or release readiness.

## How the documentation is organized

The navigation follows a reader journey:

1. Start with the [Quickstart](quickstart-site.md), command reference, and troubleshooting.
2. [Choose a usage mode](usage-modes.md).
3. Follow the matching Demo, Sandbox, or Pilot walkthrough.
4. Use provider and infrastructure material only when preparing private environments.
5. Use operations material for controlled operator planning.
6. Use public-safety and release material before maintainers consider later manual publication.

The complete taxonomy and recommended reading order are in the
[documentation navigation map](docs-navigation.md). The root `QUICKSTART.md` remains canonical;
`quickstart-site.md` is only its navigation gateway.

## Validate locally

Run these non-writing, offline commands:

```bash
make docs-site-check
make docs-preview-instructions
make docs-map
```

The checker validates configuration, navigation targets, repository links, generated-output
rules, and public-safety boundaries. It does not run MkDocs or create `site/`.

## Optional local preview

If a maintainer has independently installed MkDocs, they may use its local development server
after reviewing `make docs-preview-instructions`. MkDocs is optional and not required for Demo Mode
or any repository check. E5 does not install it automatically and does not require a build artifact.

## Safety boundary

The docs site is not published by this repository. No GitHub Pages automation, hosting
configuration, analytics, tracking, external JavaScript, or active hosted URL is included.
Private customer data, credentials, contacts, IDs, domains, evidence, reports, paths,
certificates, keys, and generated output must stay outside documentation and Git.

Any future hosting or publication remains separately scoped, manually reviewed work.

The Sandbox navigation includes F2 read validation and evidence guidance. Documentation checks
never invoke the live command; they validate Markdown and navigation only.
