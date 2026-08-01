"""Prepared package version metadata; this does not indicate a published release."""

__version__ = "0.1.0"
VERSION = __version__


def get_version() -> str:
    """Return the version kept consistent with ``project.version`` in pyproject.toml."""
    return VERSION
