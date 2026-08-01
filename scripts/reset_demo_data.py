import argparse

from app.config import get_settings
from app.database import make_engine
from app.services.demo_data_experience import reset_demo_data

parser = argparse.ArgumentParser()
parser.add_argument("--confirm", required=True)
parser.add_argument("--database-url")
args = parser.parse_args()
settings = get_settings()
report = reset_demo_data(
    make_engine(args.database_url or settings.database_url), settings, args.confirm
)
print(report.model_dump_json(indent=2))
