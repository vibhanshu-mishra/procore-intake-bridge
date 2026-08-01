import argparse

from app.config import get_settings
from app.database import make_engine
from app.services.demo_data_experience import (
    build_demo_data_inventory,
    render_demo_data_inventory_csv,
)

parser = argparse.ArgumentParser()
parser.add_argument("--database-url")
args = parser.parse_args()
settings = get_settings()
inventory = build_demo_data_inventory(
    make_engine(args.database_url or settings.database_url), settings
)
print(render_demo_data_inventory_csv(inventory), end="")
