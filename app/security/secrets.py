"""Compatibility exports for the Phase A1 secret module."""

from app.security.secret_provider import SecretNotFoundError, SecretProvider

__all__ = ["SecretNotFoundError", "SecretProvider"]
