import json
from pathlib import Path


def test_examples_are_fake_and_safe():
    markdown = Path(
        "examples/onboarding/example_gc_owner_packet.md"
    ).read_text()
    payload = json.loads(
        Path("examples/onboarding/example_gc_owner_packet.json").read_text()
    )
    combined = f"{markdown}\n{json.dumps(payload)}"
    assert "Example GC Company" in combined
    assert "Example Engineering Firm" in combined
    assert "111111" in combined and "222222" in combined
    assert "APP_VERSION_KEY_PLACEHOLDER" in combined
    assert "client_secret" not in combined.casefold()
    assert "access_token" not in combined.casefold()
