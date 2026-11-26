"""Live Production Verification for AURELIA Funding Intelligence and Complete Customer Journey."""

import sys
import time
import requests

BASE_URL = "https://caravan-juwon2.vercel.app"

def main():
    print(f"--- 1. Health & AI Status on {BASE_URL} ---")
    h_res = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"Health Status: {h_res.status_code} -> {h_res.json()}")
    assert h_res.status_code == 200
    assert h_res.json()["database"] == "connected"
    assert h_res.json()["storage_mode"] == "primary_postgres"

    ai_res = requests.get(f"{BASE_URL}/api/v1/copilot/ai-status", timeout=15)
    print(f"AI Status: {ai_res.status_code} -> {ai_res.json().get('active_provider')} / {ai_res.json().get('active_model')}")
    assert ai_res.status_code == 200

    print("\n--- 2. Customer Registration & Authentication ---")
    email = f"aurelia_founder_{int(time.time())}@caravan-demo.africa"
    reg_payload = {
        "email": email,
        "password": "AureliaPassword2026!",
        "full_name": "Hadiza Danjuma",
        "organization_name": "Savannah Harvest Technologies",
        "entity_type": "STARTUP",
        "country": "Nigeria",
        "state_location": "Kano",
        "sector": "Agriculture & AgTech",
        "stage": "GROWTH",
    }
    reg_res = requests.post(f"{BASE_URL}/api/v1/auth/register", json=reg_payload, timeout=10)
    print(f"Registration: {reg_res.status_code}")
    assert reg_res.status_code in (200, 201), reg_res.text
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 3. Fetch Institutional Opportunity ---")
    opp_res = requests.get(f"{BASE_URL}/api/v1/opportunities", timeout=10)
    assert opp_res.status_code == 200
    opps = opp_res.json()["opportunities"]
    assert len(opps) > 0
    opp = opps[0]
    opp_id = opp["opportunity_id"]
    print(f"Target Opportunity: {opp['title']} (ID: {opp_id})")

    print("\n--- 4. Verify 8-Stage AURELIA Customer Journey Endpoint ---")
    journey_res = requests.get(f"{BASE_URL}/api/v1/copilot/journey/{opp_id}", headers=headers, timeout=10)
    print(f"Journey Endpoint: {journey_res.status_code}")
    assert journey_res.status_code == 200, journey_res.text
    journey_data = journey_res.json()
    print(f"Assistant Name: {journey_data.get('assistant_name')}")
    print(f"Descriptor: {journey_data.get('descriptor')}")
    print(f"Positioning: {journey_data.get('positioning')}")
    print(f"Current Stage: {journey_data.get('current_stage')}")
    print(f"AURELIA Guidance: {journey_data.get('aurelia_guidance')}")
    
    stages = [s["stage_id"] for s in journey_data.get("stages", [])]
    print(f"Stages in Journey: {' -> '.join(stages)}")
    assert stages == ["DISCOVER", "MATCH", "UNDERSTAND", "PREPARE", "REVIEW", "APPROVE", "SUBMIT", "TRACK"]
    assert journey_data.get("assistant_name") == "AURELIA"
    assert journey_data.get("descriptor") == "Funding Intelligence"

    print("\n--- 5. Update Missing Business Profile Details via AURELIA ---")
    update_res = requests.post(
        f"{BASE_URL}/api/v1/copilot/journey/{opp_id}/update-profile",
        headers=headers,
        json={
            "fields": {
                "target_customers": "Northern Nigeria grain farmers & food processors",
                "products_services": "Decentralized grain silo telemetry & pest monitoring",
                "business_model": "SaaS and equipment financing",
                "annual_revenue_ngn": 78000000.0,
                "cac_registered": True,
                "cac_registration_number": "RC-7654321",
            }
        },
        timeout=10,
    )
    print(f"Update Missing Details: {update_res.status_code} -> {update_res.json().get('status')}")
    assert update_res.status_code == 200

    print("\n--- 6. Execute Application Agent Drafting (PREPARE) ---")
    draft_res = requests.post(
        f"{BASE_URL}/api/v1/copilot/application-agent/draft",
        headers=headers,
        json={"opportunity_id": opp_id},
        timeout=15,
    )
    print(f"Draft Response: {draft_res.status_code}")
    assert draft_res.status_code in (200, 201), draft_res.text
    draft_data = draft_res.json()
    app_id = draft_data.get("application_id")
    print(f"Created Application ID: {app_id}, Draft Status: {draft_data.get('status')}")

    print("\n--- 7. Re-check Journey at PREPARE/REVIEW Stage ---")
    journey_stage_res = requests.get(f"{BASE_URL}/api/v1/copilot/journey/{opp_id}?application_id={app_id}", headers=headers, timeout=10)
    assert journey_stage_res.status_code == 200
    j2 = journey_stage_res.json()
    print(f"Progressed Stage: {j2.get('current_stage')}")
    print(f"AURELIA Guidance: {j2.get('aurelia_guidance')}")

    print("\n--- 8. Live Chat Consultation with AURELIA ---")
    sess_res = requests.post(f"{BASE_URL}/api/v1/copilot/sessions", headers=headers, json={"title": "AgriTech Strategy", "context_mode": "GENERAL"}, timeout=10)
    sess_id = sess_res.json()["session_id"]
    print(f"Created Session ID: {sess_id}")

    chat_res = requests.post(
        f"{BASE_URL}/api/v1/copilot/sessions/{sess_id}/chat",
        headers=headers,
        json={"message": "Hello AURELIA, explain our 8-stage funding journey and recommend next steps for our grain tech business."},
        timeout=25,
    )
    print(f"Chat Status: {chat_res.status_code}")
    assert chat_res.status_code == 200, chat_res.text
    chat_data = chat_res.json()
    print(f"Provider Used: {chat_data.get('provider_used')}")
    print(f"Content Preview:\n{chat_data.get('content')[:350]}...\n")
    print(f"Citations count: {len(chat_data.get('citations', []))}")
    print(f"Actions count: {len(chat_data.get('actions', []))}")

    print("\n=======================================================")
    print(" ALL PRODUCTION AURELIA VERIFICATION CHECKS PASSED 100% ")
    print("=======================================================")

if __name__ == "__main__":
    main()
