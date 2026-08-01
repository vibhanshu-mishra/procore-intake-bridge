from app.config import get_settings
from app.services.demo_data_experience import (
    build_demo_seed_plan,
    render_demo_seed_plan_markdown,
)

if __name__ == "__main__":
    print(render_demo_seed_plan_markdown(build_demo_seed_plan(get_settings())), end="")
