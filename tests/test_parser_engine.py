import pytest
import uuid
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.services.parser import ParserService, ParserFactory
from app.services.repository import RepositoryService
from app.models.file import File
from app.core.exceptions import RepositoryImportError


def test_parse_success_multi_languages():
    # Python
    py_code = b"def greet():\n    print('hello')"
    rep = ParserService.parse_file_content(py_code, "hello.py", "hello.py", "Python")
    assert rep.status == "success"
    assert rep.syntax_errors == 0
    assert rep.root_node is not None
    assert rep.root_node.type == "module"
    
    # JavaScript
    js_code = b"function greet() { console.log('hello'); }"
    rep = ParserService.parse_file_content(js_code, "hello.js", "hello.js", "JavaScript")
    assert rep.status == "success"
    assert rep.root_node.type == "program"

    # Go
    go_code = b"package main\nfunc main() {}"
    rep = ParserService.parse_file_content(go_code, "main.go", "main.go", "Go")
    assert rep.status == "success"
    assert rep.root_node.type == "source_file"

    # Rust
    rs_code = b"fn main() { println!(\"hello\"); }"
    rep = ParserService.parse_file_content(rs_code, "main.rs", "main.rs", "Rust")
    assert rep.status == "success"
    assert rep.root_node.type == "source_file"


def test_parse_typescript_vs_tsx():
    # Verify tsx file loads TSX language
    tsx_lang = ParserFactory.get_language("TypeScript", "tsx")
    ts_lang = ParserFactory.get_language("TypeScript", "ts")
    
    # TSX and TS use different internal grammars from tree-sitter-typescript
    assert tsx_lang is not None
    assert ts_lang is not None
    assert tsx_lang != ts_lang


def test_parse_syntax_error():
    # Incomplete python expression
    bad_py = b"def greet("
    rep = ParserService.parse_file_content(bad_py, "hello.py", "hello.py", "Python")
    assert rep.status == "warning"
    assert rep.syntax_errors > 0
    assert rep.root_node is not None
    
    # Flat serialization checks
    data = rep.to_dict()
    assert data["status"] == "warning"
    assert data["syntax_errors_count"] > 0
    assert len(data["nodes"]) > 0


def test_parse_empty_file():
    rep = ParserService.parse_file_content(b"", "empty.py", "empty.py", "Python")
    assert rep.status == "success"
    assert rep.root_node is None
    assert rep.syntax_errors == 0


def test_parse_endpoint_integration(client: TestClient, db_session: Session, tmp_path):
    # 1. Create a dummy file on disk
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    file_path = workspace_dir / "test.py"
    file_path.write_text("a = 1 + 2")

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
        relative_path="test.py",
        filename="test.py",
        extension="py",
        language="Python",
        depth=0,
        size_bytes=9,
        last_modified=datetime.fromtimestamp(os.path.getmtime(str(file_path)))
    )
    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    # 3. Call REST Parse API
    response = client.post(f"/api/v1/files/{file_record.id}/parse")
    
    # 4. Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.py"
    assert data["language"] == "Python"
    assert data["status"] == "success"
    assert data["syntax_errors_count"] == 0
    assert "nodes" in data
    assert len(data["nodes"]) > 0
    
    # Verify node structure
    root_node_id = data["root_node_id"]
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    assert root_node_id in nodes_by_id
    assert nodes_by_id[root_node_id]["type"] == "module"


def test_parse_endpoint_file_not_found(client: TestClient):
    fake_id = uuid.uuid4()
    response = client.post(f"/api/v1/files/{fake_id}/parse")
    assert response.status_code == 404
