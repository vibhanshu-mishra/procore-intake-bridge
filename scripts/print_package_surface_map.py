from app.config import get_settings
from app.services.supply_chain_review import (
    build_supply_chain_review_report,
    render_package_surface_map_markdown,
)

if __name__ == "__main__":
    print(
        render_package_surface_map_markdown(build_supply_chain_review_report(get_settings())),
        end="",
    )
