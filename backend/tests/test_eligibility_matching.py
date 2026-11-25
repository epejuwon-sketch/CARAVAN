"""Test CARAVAN Eligibility Matching Engine & Recommendations."""

from fastapi.testclient import TestClient


def test_eligibility_assessment_and_recommendations(client: TestClient, registered_customer: dict):
    headers = registered_customer["headers"]

    # Retrieve an opportunity to assess
    opps = client.get("/api/v1/opportunities").json()["opportunities"]
    first_opp_id = opps[0]["opportunity_id"]

    # Assess single opportunity
    assess_res = client.post(f"/api/v1/eligibility/assess/{first_opp_id}", headers=headers)
    assert assess_res.status_code == 200
    data = assess_res.json()
    assert "match_score" in data
    assert 0.0 <= data["match_score"] <= 100.0
    assert data["recommendation_level"] in ("STRONG", "MODERATE", "WEAK", "INELIGIBLE")
    assert "criteria_breakdown" in data
    assert "geography" in data["criteria_breakdown"]
    assert "sector" in data["criteria_breakdown"]

    # Recommendations for organization
    rec_res = client.get("/api/v1/eligibility/recommendations", headers=headers)
    assert rec_res.status_code == 200
    recs = rec_res.json()["recommendations"]
    assert len(recs) >= 5
    # Verify sorted descending by match_score
    scores = [r["match_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
