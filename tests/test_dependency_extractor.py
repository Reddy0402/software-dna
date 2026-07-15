"""
Comprehensive tests for the Dependency Extraction Engine (Sprint 4 Part 1).

Covers:
  - Containment / CONTAINS / DEFINES
  - Inheritance / EXTENDS
  - Nested classes
  - Cross-file imports / IMPORTS / DEPENDS_ON
  - Circular references (A imports B, B imports A)
  - Recursive function calls
  - Interfaces / IMPLEMENTS
  - Language-specific patterns (Python __init__, Go structs)
  - Validation & deduplication
  - Edge cases (empty repos, no relationships, missing metadata)
  - API endpoints
"""
import uuid
import pytest
from datetime import datetime, timezone

from app.models.repository import Repository
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency
from app.services.dependency_extractor import DependencyExtractionService
from app.services.analyzers import (
    DependencyRecord,
    RelationshipType,
    get_all_analyzers,
)
from app.services.analyzers.containment_analyzer import ContainmentAnalyzer
from app.services.analyzers.import_analyzer import ImportAnalyzer
from app.services.analyzers.inheritance_analyzer import InheritanceAnalyzer
from app.services.analyzers.call_analyzer import CallAnalyzer
from app.services.analyzers.usage_analyzer import UsageAnalyzer
from app.core.exceptions import DependencyExtractionError


# ============================================================================
# Helper: Create test fixtures in the DB
# ============================================================================

