#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.config import get_settings
from app.schemas.deployment_recipes import DeploymentRecipeProfile
from app.services.deployment_recipes import (
    ABSOLUTE_PATH,
    BLOCKED_FILE,
    CERTIFICATE,
    DOMAIN,
    INFRA_ID,
    SECRET,
    URL,
    validate_deployment_recipe_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        if args.target.is_file():
            profile = DeploymentRecipeProfile.model_validate_json(args.target.read_text())
            unsafe = bool(validate_deployment_recipe_profile(profile, get_settings()))
        else:
            unsafe = any(
                pattern.search(path.read_text(errors="ignore"))
                for path in args.target.rglob("*") if path.is_file()
                for pattern in (
                    URL, DOMAIN, SECRET, CERTIFICATE, INFRA_ID,
                    ABSOLUTE_PATH, BLOCKED_FILE,
                )
            )
    except Exception:
        unsafe = True
    print(
        "Deployment safety check failed; details were suppressed."
        if unsafe else
        "Deployment safety check passed; no external calls or private values."
    )
    return 2 if unsafe else 0


if __name__ == "__main__":
    raise SystemExit(main())
