#!/usr/bin/env python3
"""Print local-only documentation preview guidance."""

print(
    """Documentation preview — local only
==================================

1. Run `make docs-site-check`.
2. MkDocs is optional and may need to be installed separately by the maintainer.
3. If MkDocs is already available, run `mkdocs serve` from the repository root.
4. Stop the local development server when review is complete.

This repository does not install MkDocs automatically, build a required site artifact, publish
documentation, deploy hosting, or enable GitHub Pages. The preview is not required for Demo Mode.
"""
)
