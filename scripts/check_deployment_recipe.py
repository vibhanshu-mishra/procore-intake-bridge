#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.config import get_settings
from app.schemas.deployment_recipes import DeploymentRecipeProfile
from app.services.deployment_recipes import build_deployment_recipe_readiness_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe", type=Path)
    args = parser.parse_args()
    try:
        profile = DeploymentRecipeProfile.model_validate_json(args.recipe.read_text())
        report = build_deployment_recipe_readiness_report(profile, get_settings())
    except Exception:
        print("Deployment recipe validation blocked; details were suppressed.")
        return 2
    print(report.model_dump_json(indent=2))
    return 0 if report.status != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
