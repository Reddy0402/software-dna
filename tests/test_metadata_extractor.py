import pytest
import uuid
import os
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.services.visitors import PythonVisitor, TypeScriptVisitor
from app.services.extractor import ExtractionService
from app.services.parser import ParserService
from app.services.repository import RepositoryService
from app.models.file import File
from app.models.code_entity import CodeEntity


def test_python_visitor_extraction():
    code = b"""
class _MyClass(Base):
    def __init__(self):
        pass
    def greet(self):
        pass

def global_func():
    pass
"""
    parsed = ParserService.parse_file_content(code, "test.py", "test.py", "Python")
    assert parsed.status == "success"
    
    visitor = PythonVisitor()
    visitor.visit(parsed.root_node)
    
    # 4 entities: class, method __init__, method greet, function global_func
    assert len(visitor.entities) == 4
    
    # Check class
    class_ent = [e for e in visitor.entities if e.entity_type == "class"][0]
    assert class_ent.name == "_MyClass"
    assert class_ent.visibility == "protected"
    assert class_ent.meta_data == {"bases": ["Base"]}

    # Check methods
    init_ent = [e for e in visitor.entities if e.name == "__init__"][0]
    assert init_ent.entity_type == "method"
    assert init_ent.visibility == "public" # dunders are not private conventions
    assert init_ent.parent == class_ent

    greet_ent = [e for e in visitor.entities if e.name == "greet"][0]
    assert greet_ent.entity_type == "method"
    assert greet_ent.visibility == "public"
    assert greet_ent.parent == class_ent

    # Check global function
    func_ent = [e for e in visitor.entities if e.name == "global_func"][0]
    assert func_ent.entity_type == "function"
    assert func_ent.parent is None


def test_typescript_visitor_extraction():
    code = b"""
interface IGreet {
    greet(): void;
}
class Greeter implements IGreet {
    greet() {
        console.log("hello");
    }
}
"""
    parsed = ParserService.parse_file_content(code, "test.tsx", "test.tsx", "TypeScript")
    assert parsed.status == "success"

    visitor = TypeScriptVisitor()
    visitor.visit(parsed.root_node)

    # 3 entities: interface IGreet, class Greeter, method greet
    assert len(visitor.entities) == 3

    interface_ent = [e for e in visitor.entities if e.entity_type == "interface"][0]
    assert interface_ent.name == "IGreet"

    class_ent = [e for e in visitor.entities if e.entity_type == "class"][0]
    assert class_ent.name == "Greeter"


def test_extraction_endpoint_integration(client: TestClient, db_session: Session, tmp_path):
    # 1. Create a dummy file on disk
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    file_path = workspace_dir / "maths.py"
    file_path.write_text("class Calculator:\n    def add(self, a, b):\n        return a + b\n")

    # 2. Setup mock Repository and File records
    url = "https://github.com/Reddy0402/software-dna"
    repo = RepositoryService.create_pending_record(db_session, url)
    repo.clone_status = "completed"
    repo.local_path = str(workspace_dir)
    db_session.commit()

    file_record = File(
        id=uuid.uuid4(),
        repository_id=repo.id,
        absolute_path=str(file_path),
        relative_path="maths.py",
        filename="maths.py",
        extension="py",
        language="Python",
        depth=0,
        size_bytes=len(file_path.read_text()),
        last_modified=datetime.fromtimestamp(os.path.getmtime(str(file_path)))
    )
    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    # 3. Call REST Extract API
    response = client.post(f"/api/v1/files/{file_record.id}/extract")

    # 4. Assert response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Calculator, add

    calc_ent = [e for e in data if e["entity_type"] == "class"][0]
    assert calc_ent["name"] == "Calculator"
    assert calc_ent["fully_qualified_name"] == "maths.Calculator"

    add_ent = [e for e in data if e["entity_type"] == "method"][0]
    assert add_ent["name"] == "add"
    assert add_ent["fully_qualified_name"] == "maths.Calculator.add"
    assert add_ent["parent_id"] == calc_ent["id"]

    # 5. Verify database records are persisted
    db_entities = db_session.query(CodeEntity).filter(CodeEntity.file_id == file_record.id).all()
    assert len(db_entities) == 2

    # 6. Verify extraction clean re-run deletes old ones
    response_rerun = client.post(f"/api/v1/files/{file_record.id}/extract")
    assert response_rerun.status_code == 200
    assert len(response_rerun.json()) == 2
    assert db_session.query(CodeEntity).filter(CodeEntity.file_id == file_record.id).count() == 2
