#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.schemas.deployment_recipes import DeploymentRecipeProfile
from app.services.deployment_recipes import write_deployment_recipe_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("deployment-output"))
    args = parser.parse_args()
    try:
        profile = DeploymentRecipeProfile.model_validate_json(args.recipe.read_text())
        result = write_deployment_recipe_artifacts(profile, args.output_root)
    except Exception:
        print("Deployment artifact generation blocked; details were suppressed.")
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
