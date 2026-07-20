import uuid
import pytest
from app.services.analytics_engine import AnalyticsContext, AnalyticsEngine
from app.services.analytics.complexity_rules import LargeFileRule, LongMethodRule, HighParameterCountRule
from app.models.file import File
from app.models.code_entity import CodeEntity

@pytest.fixture
def mock_context():
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    # Very long method
    e1 = CodeEntity(id=uuid.uuid4(), name="methodA", entity_type="method", file_id=file_id, start_line=1, end_line=100)
    # High params
    e2 = CodeEntity(id=uuid.uuid4(), name="methodB", entity_type="method", file_id=file_id, start_line=101, end_line=110, meta_data={"parameters": [1,2,3,4,5,6,7,8]})
    
    ctx = AnalyticsContext(
        repository_id=repo_id,
        files=[File(id=file_id, filename="test.py")],
        entities=[e1, e2],
        dependencies=[]
    )
    AnalyticsEngine._build_indexes(ctx)
    return ctx

def test_large_file_rule(mock_context):
    rule = LargeFileRule()
    rule.WARNING_THRESHOLD = 50
    rule.CRITICAL_THRESHOLD = 80
    res = rule.compute(mock_context)
    
    assert res["total"] == 1
    assert res["issues"][0]["severity"] == "critical"
    assert res["issues"][0]["metric_value"] == 110

def test_long_method_rule(mock_context):
    rule = LongMethodRule()
    res = rule.compute(mock_context)
    
    assert res["total"] >= 1
    # methodA has 100 lines (critical threshold is 60)
    critical_issue = next(i for i in res["issues"] if i["entity_name"] == "methodA")
    assert critical_issue["severity"] == "critical"
    assert critical_issue["metric_value"] == 100

def test_high_parameter_rule(mock_context):
    rule = HighParameterCountRule()
    res = rule.compute(mock_context)
    
    assert res["total"] >= 1
    critical_issue = next(i for i in res["issues"] if i["entity_name"] == "methodB")
    assert critical_issue["severity"] == "critical"
    assert critical_issue["metric_value"] == 8
