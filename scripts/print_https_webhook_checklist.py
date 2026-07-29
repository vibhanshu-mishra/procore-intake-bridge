#!/usr/bin/env python3
from app.config import get_settings
from app.services.deployment_recipes import (
    build_default_deployment_recipe_template,
    build_deployment_recipe_readiness_report,
    render_https_tls_checklist,
    render_webhook_ingress_checklist,
)


def main() -> int:
    settings = get_settings()
    profile = build_default_deployment_recipe_template(
        settings.deployment_target, settings
    )
    report = build_deployment_recipe_readiness_report(profile, settings)
    print(render_https_tls_checklist(profile, report), end="")
    print(render_webhook_ingress_checklist(profile, report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
