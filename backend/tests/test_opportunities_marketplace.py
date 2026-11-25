"""Test CARAVAN Funding Opportunities Marketplace, 15 Categories & Filters."""

from fastapi.testclient import TestClient


def test_list_opportunities_and_categories(client: TestClient):
    # 1. Categories endpoint
    cat_res = client.get("/api/v1/opportunities/categories")
    assert cat_res.status_code == 200
    categories = cat_res.json()["categories"]
    assert len(categories) == 15
    category_ids = [c["id"] for c in categories]
    assert "GRANT" in category_ids
    assert "LOAN" in category_ids
    assert "VENTURE_CAPITAL" in category_ids
    assert "ANGEL_INVESTMENT" in category_ids
    assert "SEED_FUNDING" in category_ids
    assert "ACCELERATOR" in category_ids
    assert "WORKING_CAPITAL" in category_ids
    assert "RESEARCH_FUNDING" in category_ids
    assert "PHILANTHROPIC_FUNDING" in category_ids
    assert "SCHOLARSHIP" in category_ids

    # 2. List opportunities (seeded)
    res = client.get("/api/v1/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 10
    assert len(data["opportunities"]) >= 10

    # 3. Filter by category
    grant_res = client.get("/api/v1/opportunities?category=GRANT")
    assert grant_res.status_code == 200
    for opp in grant_res.json()["opportunities"]:
        assert opp["funding_type"] == "GRANT"

    # 4. Search by keyword
    search_res = client.get("/api/v1/opportunities?query=Tony+Elumelu")
    assert search_res.status_code == 200
    opps = search_res.json()["opportunities"]
    assert len(opps) >= 1
    assert "Tony Elumelu" in opps[0]["title"]

    # 5. Detail retrieval
    first_id = opps[0]["opportunity_id"]
    detail = client.get(f"/api/v1/opportunities/{first_id}")
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["opportunity_id"] == first_id
    assert "official_source_url" in detail_data
    assert detail_data["verification_status"] in {"VERIFIED", "VERIFIED_OPEN", "UPCOMING", "UPCOMING_CONFIRMED", "CLOSED"}

    # 6. Verify total count accuracy with pagination limit
    paged_res = client.get("/api/v1/opportunities?limit=1")
    assert paged_res.status_code == 200
    paged_data = paged_res.json()
    assert len(paged_data["opportunities"]) == 1
    assert paged_data["total"] >= 12
