#!/usr/bin/env python3
import argparse

from app.config import get_settings
from app.services.deployment_recipes import build_default_deployment_recipe_template


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="docker_local")
    args = parser.parse_args()
    print(build_default_deployment_recipe_template(
        args.target, get_settings()
    ).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
