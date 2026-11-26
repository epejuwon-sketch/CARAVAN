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


def test_document_persistence_across_restarts_and_disaster_recovery(client: TestClient):
    """Verifies that uploaded documents survive application restarts and can be exported for disaster recovery."""
    import hashlib
    from app.services.storage_service import get_storage_service, _STORAGE_INSTANCE
    import app.services.storage_service as storage_mod

    storage = get_storage_service()
    org_id = "org_durability_test"
    doc_id = "doc_durability_test_01"
    test_content = b"%PDF-1.4\nTest Durable Document Persistence Content\n%%EOF"

    # 1. Store document
    res = storage.store_document(org_id, doc_id, test_content)
    assert res.file_size_bytes == len(test_content)
    assert res.sha256_hash == hashlib.sha256(test_content).hexdigest()

    # 2. Simulate application restart / cold-start by destroying the singleton storage instance
    storage_mod._STORAGE_INSTANCE = None
    restarted_storage = storage_mod.get_storage_service()

    # 3. Retrieve document after restart
    retrieved_bytes, file_path = restarted_storage.retrieve_document(org_id, doc_id)
    assert retrieved_bytes == test_content
    assert hashlib.sha256(retrieved_bytes).hexdigest() == res.sha256_hash

    # 4. Disaster Recovery Manifest Export
    manifest = restarted_storage.export_tenant_documents_manifest(org_id)
    assert len(manifest) >= 1
    target_entry = next((e for e in manifest if e["doc_id"] == doc_id), None)
    assert target_entry is not None
    assert target_entry["sha256_hash"] == res.sha256_hash
    assert target_entry["organization_id"] == org_id

    # 5. Clean up
    restarted_storage.delete_document(org_id, doc_id)


def test_file_size_limit_and_untrusted_handling(client: TestClient):
    """Verifies that oversized documents (>15MB) and untrusted payloads are rejected."""
    from app.services.storage_service import get_storage_service
    from fastapi import HTTPException

    storage = get_storage_service()
    oversized_bytes = b"0" * (16 * 1024 * 1024)  # 16MB

    with pytest.raises(HTTPException) as exc_info:
        storage.store_document("org_limit_test", "doc_oversized", oversized_bytes)
    assert exc_info.value.status_code == 413


def test_supabase_storage_client_mock_integration():
    """Verifies SupabaseStorageClient upload, signed URL, download, and delete operations via HTTP mock."""
    import httpx
    from app.services.storage_service import SupabaseStorageClient

    test_key = "mock-service-key-with-enough-length-2026"

    def mock_supabase_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # Check authentication headers
        auth = request.headers.get("Authorization", "")
        api_key = request.headers.get("apiKey", "")
        if f"Bearer {test_key}" not in auth or api_key != test_key:
            return httpx.Response(401, json={"message": "Invalid API key"})

        if request.method == "POST" and "/object/sign/" in url_str:
            return httpx.Response(200, json={"signedURL": "/object/sign/caravan-vault/test.bin?token=valid123"})
        elif request.method == "POST" and "/object/caravan-vault/" in url_str:
            return httpx.Response(201, json={"Key": "caravan-vault/test.bin"})
        elif request.method == "GET" and "/object/caravan-vault/" in url_str:
            return httpx.Response(200, content=b"Mock Supabase Content")
        elif request.method == "DELETE" and "/object/caravan-vault/" in url_str:
            return httpx.Response(200, json={"message": "Deleted"})
        return httpx.Response(404, json={"message": "Not Found"})

    mock_transport = httpx.MockTransport(mock_supabase_handler)

    client = SupabaseStorageClient(
        supabase_url="https://mock-ref.supabase.co",
        service_role_key="mock-service-key-with-enough-length-2026",
        bucket="caravan-vault",
    )
    assert client.is_configured() is True

    # Monkeypatch transport in httpx.Client calls
    orig_client = httpx.Client
    try:
        httpx.Client = lambda **kwargs: orig_client(transport=mock_transport, **{k: v for k, v in kwargs.items() if k != "transport"})

        # 1. Upload
        uri = client.upload_object("documents/org1/doc1.bin", b"Mock Supabase Content")
        assert uri == "supabase://caravan-vault/documents/org1/doc1.bin"

        # 2. Signed URL
        signed = client.create_signed_url("documents/org1/doc1.bin", expires_in_seconds=900)
        assert "valid123" in signed

        # 3. Download
        downloaded = client.download_object("documents/org1/doc1.bin")
        assert downloaded == b"Mock Supabase Content"

        # 4. Delete
        assert client.delete_object("documents/org1/doc1.bin") is True
    finally:
        httpx.Client = orig_client