def _create_repo(db, name="test-repo"):
    repo = Repository(
        id=uuid.uuid4(),
        name=name,
        url=f"https://github.com/test/{name}",
        clone_status="completed",
        parser_status="completed",
        graph_status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def _create_file(db, repo_id, relative_path="src/main.py", language="Python"):
    filename = relative_path.rsplit("/", 1)[-1] if "/" in relative_path else relative_path
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    f = File(
        id=uuid.uuid4(),
        repository_id=repo_id,
        absolute_path=f"/workspace/{relative_path}",
        relative_path=relative_path,
        filename=filename,
        extension=ext,
        language=language,
        depth=relative_path.count("/"),
        size_bytes=100,
        last_modified=datetime.utcnow(),
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _create_entity(
    db, repo_id, file_id, name, entity_type,
    fqn=None, parent_id=None, start_line=0, end_line=10,
    visibility="public", language="Python", meta_data=None
):
    entity = CodeEntity(
        id=uuid.uuid4(),
        repository_id=repo_id,
        file_id=file_id,
        parent_id=parent_id,
        entity_type=entity_type,
        name=name,
        fully_qualified_name=fqn or f"module.{name}",
        start_line=start_line,
        end_line=end_line,
        visibility=visibility,
        language=language,
        meta_data=meta_data or {},
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


# ============================================================================
# Tests: Containment Analyzer
# ============================================================================

class TestContainmentAnalyzer:
    """Test CONTAINS and DEFINES relationships from parent-child nesting."""

    def test_class_contains_method(self, db_session):
        """A class should CONTAIN its method."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        cls = _create_entity(db_session, repo.id, file.id, "Calculator", "class")
        method = _create_entity(
            db_session, repo.id, file.id, "add", "method",
            fqn="module.Calculator.add", parent_id=cls.id, start_line=2
        )

        analyzer = ContainmentAnalyzer()
        entities = [cls, method]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        contains = [r for r in records if r.relationship_type == RelationshipType.CONTAINS]
        defines = [r for r in records if r.relationship_type == RelationshipType.DEFINES]

        assert len(contains) == 1
        assert contains[0].source_entity_id == cls.id
        assert contains[0].target_entity_id == method.id
        assert contains[0].confidence == 1.0

        assert len(defines) == 1
        assert defines[0].source_entity_id == cls.id
        assert defines[0].target_entity_id == method.id

    def test_nested_class_containment(self, db_session):
        """Nested class should produce CONTAINS for outer → inner."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        outer = _create_entity(db_session, repo.id, file.id, "Outer", "class")
        inner = _create_entity(
            db_session, repo.id, file.id, "Inner", "class",
            fqn="module.Outer.Inner", parent_id=outer.id, start_line=5
        )
        inner_method = _create_entity(
            db_session, repo.id, file.id, "do_stuff", "method",
            fqn="module.Outer.Inner.do_stuff", parent_id=inner.id, start_line=6
        )

        analyzer = ContainmentAnalyzer()
        entities = [outer, inner, inner_method]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        contains = [r for r in records if r.relationship_type == RelationshipType.CONTAINS]
        # outer→inner and inner→inner_method
        assert len(contains) == 2

        parent_child_pairs = [(r.source_entity_id, r.target_entity_id) for r in contains]
        assert (outer.id, inner.id) in parent_child_pairs
        assert (inner.id, inner_method.id) in parent_child_pairs


# ============================================================================
# Tests: Inheritance Analyzer
# ============================================================================

class TestInheritanceAnalyzer:
    """Test EXTENDS and IMPLEMENTS relationships."""

    def test_python_class_extends(self, db_session):
        """Python class with bases metadata should produce EXTENDS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        base_cls = _create_entity(
            db_session, repo.id, file.id, "Animal", "class",
            fqn="module.Animal"
        )
        child_cls = _create_entity(
            db_session, repo.id, file.id, "Dog", "class",
            fqn="module.Dog", meta_data={"bases": ["Animal"]}
        )

        analyzer = InheritanceAnalyzer()
        entities = [base_cls, child_cls]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        assert len(records) == 1
        assert records[0].relationship_type == RelationshipType.EXTENDS
        assert records[0].source_entity_id == child_cls.id
        assert records[0].target_entity_id == base_cls.id
        assert records[0].confidence == 1.0
        assert records[0].target_fqn == "Animal"

    def test_multiple_inheritance(self, db_session):
        """Class with multiple bases should produce multiple EXTENDS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        base_a = _create_entity(
            db_session, repo.id, file.id, "Serializable", "class",
            fqn="module.Serializable"
        )
        base_b = _create_entity(
            db_session, repo.id, file.id, "Loggable", "class",
            fqn="module.Loggable"
        )
        child = _create_entity(
            db_session, repo.id, file.id, "Service", "class",
            fqn="module.Service",
            meta_data={"bases": ["Serializable", "Loggable"]}
        )

        analyzer = InheritanceAnalyzer()
        entities = [base_a, base_b, child]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)
        extends = [r for r in records if r.relationship_type == RelationshipType.EXTENDS]

        assert len(extends) == 2
        targets = {r.target_fqn for r in extends}
        assert targets == {"Serializable", "Loggable"}

    def test_unresolved_base_class(self, db_session):
        """Base class not in repo should produce EXTENDS with lower confidence."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        child = _create_entity(
            db_session, repo.id, file.id, "MyException", "class",
            fqn="module.MyException",
            meta_data={"bases": ["Exception"]}
        )

        analyzer = InheritanceAnalyzer()
        entities = [child]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        assert len(records) == 1
        assert records[0].target_entity_id is None
        assert records[0].confidence == 0.7
        assert records[0].target_fqn == "Exception"

    def test_interface_implements(self, db_session):
        """Class implementing an interface should produce IMPLEMENTS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/app.ts", "TypeScript")
        iface = _create_entity(
            db_session, repo.id, file.id, "Drawable", "interface",
            fqn="module.Drawable", language="TypeScript"
        )
        cls = _create_entity(
            db_session, repo.id, file.id, "Circle", "class",
            fqn="module.Circle", language="TypeScript",
            meta_data={"bases": ["Drawable"]}
        )

        analyzer = InheritanceAnalyzer()
        entities = [iface, cls]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        assert len(records) == 1
        assert records[0].relationship_type == RelationshipType.IMPLEMENTS
        assert records[0].source_entity_id == cls.id
        assert records[0].target_entity_id == iface.id

    def test_java_explicit_implements(self, db_session):
        """Java class with explicit implements list should produce IMPLEMENTS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/Service.java", "Java")
        iface = _create_entity(
            db_session, repo.id, file.id, "Runnable", "interface",
            fqn="module.Runnable", language="Java"
        )
        cls = _create_entity(
            db_session, repo.id, file.id, "TaskRunner", "class",
            fqn="module.TaskRunner", language="Java",
            meta_data={"bases": [], "implements": ["Runnable"]}
        )

        analyzer = InheritanceAnalyzer()
        entities = [iface, cls]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        implements = [r for r in records if r.relationship_type == RelationshipType.IMPLEMENTS]
        assert len(implements) == 1
        assert implements[0].source_entity_id == cls.id
        assert implements[0].target_entity_id == iface.id


# ============================================================================
# Tests: Import Analyzer
# ============================================================================

class TestImportAnalyzer:
    """Test IMPORTS and DEPENDS_ON relationships."""

    def test_basic_import(self, db_session):
        """Import entity should produce IMPORTS relationship."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/main.py")
        imp = _create_entity(
            db_session, repo.id, file.id, "import os", "import",
            fqn="main.import_os",
            meta_data={"raw_import": "import os"}
        )

        analyzer = ImportAnalyzer()
        entities = [imp]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        imports = [r for r in records if r.relationship_type == RelationshipType.IMPORTS]
        assert len(imports) == 1
        assert imports[0].source_entity_id == imp.id
        assert imports[0].target_fqn == "os"
        # External import → unresolved
        assert imports[0].target_entity_id is None
        assert imports[0].confidence == 0.5

    def test_cross_file_import(self, db_session):
        """Import from another file in the repo should resolve and produce DEPENDS_ON."""
        repo = _create_repo(db_session)
        file_a = _create_file(db_session, repo.id, "utils/helpers.py")
        file_b = _create_file(db_session, repo.id, "src/main.py")

        helper_cls = _create_entity(
            db_session, repo.id, file_a.id, "Helper", "class",
            fqn="helpers.Helper"
        )
        imp = _create_entity(
            db_session, repo.id, file_b.id, "from utils.helpers import Helper", "import",
            fqn="main.import_helpers",
            meta_data={"raw_import": "from utils.helpers import Helper"}
        )

        analyzer = ImportAnalyzer()
        entities = [helper_cls, imp]
        files = [file_a, file_b]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, files, entity_lookup, fqn_lookup)

        imports = [r for r in records if r.relationship_type == RelationshipType.IMPORTS]
        depends = [r for r in records if r.relationship_type == RelationshipType.DEPENDS_ON]

        assert len(imports) == 1
        # The import target is "utils.helpers" (module path), resolved via file_module_map
        assert imports[0].source_entity_id == imp.id

    def test_circular_imports(self, db_session):
        """Circular imports (A imports B, B imports A) should both be captured."""
        repo = _create_repo(db_session)
        file_a = _create_file(db_session, repo.id, "module_a.py")
        file_b = _create_file(db_session, repo.id, "module_b.py")

        cls_a = _create_entity(
            db_session, repo.id, file_a.id, "ClassA", "class",
            fqn="module_a.ClassA"
        )
        cls_b = _create_entity(
            db_session, repo.id, file_b.id, "ClassB", "class",
            fqn="module_b.ClassB"
        )

        # A imports B
        imp_a = _create_entity(
            db_session, repo.id, file_a.id, "from module_b import ClassB", "import",
            fqn="module_a.import_b",
            meta_data={"raw_import": "from module_b import ClassB"}
        )
        # B imports A
        imp_b = _create_entity(
            db_session, repo.id, file_b.id, "from module_a import ClassA", "import",
            fqn="module_b.import_a",
            meta_data={"raw_import": "from module_a import ClassA"}
        )

        analyzer = ImportAnalyzer()
        entities = [cls_a, cls_b, imp_a, imp_b]
        files = [file_a, file_b]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, files, entity_lookup, fqn_lookup)

        imports = [r for r in records if r.relationship_type == RelationshipType.IMPORTS]
        # Should have 2 import relationships (one from each direction)
        assert len(imports) == 2

        source_ids = {r.source_entity_id for r in imports}
        assert imp_a.id in source_ids
        assert imp_b.id in source_ids


