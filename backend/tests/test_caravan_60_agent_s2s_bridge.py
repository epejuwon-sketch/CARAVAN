"""CARAVAN Standalone Platform — 60-Agent S2S Bridge Verification Suite.

Validates:
1. S2S Authentication (X-Ultron-Bridge-Key)
2. Agent Identity Enforcement (X-Agent-ID, Correlation IDs, Task IDs)
3. Strict Least-Privilege Scoping & Boundary Violation Rejection (403)
4. Domain Coverage Across All 12 Functional Domains
5. Comprehensive Test of All 60 Specialist Agents (AGT-01 to AGT-60)
6. Immutable Audit Trail Logging
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import AuditLogRecord
from app.services.bridge_service import AGENT_SCOPE_MAP, PERMITTED_SCOPE_OPERATIONS

BRIDGE_KEY = "test-ultron-s2s-bridge-key"


def test_bridge_authentication_enforcement(client: TestClient):
    """Test S2S bridge rejects missing or invalid bridge keys."""
    # 1. Missing bridge key -> 401
    res = client.post(
        "/api/v1/bridge/agent-action",
        json={"operation": "get_operations_summary", "agent_id": "AGT-01"},
    )
    assert res.status_code == 401

    # 2. Invalid bridge key -> 401
    res = client.post(
        "/api/v1/bridge/agent-action",
        headers={"X-Ultron-Bridge-Key": "invalid-tampered-key"},
        json={"operation": "get_operations_summary", "agent_id": "AGT-01"},
    )
    assert res.status_code == 401


def test_bridge_agent_id_required(client: TestClient):
    """Test bridge requires agent identification."""
    res = client.post(
        "/api/v1/bridge/agent-action",
        headers={"X-Ultron-Bridge-Key": BRIDGE_KEY},
        json={"operation": "get_operations_summary"},
    )
    assert res.status_code == 400
    assert "agent identifier" in res.json()["detail"].lower()


def test_bridge_least_privilege_scope_enforcement(client: TestClient):
    """Test that agents cannot probe or execute operations outside their designated domain."""
    headers = {
        "X-Ultron-Bridge-Key": BRIDGE_KEY,
        "X-Agent-ID": "AGT-02",  # AGT-02 is Research (caravan:research)
        "X-Correlation-ID": "test-corr-priv-01",
    }

    # AGT-02 attempting financial transaction inspection -> 403 Forbidden
    res = client.post(
        "/api/v1/bridge/agent-action",
        headers=headers,
        json={"operation": "get_revenue_metrics", "scope": "caravan:finance"},
    )
    assert res.status_code == 403
    assert "cannot access scope" in res.json()["detail"]

    # AGT-02 attempting security audit log export -> 403 Forbidden
    res2 = client.post(
        "/api/v1/bridge/agent-action",
        headers=headers,
        json={"operation": "get_security_events", "scope": "caravan:security"},
    )
    assert res2.status_code == 403

    # AGT-08 (Finance) attempting engineering system backup -> 403 Forbidden
    headers_fin = {
        "X-Ultron-Bridge-Key": BRIDGE_KEY,
        "X-Agent-ID": "AGT-08",
        "X-Correlation-ID": "test-corr-priv-02",
    }
    res3 = client.post(
        "/api/v1/bridge/agent-action",
        headers=headers_fin,
        json={"operation": "get_system_health", "scope": "caravan:engineering"},
    )
    assert res3.status_code == 403


def test_all_12_functional_domains_executed(client: TestClient):
    """Verify sample agent execution across all 12 domains."""
    domain_samples = [
        ("AGT-01", "caravan:operations", "executive_operations_synthesis", {}),
        ("AGT-02", "caravan:research", "search_opportunities", {"query": "tech"}),
        ("AGT-03", "caravan:engineering", "probe_service_health", {}),
        ("AGT-06", "caravan:marketing", "get_marketing_audience", {}),
        ("AGT-07", "caravan:sales", "get_customer_pipeline", {}),
        ("AGT-08", "caravan:finance", "get_revenue_telemetry", {}),
        ("AGT-10", "caravan:legal", "compliance_calendar", {}),
        ("AGT-11", "caravan:analytics", "get_platform_metrics", {}),
        ("AGT-12", "caravan:product", "product_feature_backlog", {}),
        ("AGT-15", "caravan:funding", "get_application_pipeline", {}),
        ("AGT-16", "caravan:support", "list_support_tickets", {}),
        ("AGT-20", "caravan:security", "audit_security_logs", {}),
    ]

    for agent_id, expected_scope, operation, params in domain_samples:
        headers = {
            "X-Ultron-Bridge-Key": BRIDGE_KEY,
            "X-Agent-ID": agent_id,
            "X-Correlation-ID": f"corr-sample-{agent_id}",
            "X-Task-ID": f"task-sample-{agent_id}",
        }
        res = client.post(
            "/api/v1/bridge/agent-action",
            headers=headers,
            json={"operation": operation, "parameters": params},
        )
        assert res.status_code == 200, f"Domain test failed for {agent_id} ({expected_scope}) -> {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["agent_id"] == agent_id
        assert data["scope"] == expected_scope
        assert data["operation"] == operation
        assert "data" in data


def test_all_60_specialist_agents_registered_and_executable(client: TestClient):
    """Ensure every single specialist agent from AGT-01 to AGT-60 is mapped and operational."""
    assert len(AGENT_SCOPE_MAP) == 60, f"Expected 60 agents, found {len(AGENT_SCOPE_MAP)}"

    # Default representative operation for each scope
    scope_default_op = {
        "caravan:operations": "executive_operations_synthesis",
        "caravan:research": "search_opportunities",
        "caravan:engineering": "probe_service_health",
        "caravan:marketing": "get_marketing_audience",
        "caravan:sales": "get_customer_pipeline",
        "caravan:finance": "get_revenue_telemetry",
        "caravan:legal": "compliance_calendar",
        "caravan:analytics": "get_platform_metrics",
        "caravan:product": "product_feature_backlog",
        "caravan:funding": "get_application_pipeline",
        "caravan:support": "list_support_tickets",
        "caravan:security": "audit_security_logs",
    }

    for i in range(1, 61):
        agent_id = f"AGT-{i:02d}"
        assert agent_id in AGENT_SCOPE_MAP, f"Agent {agent_id} missing from AGENT_SCOPE_MAP"
        scope = AGENT_SCOPE_MAP[agent_id]
        op = scope_default_op[scope]

        res = client.post(
            "/api/v1/bridge/agent-action",
            headers={
                "X-Ultron-Bridge-Key": BRIDGE_KEY,
                "X-Agent-ID": agent_id,
                "X-Correlation-ID": f"corr-all-60-{agent_id}",
                "X-Task-ID": f"task-all-60-{agent_id}",
            },
            json={"operation": op},
        )
        assert res.status_code == 200, f"Failed execution for {agent_id} ({scope}): {res.text}"
        payload = res.json()
        assert payload["success"] is True
        assert payload["agent_id"] == agent_id
        assert payload["scope"] == scope


def test_audit_trail_logging_on_agent_action(client: TestClient):
    """Verify that every S2S agent action produces a structured audit record."""
    from app.db.session import get_session_factory
    corr_id = "test-corr-audit-verify-999"
    task_id = "task-audit-verify-999"

    res = client.post(
        "/api/v1/bridge/agent-action",
        headers={
            "X-Ultron-Bridge-Key": BRIDGE_KEY,
            "X-Agent-ID": "AGT-01",
            "X-Correlation-ID": corr_id,
            "X-Task-ID": task_id,
        },
        json={"operation": "executive_operations_synthesis"},
    )
    assert res.status_code == 200

    session_factory = get_session_factory()
    with session_factory() as db:
        stmt = select(AuditLogRecord).where(AuditLogRecord.action == "CARAVAN_AGENT_EXECUTIVE_OPERATIONS_SYNTHESIS")
        logs = db.execute(stmt).scalars().all()
        matching = [l for l in logs if l.details and l.details.get("correlation_id") == corr_id]
        assert len(matching) >= 1
        log = matching[0]
        assert log.actor == "ultron:AGT-01"
        assert log.details.get("task_id") == task_id
        assert log.details.get("scope") == "caravan:operations"
