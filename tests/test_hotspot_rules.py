import uuid
import pytest
from app.services.analytics_engine import AnalyticsContext, AnalyticsEngine
from app.services.analytics.hotspot_rules import CentralityHotspotRule, ComplexityHotspotRule, CompositeHotspotRule
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency

@pytest.fixture
def mock_context():
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    e1 = CodeEntity(id=uuid.uuid4(), name="Central", entity_type="class", file_id=file_id, start_line=1, end_line=50)
    e2 = CodeEntity(id=uuid.uuid4(), name="Edge1", entity_type="class", file_id=file_id, start_line=51, end_line=60)
    e3 = CodeEntity(id=uuid.uuid4(), name="Edge2", entity_type="class", file_id=file_id, start_line=61, end_line=70)
    
    deps = [
        Dependency(id=uuid.uuid4(), source_entity_id=e2.id, target_entity_id=e1.id, relationship_type="CALLS"),
        Dependency(id=uuid.uuid4(), source_entity_id=e1.id, target_entity_id=e3.id, relationship_type="CALLS")
    ]
    
    ctx = AnalyticsContext(
        repository_id=repo_id,
        files=[File(id=file_id, filename="test.py")],
        entities=[e1, e2, e3],
        dependencies=deps
    )
    AnalyticsEngine._build_indexes(ctx)
    return ctx

def test_centrality_hotspot(mock_context):
    rule = CentralityHotspotRule()
    res = rule.compute(mock_context)
    
    assert res["total_hotspots"] >= 1
    # 'Central' should have the highest centrality (1 in, 1 out)
    top_hotspot = res["hotspots"][0]
    assert top_hotspot["entity_name"] == "Central"
    assert top_hotspot["centrality_score"] == 1.0

def test_complexity_hotspot(mock_context):
    rule = ComplexityHotspotRule()
    res = rule.compute(mock_context)
    
    assert res["total_hotspots"] >= 1
    # 'Central' is the largest (50 lines) and has the most deps
    top_hotspot = res["hotspots"][0]
    assert top_hotspot["entity_name"] == "Central"
    assert top_hotspot["complexity_score"] == 1.0

def test_composite_hotspot(mock_context):
    rule = CompositeHotspotRule()
    res = rule.compute(mock_context)
    
    assert res["total_hotspots"] >= 1
    top_hotspot = res["hotspots"][0]
    assert top_hotspot["entity_name"] == "Central"
    assert "composite_score" in top_hotspot
    assert "sub_scores" in top_hotspot