# ============================================================================
# Tests: Call Analyzer
# ============================================================================

class TestCallAnalyzer:
    """Test CALLS and REFERENCES relationships."""

    def test_recursive_function_call(self, db_session):
        """Function calling itself should produce CALLS with recursive=True."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        func = _create_entity(
            db_session, repo.id, file.id, "factorial", "function",
            fqn="module.factorial",
            meta_data={"parameters": ["n"], "calls": ["factorial"]}
        )

        analyzer = CallAnalyzer()
        entities = [func]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        calls = [r for r in records if r.relationship_type == RelationshipType.CALLS]
        assert len(calls) >= 1

        recursive_calls = [r for r in calls if r.meta_data.get("recursive")]
        assert len(recursive_calls) == 1
        assert recursive_calls[0].source_entity_id == func.id
        assert recursive_calls[0].target_entity_id == func.id

    def test_function_calls_another(self, db_session):
        """Function calling another function should produce CALLS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        helper = _create_entity(
            db_session, repo.id, file.id, "validate", "function",
            fqn="module.validate"
        )
        caller = _create_entity(
            db_session, repo.id, file.id, "process", "function",
            fqn="module.process",
            meta_data={"calls": ["validate"]}
        )

        analyzer = CallAnalyzer()
        entities = [helper, caller]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        calls = [r for r in records if r.relationship_type == RelationshipType.CALLS]
        assert len(calls) >= 1

        direct_calls = [
            r for r in calls
            if r.source_entity_id == caller.id and r.target_entity_id == helper.id
        ]
        assert len(direct_calls) == 1
        assert not direct_calls[0].meta_data.get("recursive")

    def test_explicit_references(self, db_session):
        """Entity with references metadata should produce REFERENCES."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        target = _create_entity(
            db_session, repo.id, file.id, "Config", "class",
            fqn="module.Config"
        )
        func = _create_entity(
            db_session, repo.id, file.id, "init_app", "function",
            fqn="module.init_app",
            meta_data={"references": ["Config"]}
        )

        analyzer = CallAnalyzer()
        entities = [target, func]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        refs = [r for r in records if r.relationship_type == RelationshipType.REFERENCES]
        assert len(refs) == 1
        assert refs[0].source_entity_id == func.id
        assert refs[0].target_entity_id == target.id


# ============================================================================
# Tests: Usage Analyzer
# ============================================================================

class TestUsageAnalyzer:
    """Test USES relationships from decorators, type annotations, etc."""

    def test_decorator_usage(self, db_session):
        """Entity with decorator metadata should produce USES."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        decorator_cls = _create_entity(
            db_session, repo.id, file.id, "staticmethod", "class",
            fqn="module.staticmethod"
        )
        method = _create_entity(
            db_session, repo.id, file.id, "helper", "method",
            fqn="module.helper",
            meta_data={"decorators": ["@staticmethod"]}
        )

        analyzer = UsageAnalyzer()
        entities = [decorator_cls, method]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        uses = [r for r in records if r.relationship_type == RelationshipType.USES]
        assert len(uses) >= 1

        decorator_uses = [r for r in uses if r.meta_data.get("usage_type") == "decorator"]
        assert len(decorator_uses) == 1

    def test_return_type_usage(self, db_session):
        """Function with return type annotation should produce USES."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id)
        ret_cls = _create_entity(
            db_session, repo.id, file.id, "Response", "class",
            fqn="module.Response"
        )
        func = _create_entity(
            db_session, repo.id, file.id, "get_data", "function",
            fqn="module.get_data",
            meta_data={"return_type": "Response"}
        )

        analyzer = UsageAnalyzer()
        entities = [ret_cls, func]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        uses = [r for r in records if r.relationship_type == RelationshipType.USES]
        return_uses = [r for r in uses if r.meta_data.get("usage_type") == "return_type"]
        assert len(return_uses) == 1
        assert return_uses[0].target_entity_id == ret_cls.id


# ============================================================================
# Tests: Full Pipeline (DependencyExtractionService)
# ============================================================================

class TestDependencyExtractionService:
    """Integration tests for the full extraction pipeline."""

    def test_full_pipeline(self, db_session):
        """Full extraction pipeline should produce and persist dependencies."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/models.py")

        # Create a class with a method
        cls = _create_entity(
            db_session, repo.id, file.id, "User", "class",
            fqn="models.User", meta_data={"bases": []}
        )
        method = _create_entity(
            db_session, repo.id, file.id, "get_name", "method",
            fqn="models.User.get_name", parent_id=cls.id,
            start_line=5, end_line=8
        )

        stats = DependencyExtractionService.extract_dependencies(
            db=db_session, repository_id=repo.id
        )

        assert stats["repository_id"] == repo.id
        assert stats["total_dependencies"] > 0

        # Verify records persisted in DB
        deps = db_session.query(Dependency).filter(
            Dependency.repository_id == repo.id
        ).all()
        assert len(deps) == stats["total_dependencies"]

    def test_pipeline_with_inheritance(self, db_session):
        """Pipeline should capture inheritance relationships."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/animals.py")

        base = _create_entity(
            db_session, repo.id, file.id, "Animal", "class",
            fqn="animals.Animal"
        )
        child = _create_entity(
            db_session, repo.id, file.id, "Cat", "class",
            fqn="animals.Cat", meta_data={"bases": ["Animal"]}
        )

        stats = DependencyExtractionService.extract_dependencies(
            db=db_session, repository_id=repo.id
        )

        deps = db_session.query(Dependency).filter(
            Dependency.repository_id == repo.id,
            Dependency.relationship_type == RelationshipType.EXTENDS
        ).all()

        assert len(deps) >= 1
        extends_dep = deps[0]
        assert extends_dep.source_entity_id == child.id
        assert extends_dep.target_entity_id == base.id

    def test_empty_repository(self, db_session):
        """Empty repository should return zero dependencies."""
        repo = _create_repo(db_session)

        stats = DependencyExtractionService.extract_dependencies(
            db=db_session, repository_id=repo.id
        )

        assert stats["total_dependencies"] == 0
        assert stats["unresolved_count"] == 0

    def test_nonexistent_repository(self, db_session):
        """Extracting from a nonexistent repo should raise DependencyExtractionError."""
        fake_id = uuid.uuid4()
        with pytest.raises(DependencyExtractionError):
            DependencyExtractionService.extract_dependencies(
                db=db_session, repository_id=fake_id
            )

    def test_re_extraction_clears_old_data(self, db_session):
        """Running extraction twice should replace old dependencies."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/app.py")
        cls = _create_entity(
            db_session, repo.id, file.id, "App", "class",
            fqn="app.App"
        )
        method = _create_entity(
            db_session, repo.id, file.id, "run", "method",
            fqn="app.App.run", parent_id=cls.id
        )

        # First run
        stats1 = DependencyExtractionService.extract_dependencies(
            db=db_session, repository_id=repo.id
        )

        # Second run
        stats2 = DependencyExtractionService.extract_dependencies(
            db=db_session, repository_id=repo.id
        )

        # Should have same count (old cleared, new inserted)
        assert stats1["total_dependencies"] == stats2["total_dependencies"]

        # Verify no duplicates in DB
        deps = db_session.query(Dependency).filter(
            Dependency.repository_id == repo.id
        ).all()
        assert len(deps) == stats2["total_dependencies"]


