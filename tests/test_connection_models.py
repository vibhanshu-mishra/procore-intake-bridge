from app.models.connections import DMSAConnection


def test_connection_creation_uses_secret_reference(client):
    raw_client_id = "client-id-must-not-be-returned"
    raw_secret = "client-secret-must-not-be-returned"
    response = client.post(
        "/connections",
        json={
            "name": "Fixture connection",
            "procore_company_id": "company-fixture",
            "environment": "sandbox",
            "permitted_project_ids": ["project-1001"],
            "enabled_tools": ["rfis", "submittals"],
            "client_id_ref": "demo_client_id",
            "secret_name": "secret/placeholder",
            "client_id": raw_client_id,
            "client_secret": raw_secret,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["secret_name"] != "secret/placeholder"
    assert payload["client_id_ref"] != "demo_client_id"
    assert "****" in payload["secret_name"]
    assert "****" in payload["client_id_ref"]
    assert "client_secret" not in payload
    serialized = response.text
    assert raw_client_id not in serialized
    assert raw_secret not in serialized


def test_model_has_no_plaintext_secret_column():
    columns = set(DMSAConnection.__table__.columns.keys())
    assert "secret_name" in columns
    assert "client_id_ref" in columns
    assert "client_id" not in columns
    assert "client_secret" not in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns
