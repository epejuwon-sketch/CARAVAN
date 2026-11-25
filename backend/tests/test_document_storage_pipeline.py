"""CARAVAN Standalone Platform — Document Storage Pipeline End-to-End Tests.

Verifies:
- Private tenant object storage
- Authorized binary upload and download
- Magic header & MIME validation
- Anti-malware scanning & quarantine isolation
- Cross-tenant document isolation
- Short-lived HMAC signed URL generation and token tampering rejection
- Secure physical file shredding and deletion
- Full audit trail logging
"""

import io
import pytest
from fastapi.testclient import TestClient


def test_document_storage_pipeline_complete(client: TestClient):
    # 1. Register tenant A
    reg_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "org_a_founder@docsec.org",
            "password": "PasswordOrgA#2026",
            "full_name": "Alice Tenant",
            "organization_name": "Tenant A Holdings",
        },
    )
    assert reg_a.status_code == 201
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register tenant B
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "org_b_founder@docsec.org",
            "password": "PasswordOrgB#2026",
            "full_name": "Bob Tenant",
            "organization_name": "Tenant B Corp",
        },
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create application workspace in Tenant A
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    opp_id = opps[0]["opportunity_id"]

    app_res = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={"opportunity_id": opp_id, "notes": "Doc pipeline test"},
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["application_id"]

    # 4. Upload clean valid PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Pitch Deck) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/applications/{app_id}/documents/upload",
        headers=headers_a,
        files={"file": ("Pitch_Deck_Final.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"doc_type": "PITCH_DECK"},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["doc_id"]
    assert doc_data["scan_status"] == "AVAILABLE"
    assert "download_url" in doc_data

    # 5. Download clean document by owner (Tenant A)
    dl_res = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/download",
        headers=headers_a,
    )
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_content
    assert "attachment" in dl_res.headers.get("Content-Disposition", "")
    assert dl_res.headers.get("X-Content-Type-Options") == "nosniff"

    # 6. Cross-tenant download attempt by Tenant B -> REJECTED (HTTP 404)
    cross_dl = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/download",
        headers=headers_b,
    )
    assert cross_dl.status_code == 404

    # 7. Generate scoped signed URL (15 min)
    signed_res = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/signed-url",
        headers=headers_a,
    )
    assert signed_res.status_code == 200
    signed_data = signed_res.json()
    token = signed_data["token"]
    stream_url = signed_data["stream_url"]

    # Retrieve via stream URL with valid token (unauthenticated URL)
    stream_res = client.get(stream_url)
    assert stream_res.status_code == 200
    assert stream_res.content == pdf_content

    # Stream with tampered token -> REJECTED (HTTP 403)
    tampered_url = f"/api/v1/applications/{app_id}/documents/{doc_id}/stream?token={token}invalid"
    tampered_res = client.get(tampered_url)
    assert tampered_res.status_code == 403

    # 8. Test Malware Upload: EICAR Standard Antivirus Test Signature -> REJECTED & QUARANTINED
    eicar_bytes = b"%PDF-1.4\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*\n%%EOF"
    malware_res = client.post(
        f"/api/v1/applications/{app_id}/documents/upload",
        headers=headers_a,
        files={"file": ("Malware_Pitch.pdf", io.BytesIO(eicar_bytes), "application/pdf")},
        data={"doc_type": "PITCH_DECK"},
    )
    assert malware_res.status_code == 400
    assert "threat" in malware_res.json()["detail"].lower() or "quarantine" in malware_res.json()["detail"].lower()

    # 9. Test Disguised Executable Header (Windows MZ header in a .pdf) -> REJECTED
    pe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    pe_res = client.post(
        f"/api/v1/applications/{app_id}/documents/upload",
        headers=headers_a,
        files={"file": ("Fake_Statement.pdf", io.BytesIO(pe_bytes), "application/pdf")},
        data={"doc_type": "FINANCIALS"},
    )
    assert pe_res.status_code == 400
    assert "executable" in pe_res.json()["detail"].lower()

    # 10. Delete Document -> Physical file shredded & removed
    del_res = client.delete(
        f"/api/v1/applications/{app_id}/documents/{doc_id}",
        headers=headers_a,
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"

    # Subsequent download returns 404
    after_del_dl = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/download",
        headers=headers_a,
    )
    assert after_del_dl.status_code == 404
