def create(client, **overrides):
    payload = {"company": "Acme", "role": "Engineer", **overrides}
    return client.post("/applications", json=payload).json()


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_creates_an_application(client, sample_payload):
    response = client.post("/applications", json=sample_payload)

    assert response.status_code == 201
    assert response.json()["company"] == "Shopify"


def test_created_application_starts_at_saved(client, sample_payload):
    body = client.post("/applications", json=sample_payload).json()

    assert body["stage"] == "saved"


def test_rejects_an_empty_company(client):
    response = client.post("/applications", json={"company": "", "role": "Engineer"})

    assert response.status_code == 422


def test_rejects_an_inverted_salary_band(client):
    response = client.post(
        "/applications",
        json={"company": "A", "role": "B", "salary_min": 200, "salary_max": 100},
    )

    assert response.status_code == 422


def test_lists_created_applications(client):
    create(client)
    create(client, company="Shopify")

    response = client.get("/applications")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filters_list_by_company(client):
    create(client, company="Shopify")
    create(client, company="Acme")

    response = client.get("/applications", params={"company": "shop"})

    assert [a["company"] for a in response.json()] == ["Shopify"]


def test_rejects_an_out_of_range_limit(client):
    response = client.get("/applications", params={"limit": 9999})

    assert response.status_code == 422


def test_shows_a_single_application(client):
    created = create(client)

    response = client.get(f"/applications/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_returns_404_for_an_unknown_application(client):
    assert client.get("/applications/4242").status_code == 404


def test_patches_supplied_fields_only(client):
    created = create(client, location="Toronto")

    response = client.patch(
        f"/applications/{created['id']}", json={"role": "Staff Engineer"}
    )

    assert response.json()["role"] == "Staff Engineer"
    assert response.json()["location"] == "Toronto"


def test_patch_returns_404_for_unknown_application(client):
    assert client.patch("/applications/4242", json={"role": "X"}).status_code == 404


def test_moves_an_application_to_a_new_stage(client):
    created = create(client)

    response = client.post(
        f"/applications/{created['id']}/stage",
        json={"to_stage": "applied", "note": "Submitted"},
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "applied"


def test_stage_change_is_recorded_in_history(client):
    created = create(client)
    client.post(f"/applications/{created['id']}/stage", json={"to_stage": "applied"})

    events = client.get(f"/applications/{created['id']}").json()["events"]

    assert [e["to_stage"] for e in events] == ["saved", "applied"]


def test_conflicting_stage_change_returns_409(client):
    created = create(client)

    response = client.post(
        f"/applications/{created['id']}/stage", json={"to_stage": "saved"}
    )

    assert response.status_code == 409


def test_moving_out_of_a_terminal_stage_returns_409(client):
    created = create(client)
    client.post(f"/applications/{created['id']}/stage", json={"to_stage": "rejected"})

    response = client.post(
        f"/applications/{created['id']}/stage", json={"to_stage": "applied"}
    )

    assert response.status_code == 409


def test_deletes_an_application(client):
    created = create(client)

    assert client.delete(f"/applications/{created['id']}").status_code == 204
    assert client.get(f"/applications/{created['id']}").status_code == 404


def test_delete_returns_404_for_unknown_application(client):
    assert client.delete("/applications/4242").status_code == 404


def test_stats_reports_the_funnel(client):
    created = create(client)
    client.post(f"/applications/{created['id']}/stage", json={"to_stage": "applied"})

    body = client.get("/stats").json()

    assert body["total"] == 1
    assert body["active"] == 1
    assert body["by_stage"]["applied"] == 1


def test_stats_response_rate_is_a_fraction(client):
    body = client.get("/stats").json()

    assert 0.0 <= body["response_rate"] <= 1.0
