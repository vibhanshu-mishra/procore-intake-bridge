from app.services.security_gap_closeout import (
    build_security_gap_closeout_report,
    render_known_limitations_closeout_markdown,
)

from app.config import get_settings

if __name__ == "__main__":
    report = build_security_gap_closeout_report(get_settings())
    print(render_known_limitations_closeout_markdown(report), end="")
