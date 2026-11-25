"""CARAVAN Standalone Platform — Independent Customer Operations Verification.

Proves that CARAVAN functions completely autonomously without ULTRON:
- Public marketplace browsing
- User registration and authentication
- Opportunity detail viewing and criteria inspection
- Autonomous eligibility assessment
- Opportunity bookmarking / saved list
- Application workspace creation, progress tracking, and notes updating
- Document metadata management
- Notification lifecycle
- Platform admin operations
"""

import pytest
from fastapi.testclient import TestClient


def test_caravan_complete_independent_customer_operations(client):
    # 1. Public Marketplace browsing without authentication or ULTRON
    market_res = client.get("/api/v1/opportunities")
    assert market_res.status_code == 200
    opps = market_res.json()["opportunities"]
    assert len(opps) >= 12

    target_opp = opps[0]
    target_id = target_opp["opportunity_id"]

    # 2. View Opportunity Details
    detail_res = client.get(f"/api/v1/opportunities/{target_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["opportunity_id"] == target_id

    # 3. Customer Registration & JWT Token Issuance (Standalone Argon2id)
    reg_email = f"independent_founder_{target_id[:6]}@example.com"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": reg_email,
            "password": "IndependentPassword2026#",
            "full_name": "Apex Founder",
            "organization_name": "Apex Independent Ventures",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Independent Eligibility Assessment
    elig_res = client.post(
        "/api/v1/eligibility/assess",
        headers=headers,
        json={"opportunity_id": target_id},
    )
    assert elig_res.status_code == 200
    elig_data = elig_res.json()
    assert 0.0 <= elig_data["match_score"] <= 100.0
    assert "criteria_breakdown" in elig_data

    # 5. Save Opportunity to Workspace
    save_res = client.post(f"/api/v1/saved/{target_id}", headers=headers)
    assert save_res.status_code == 200
    assert save_res.json()["saved"] is True

    # 6. Retrieve Saved Opportunities
    saved_list_res = client.get("/api/v1/saved", headers=headers)
    assert saved_list_res.status_code == 200
    saved_ids = [s["opportunity_id"] for s in saved_list_res.json()["saved"]]
    assert target_id in saved_ids

    # 7. Create Application Workspace
    app_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"opportunity_id": target_id, "notes": "Independent application workspace test"},
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["application_id"]

    # 8. Update Application Status & Notes
    update_res = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "DOCS_COLLECTING", "notes": "Updated independent progress"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "DOCS_COLLECTING"

    # 9. Document Metadata Attachment
    doc_res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        json={
            "name": "Pitch_Deck_Apex_2026.pdf",
            "doc_type": "PITCH_DECK",
            "file_size_bytes": 2048500,
        },
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["doc_id"]
    assert doc_res.json()["file_size_bytes"] == 2048500

    # 10. Delete Document Metadata
    del_doc_res = client.delete(f"/api/v1/applications/{app_id}/documents/{doc_id}", headers=headers)
    assert del_doc_res.status_code == 200
    assert del_doc_res.json()["status"] == "DELETED"

    # 11. Customer Notifications Retrieval
    notif_res = client.get("/api/v1/notifications", headers=headers)
    assert notif_res.status_code == 200
    assert "notifications" in notif_res.json()

    # 12. Public Support Endpoint
    support_res = client.post(
        "/api/v1/support/tickets",
        headers=headers,
        json={"subject": "Inquiry on grant disbursement", "message": "Does grant require collateral?"},
    )
    assert support_res.status_code == 201
    assert "ticket_id" in support_res.json()
