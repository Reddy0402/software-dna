import uuid
import pytest
from app.services.analytics_engine import AnalyticsEngine, AnalyticsContext, AnalyticsRule, RuleResult
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency
from app.services.analytics import register_rule

# Mock rules for testing
@register_rule
class MockSuccessRule(AnalyticsRule):
    rule_id = "test.mock_success"
    category = "test_category"
    def compute(self, ctx: AnalyticsContext):
        return {"value": 42}

@register_rule
class MockErrorRule(AnalyticsRule):
    rule_id = "test.mock_error"
    category = "test_category"
    def compute(self, ctx: AnalyticsContext):
        raise ValueError("Mock error")

def test_context_building():
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    
    ctx = AnalyticsContext(
        repository_id=repo_id,
        files=[File(id=file_id, filename="test.py", repository_id=repo_id)],
        entities=[CodeEntity(id=entity_id, name="TestClass", entity_type="class", file_id=file_id, repository_id=repo_id)],
        dependencies=[]
    )
    
    AnalyticsEngine._build_indexes(ctx)
    
    assert file_id in ctx.files_by_id
    assert entity_id in ctx.entities_by_id
    assert "class" in ctx.entities_by_type
    assert file_id in ctx.entities_by_file

def test_rule_execution():
    ctx = AnalyticsContext(repository_id=uuid.uuid4())
    
    # Run success rule
    results = AnalyticsEngine._run_rules([MockSuccessRule], ctx)
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].data["value"] == 42
    
    # Run error rule
    results_err = AnalyticsEngine._run_rules([MockErrorRule], ctx)
    assert len(results_err) == 1
    assert results_err[0].success is False
    assert "Mock error" in results_err[0].error

def test_aggregate_results():
    results = [
        RuleResult(rule_id="r1", category="c1", success=True, data={"x": 1}),
        RuleResult(rule_id="r2", category="c1", success=False, error="err"),
    ]
    aggregated = AnalyticsEngine.aggregate_results(results)
    
    assert "c1" in aggregated
    assert "r1" in aggregated["c1"]
    assert "r2" in aggregated["c1"]
    assert aggregated["c1"]["r1"]["success"] is True
    assert aggregated["c1"]["r2"]["success"] is False
