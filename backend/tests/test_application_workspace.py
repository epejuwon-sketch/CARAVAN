"""Test CARAVAN Application Preparation Workspace, Checklists & Documents."""

from fastapi.testclient import TestClient


def test_application_lifecycle_and_documents(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # 1. Get an opportunity
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    # 2. Create application workspace
    create_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"opportunity_id": opp_id, "notes": "Targeting Q2 submission cycle."},
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["application_id"]
    assert create_res.json()["status"] == "DRAFTING"
    assert len(create_res.json()["checklist_progress"]) >= 1

    # 3. List applications
    list_res = client.get("/api/v1/applications", headers=headers)
    assert list_res.status_code == 200
    apps = list_res.json()["applications"]
    assert any(a["application_id"] == app_id for a in apps)

    # 4. Update checklist progress & status
    checklist = [{"item": "Pitch Deck & Presentation", "completed": True}]
    update_res = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "DOCS_COLLECTING", "checklist_progress": checklist, "notes": "Deck finalized."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "DOCS_COLLECTING"
    assert update_res.json()["checklist_progress"][0]["completed"] is True

    # 5. Add document metadata
    doc_res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        json={"name": "Adeleke_AgriTech_Pitch_2026.pdf", "doc_type": "PITCH_DECK", "file_size_bytes": 4500000},
    )
    assert doc_res.status_code == 201
    assert "doc_id" in doc_res.json()
    assert doc_res.json()["doc_type"] == "PITCH_DECK"
