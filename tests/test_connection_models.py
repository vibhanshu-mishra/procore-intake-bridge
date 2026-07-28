from app.models.connections import DMSAConnection


def test_connection_creation_uses_secret_reference(client):
    response = client.post(
        "/connections",
        json={
            "name": "Fixture connection",
            "procore_company_id": "company-fixture",
            "environment": "sandbox",
            "permitted_project_ids": ["project-1001"],
            "enabled_tools": ["rfis", "submittals"],
            "secret_name": "secret/placeholder",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["secret_name"] == "secret/placeholder"
    assert "client_secret" not in payload


def test_model_has_no_plaintext_secret_column():
    columns = set(DMSAConnection.__table__.columns.keys())
    assert "secret_name" in columns
    assert "client_secret" not in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns
