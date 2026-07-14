import os
import shutil
import pytest
from sqlalchemy.orm import Session
from app.services.repository import RepositoryService
from app.services.scanner import ScannerService
from app.models.file import File
from app.core.exceptions import RepositoryImportError


def test_scan_repository_success(db_session: Session, tmp_path):
    # 1. Create a mock filesystem workspace
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Supported files
    (repo_dir / "main.py").write_text("print('hello')")  # Size 14, depth 0
    app_dir = repo_dir / "app"
    app_dir.mkdir()
    (app_dir / "api.go").write_text("package main")  # Size 12, depth 1
    (app_dir / "utils.js").write_text("console.log('hi')")  # Size 17, depth 1
    
    # Ignored filenames & extensions
    (repo_dir / "package-lock.json").write_text("{}")
    (repo_dir / "image.png").write_bytes(b"\x00\x01")
    (app_dir / "notes.txt").write_text("some notes")
    
    # Ignored directories (should be skipped completely)
    node_modules = repo_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "index.js").write_text("console.log()")
    
    venv_dir = repo_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "script.py").write_text("print()")

    # 2. Setup mock DB repository
    url = "https://github.com/Reddy0402/software-dna"
    repo_record = RepositoryService.create_pending_record(db_session, url)
    repo_record.clone_status = "completed"
    repo_record.local_path = str(repo_dir)
    db_session.commit()

    # 3. Execute Scan
    summary = ScannerService.scan_repository(db_session, repo_record.id)

    # 4. Assert summary output
    assert summary["repository_id"] == repo_record.id
    # We scanned main.py, api.go, utils.js, package-lock.json, image.png, notes.txt (6 files).
    # Files inside node_modules/ and .venv/ should not be scanned at all because we prune in-place!
    assert summary["total_files_scanned"] == 6
    assert summary["supported_files_found"] == 3
    assert summary["language_distribution"] == {"Python": 1, "Go": 1, "JavaScript": 1}

    # 5. Assert Database Records
    files = db_session.query(File).filter(File.repository_id == repo_record.id).all()
    assert len(files) == 3
    
    file_map = {f.filename: f for f in files}
    assert "main.py" in file_map
    assert "api.go" in file_map
    assert "utils.js" in file_map

    main_py = file_map["main.py"]
    assert main_py.relative_path == "main.py"
    assert main_py.depth == 0
    assert main_py.size_bytes == 14
    assert main_py.language == "Python"
    assert main_py.extension == "py"

    api_go = file_map["api.go"]
    assert api_go.relative_path == "app/api.go"
    assert api_go.depth == 1
    assert api_go.size_bytes == 12
    assert api_go.language == "Go"


def test_scan_repository_symbolic_links_ignored(db_session: Session, tmp_path):
    # Setup folders
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("print('hello')")
    
    # Create a link pointing to main.py
    link_path = os.path.join(str(repo_dir), "link.py")
    try:
        os.symlink(os.path.join(str(repo_dir), "main.py"), link_path)
        symlink_supported = True
    except (OSError, NotImplementedError):
        # Symlinks require admin privileges on Windows; fallback if not supported
        symlink_supported = False

    url = "https://github.com/Reddy0402/software-dna"
    repo_record = RepositoryService.create_pending_record(db_session, url)
    repo_record.clone_status = "completed"
    repo_record.local_path = str(repo_dir)
    db_session.commit()

    summary = ScannerService.scan_repository(db_session, repo_record.id)
    
    # Assert database
    files = db_session.query(File).filter(File.repository_id == repo_record.id).all()
    if symlink_supported:
        # Symbolic link should be skipped, only main.py is scanned
        assert len(files) == 1
        assert files[0].filename == "main.py"
    else:
        assert len(files) == 1


def test_scan_repository_cleanup_prev_run(db_session: Session, tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("print()")

    url = "https://github.com/Reddy0402/software-dna"
    repo_record = RepositoryService.create_pending_record(db_session, url)
    repo_record.clone_status = "completed"
    repo_record.local_path = str(repo_dir)
    db_session.commit()

    # Run scan 1
    ScannerService.scan_repository(db_session, repo_record.id)
    assert db_session.query(File).filter(File.repository_id == repo_record.id).count() == 1

    # Modify file list to be empty and run scan 2
    os.remove(repo_dir / "main.py")
    ScannerService.scan_repository(db_session, repo_record.id)
    
    # Assert database contains 0 entries (previous records deleted)
    assert db_session.query(File).filter(File.repository_id == repo_record.id).count() == 0


def test_scan_repository_invalid_states(db_session: Session):
    url = "https://github.com/Reddy0402/software-dna"
    repo_record = RepositoryService.create_pending_record(db_session, url)
    
    # Cannot scan if not completed clone
    repo_record.clone_status = "pending"
    db_session.commit()

    with pytest.raises(RepositoryImportError):
        ScannerService.scan_repository(db_session, repo_record.id)