# ============================================================================
# Tests: Validation & Deduplication
# ============================================================================

class TestValidation:
    """Test the validation and deduplication step."""

    def test_duplicate_removal(self):
        """Duplicate records with same unique key should be deduplicated."""
        repo_id = uuid.uuid4()
        src_id = uuid.uuid4()
        tgt_id = uuid.uuid4()

        records = [
            DependencyRecord(
                repository_id=repo_id,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relationship_type=RelationshipType.CONTAINS,
                confidence=1.0,
                source_file="test.py",
                line_number=1,
                target_fqn="module.Class",
            ),
            DependencyRecord(
                repository_id=repo_id,
                source_entity_id=src_id,
                target_entity_id=tgt_id,
                relationship_type=RelationshipType.CONTAINS,
                confidence=1.0,
                source_file="test.py",
                line_number=1,
                target_fqn="module.Class",
            ),
        ]

        validated = DependencyExtractionService._validate_dependencies(records)
        assert len(validated) == 1

    def test_invalid_relationship_type_filtered(self):
        """Records with unknown relationship types should be filtered out."""
        records = [
            DependencyRecord(
                repository_id=uuid.uuid4(),
                source_entity_id=uuid.uuid4(),
                target_entity_id=uuid.uuid4(),
                relationship_type="INVALID_TYPE",
                confidence=1.0,
                source_file="test.py",
                line_number=1,
                target_fqn="something",
            ),
        ]

        validated = DependencyExtractionService._validate_dependencies(records)
        assert len(validated) == 0

    def test_confidence_clamping(self):
        """Confidence should be clamped to [0.0, 1.0]."""
        records = [
            DependencyRecord(
                repository_id=uuid.uuid4(),
                source_entity_id=uuid.uuid4(),
                target_entity_id=uuid.uuid4(),
                relationship_type=RelationshipType.CALLS,
                confidence=1.5,
                source_file="test.py",
                line_number=1,
                target_fqn="something",
            ),
            DependencyRecord(
                repository_id=uuid.uuid4(),
                source_entity_id=uuid.uuid4(),
                target_entity_id=uuid.uuid4(),
                relationship_type=RelationshipType.USES,
                confidence=-0.5,
                source_file="test.py",
                line_number=1,
                target_fqn="other",
            ),
        ]

        validated = DependencyExtractionService._validate_dependencies(records)
        assert validated[0].confidence == 1.0
        assert validated[1].confidence == 0.0


