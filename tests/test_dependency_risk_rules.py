import uuid
import pytest
from app.services.analytics_engine import AnalyticsContext, AnalyticsEngine
from app.services.analytics.dependency_rules import HighCouplingRule, BottleneckRule, IsolatedModuleRule
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency

@pytest.fixture
def mock_context():
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    e1 = CodeEntity(id=uuid.uuid4(), name="Hub", entity_type="class", file_id=file_id)
    e2 = CodeEntity(id=uuid.uuid4(), name="Dep1", entity_type="class", file_id=file_id)
    e3 = CodeEntity(id=uuid.uuid4(), name="Isolated", entity_type="class", file_id=file_id)
    
    deps = [
        Dependency(id=uuid.uuid4(), source_entity_id=e1.id, target_entity_id=e2.id, relationship_type="CALLS")
    ]
    
    ctx = AnalyticsContext(
        repository_id=repo_id,
        files=[File(id=file_id, filename="test.py")],
        entities=[e1, e2, e3],
        dependencies=deps
    )
    AnalyticsEngine._build_indexes(ctx)
    return ctx

def test_high_coupling_rule(mock_context):
    rule = HighCouplingRule()
    rule.FAN_OUT_THRESHOLD = 1
    res = rule.compute(mock_context)
    
    assert res["total"] >= 1
    hub_issue = next(r for r in res["risks"] if r["affected_entities"][0]["entity_name"] == "Hub")
    assert hub_issue["affected_entities"][0]["fan_out"] == 1

def test_bottleneck_rule(mock_context):
    rule = BottleneckRule()
    rule.FAN_IN_THRESHOLD = 1
    res = rule.compute(mock_context)
    
    assert res["total"] >= 1
    dep_issue = next(r for r in res["risks"] if r["affected_entities"][0]["entity_name"] == "Dep1")
    assert dep_issue["affected_entities"][0]["fan_in"] == 1

def test_isolated_module_rule(mock_context):
    rule = IsolatedModuleRule()
    res = rule.compute(mock_context)
    
    assert res["total"] == 1
    isolated_issue = res["risks"][0]
    assert isolated_issue["affected_entities"][0]["entity_name"] == "Isolated"
    assert isolated_issue["severity"] == "info"
