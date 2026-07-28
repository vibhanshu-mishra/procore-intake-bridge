HTML_ROUTES = (
    "/admin",
    "/admin/connections",
    "/admin/sync-profiles",
    "/admin/sync-runs",
    "/admin/intake-records",
    "/admin/attachments",
    "/admin/webhook-events",
    "/admin/onboarding-packets",
    "/admin/safety",
)


def test_all_admin_html_routes_render_without_external_assets(client):
    for route in HTML_ROUTES:
        response = client.get(route)
        assert response.status_code == 200
        body = response.text.lower()
        assert "<script" not in body
        assert "cdn" not in body
        assert "http://" not in body
        assert "https://" not in body
        assert "no live procore calls" in body


def test_admin_html_has_empty_states(client):
    body = client.get("/admin").text
    assert "No connections yet" in body
    assert "No sync profiles yet" in body
    assert "No webhook events yet" in body


def test_admin_html_masks_seeded_values(client, connection, sync_profile):
    body = client.get("/admin/connections").text
    profile_body = client.get("/admin/sync-profiles").text
    combined = body + profile_body
    assert "com***est" in body
    assert "pro***001" in profile_body
    assert "Synthetic contractor" not in combined
    assert "Synthetic project polling" not in combined
    assert "secret/test-placeholder" not in combined
    assert "project-1001" not in combined
