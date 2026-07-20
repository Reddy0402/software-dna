import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest

from app.services.analytics_engine import AnalyticsContext

# Mocks for AnalyticsEngine methods
def mock_build_context(*args, **kwargs):
    return AnalyticsContext(repository_id=uuid.uuid4())

def mock_run_category_health(*args, **kwargs):
    from app.services.analytics_engine import RuleResult
    return [RuleResult(rule_id="health.overall_score", category="health", success=True, data={"overall_score": 85.5, "grade": "B"})]

def mock_aggregate_results(*args, **kwargs):
    return {
        "health": {
            "health.overall_score": {"success": True, "data": {"overall_score": 85.5, "grade": "B"}}
        }
    }

def mock_run_category_complexity(*args, **kwargs):
    from app.services.analytics_engine import RuleResult
    return [RuleResult(rule_id="complexity.long_methods", category="complexity", success=True, data={
        "issues": [{"entity_id": "1", "entity_name": "methodA", "entity_type": "method", "issue_type": "long_method", "severity": "critical", "metric_value": 100, "threshold": 60}],
        "total": 1, "critical_count": 1, "warning_count": 0
    })]

def mock_aggregate_results_complexity(*args, **kwargs):
    return {
        "complexity": {
            "complexity.long_methods": {"success": True, "data": {
                "issues": [{"entity_id": "1", "entity_name": "methodA", "entity_type": "method", "issue_type": "long_method", "severity": "critical", "metric_value": 100, "threshold": 60}],
                "total": 1, "critical_count": 1, "warning_count": 0
            }}
        }
    }

def test_get_health_report(client, db_session):
    # Setup test repo
    from app.models.repository import Repository
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, name="TestRepo", url="http://test.com")
    db_session.add(repo)
    db_session.commit()

    with patch("app.api.v1.endpoints.analytics.AnalyticsEngine.build_context", side_effect=mock_build_context), \
         patch("app.api.v1.endpoints.analytics.AnalyticsEngine.run_category", side_effect=mock_run_category_health), \
         patch("app.api.v1.endpoints.analytics.AnalyticsEngine.aggregate_results", side_effect=mock_aggregate_results):
        
        response = client.get(f"/api/v1/analytics/repositories/{repo_id}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 85.5
        assert data["grade"] == "B"

def test_get_complexity_report(client, db_session):
    # Setup test repo
    from app.models.repository import Repository
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, name="TestRepo", url="http://test.com")
    db_session.add(repo)
    db_session.commit()

    with patch("app.api.v1.endpoints.analytics.AnalyticsEngine.build_context", side_effect=mock_build_context), \
         patch("app.api.v1.endpoints.analytics.AnalyticsEngine.run_category", side_effect=mock_run_category_complexity), \
         patch("app.api.v1.endpoints.analytics.AnalyticsEngine.aggregate_results", side_effect=mock_aggregate_results_complexity):
        
        response = client.get(f"/api/v1/analytics/repositories/{repo_id}/complexity?severity=critical")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["issues"][0]["entity_name"] == "methodA"
        assert data["issues"][0]["severity"] == "critical"

def test_get_architecture_summary(client, db_session):
    from app.models.repository import Repository
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, name="TestRepo", url="http://test.com")
    db_session.add(repo)
    db_session.commit()

    with patch("app.api.v1.endpoints.analytics.AnalyticsEngine.build_context", side_effect=mock_build_context):
        # Even with empty context, the endpoint should return the basic summary structure
        response = client.get(f"/api/v1/analytics/repositories/{repo_id}/architecture")
        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_entities" in data
