from app.config import get_settings
from app.services.security_gap_closeout import (
    build_security_gap_closeout_report,
    render_private_security_action_register_markdown,
)

if __name__ == "__main__":
    report = build_security_gap_closeout_report(get_settings())
    print(render_private_security_action_register_markdown(report), end="")
