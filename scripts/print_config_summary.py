#!/usr/bin/env python3
import json

from app.config import get_settings
from app.services.deployment_readiness import build_sanitized_config_summary

if __name__ == "__main__":
    print(json.dumps(build_sanitized_config_summary(get_settings()), indent=2))
