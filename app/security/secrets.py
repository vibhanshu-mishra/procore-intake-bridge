class SecretResolutionDisabled(RuntimeError):
    """Raised because Phase A1 deliberately does not resolve production secrets."""


def resolve_connection_secret(_secret_name: str) -> str:
    raise SecretResolutionDisabled(
        "Secret resolution is disabled in Phase A1; use fixture mode only."
    )
