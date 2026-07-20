import uuid
import pytest
from app.services.analytics_engine import AnalyticsContext
from app.services.analytics.health_rules import StructuralCountsRule, SizeMetricsRule, GraphDensityRule, HealthScoreRule
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency

@pytest.fixture
def mock_context():
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    e1 = CodeEntity(id=uuid.uuid4(), name="ClassA", entity_type="class", file_id=file_id, start_line=1, end_line=10)
    e2 = CodeEntity(id=uuid.uuid4(), name="methodA", entity_type="method", file_id=file_id, start_line=2, end_line=9)
    e3 = CodeEntity(id=uuid.uuid4(), name="funcB", entity_type="function", file_id=file_id, start_line=12, end_line=20)
    
    deps = [
        Dependency(id=uuid.uuid4(), source_entity_id=e1.id, target_entity_id=e2.id, relationship_type="CALLS")
    ]
    
    ctx = AnalyticsContext(
        repository_id=repo_id,
        files=[File(id=file_id, filename="test.py")],
        entities=[e1, e2, e3],
        dependencies=deps
    )
    # Mock some methods that build indexes
    from app.services.analytics_engine import AnalyticsEngine
    AnalyticsEngine._build_indexes(ctx)
    return ctx

def test_structural_counts(mock_context):
    rule = StructuralCountsRule()
    res = rule.compute(mock_context)
    
    assert res["total_files"] == 1
    assert res["total_entities"] == 3
    assert res["classes"] == 1
    assert res["methods"] == 1
    assert res["functions"] == 1

def test_size_metrics(mock_context):
    rule = SizeMetricsRule()
    res = rule.compute(mock_context)
    
    # methodA is 8 lines, funcB is 9 lines, ClassA is 10 lines
    assert res["avg_class_size"] == 10.0
    assert res["avg_method_size"] == 8.0
    assert res["avg_function_size"] == 9.0

def test_graph_density(mock_context):
    rule = GraphDensityRule()
    res = rule.compute(mock_context)
    
    assert res["total_nodes"] == 3
    assert res["total_edges"] == 1
    # 3 nodes, max edges = 3 * 2 = 6, density = 1/6
    assert round(res["density"], 4) == 0.1667

def test_health_score(mock_context):
    rule = HealthScoreRule()
    res = rule.compute(mock_context)
    
    assert "overall_score" in res
    assert "grade" in res
    assert res["grade"] in ["A", "B", "C", "D", "F"]