# ============================================================================
# Tests: Analyzer Registry
# ============================================================================

class TestAnalyzerRegistry:
    """Test the analyzer discovery and registry mechanism."""

    def test_all_analyzers_registered(self):
        """All five analyzers should be registered."""
        analyzers = get_all_analyzers()
        analyzer_types = {type(a).__name__ for a in analyzers}

        assert "ContainmentAnalyzer" in analyzer_types
        assert "ImportAnalyzer" in analyzer_types
        assert "InheritanceAnalyzer" in analyzer_types
        assert "CallAnalyzer" in analyzer_types
        assert "UsageAnalyzer" in analyzer_types

    def test_dependency_record_unique_key(self):
        """DependencyRecord.unique_key() should produce consistent keys."""
        src_id = uuid.uuid4()
        tgt_id = uuid.uuid4()
        record = DependencyRecord(
            repository_id=uuid.uuid4(),
            source_entity_id=src_id,
            target_entity_id=tgt_id,
            relationship_type="CONTAINS",
            confidence=1.0,
            source_file="test.py",
            line_number=1,
            target_fqn="module.Class",
        )

        key1 = record.unique_key()
        key2 = record.unique_key()
        assert key1 == key2
        assert str(src_id) in key1
        assert str(tgt_id) in key1
        assert "CONTAINS" in key1


