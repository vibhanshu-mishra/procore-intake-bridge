#!/usr/bin/env python3
"""Print a conceptual webhook-ingress matrix without checking any service."""

import json


def main() -> int:
    rows = [
        {
            "style": style,
            "https_required": True,
            "private_setup_required": True,
            "public_url_checked": False,
            "dns_checked": False,
            "tls_checked": False,
            "webhook_registered": False,
        }
        for style in (
            "reverse_proxy",
            "managed_paas_ingress",
            "container_platform_ingress",
            "cloud_managed_ingress",
        )
    ]
    print(json.dumps({"ingress_styles": rows, "external_calls": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
