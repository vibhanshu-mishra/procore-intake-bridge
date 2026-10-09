#!/usr/bin/env python3

from app.config import get_settings
from app.services.deployment_readiness import build_sanitized_config_summary

if __name__ == "__main__":
    _summary = build_sanitized_config_summary(get_settings())
    print("Configuration summary generated successfully.")