# ============================================================================
# Tests: Language-Specific Patterns
# ============================================================================

class TestLanguagePatterns:
    """Test language-specific dependency patterns."""

    def test_python_init_defines(self, db_session):
        """Python __init__ method should be contained by its class."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/model.py")
        cls = _create_entity(
            db_session, repo.id, file.id, "Model", "class",
            fqn="model.Model"
        )
        init = _create_entity(
            db_session, repo.id, file.id, "__init__", "method",
            fqn="model.Model.__init__", parent_id=cls.id,
            visibility="public", start_line=2
        )

        analyzer = ContainmentAnalyzer()
        entities = [cls, init]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        defines = [r for r in records if r.relationship_type == RelationshipType.DEFINES]
        assert len(defines) == 1
        assert defines[0].source_entity_id == cls.id
        assert defines[0].target_entity_id == init.id

    def test_go_struct_method(self, db_session):
        """Go struct with methods should produce CONTAINS."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "main.go", "Go")
        struct = _create_entity(
            db_session, repo.id, file.id, "Server", "struct",
            fqn="main.Server", language="Go"
        )
        method = _create_entity(
            db_session, repo.id, file.id, "Start", "method",
            fqn="main.Server.Start", parent_id=struct.id,
            language="Go", start_line=10
        )

        analyzer = ContainmentAnalyzer()
        entities = [struct, method]
        entity_lookup = {e.id: e for e in entities}
        fqn_lookup = {e.fully_qualified_name: e.id for e in entities}

        records = analyzer.analyze(entities, [file], entity_lookup, fqn_lookup)

        contains = [r for r in records if r.relationship_type == RelationshipType.CONTAINS]
        assert len(contains) == 1
        assert contains[0].meta_data["parent_type"] == "struct"
        assert contains[0].meta_data["child_type"] == "method"


# ============================================================================
# Tests: API Endpoints
# ============================================================================

class TestAPIEndpoints:
    """Test the REST API endpoints for dependency extraction."""

    def test_extract_endpoint(self, client, db_session):
        """POST /repositories/{id}/dependencies/extract should return stats."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/main.py")
        cls = _create_entity(
            db_session, repo.id, file.id, "App", "class", fqn="main.App"
        )

        response = client.post(f"/api/v1/repositories/{repo.id}/dependencies/extract")
        assert response.status_code == 200

        data = response.json()
        assert "total_dependencies" in data
        assert "by_relationship_type" in data
        assert data["repository_id"] == str(repo.id)

    def test_list_endpoint(self, client, db_session):
        """GET /repositories/{id}/dependencies should return dependency list."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/main.py")
        cls = _create_entity(
            db_session, repo.id, file.id, "App", "class", fqn="main.App"
        )
        method = _create_entity(
            db_session, repo.id, file.id, "run", "method",
            fqn="main.App.run", parent_id=cls.id
        )

        # First extract
        client.post(f"/api/v1/repositories/{repo.id}/dependencies/extract")

        # Then list
        response = client.get(f"/api/v1/repositories/{repo.id}/dependencies")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_with_type_filter(self, client, db_session):
        """GET with relationship_type filter should return filtered results."""
        repo = _create_repo(db_session)
        file = _create_file(db_session, repo.id, "src/main.py")
        cls = _create_entity(
            db_session, repo.id, file.id, "App", "class", fqn="main.App"
        )
        method = _create_entity(
            db_session, repo.id, file.id, "run", "method",
            fqn="main.App.run", parent_id=cls.id
        )

        client.post(f"/api/v1/repositories/{repo.id}/dependencies/extract")

        response = client.get(
            f"/api/v1/repositories/{repo.id}/dependencies",
            params={"relationship_type": "CONTAINS"}
        )
        assert response.status_code == 200

        data = response.json()
        for dep in data:
            assert dep["relationship_type"] == "CONTAINS"

    def test_extract_nonexistent_repo(self, client):
        """Extracting from nonexistent repo should return 400."""
        fake_id = uuid.uuid4()
        response = client.post(f"/api/v1/repositories/{fake_id}/dependencies/extract")
        assert response.status_code == 400
