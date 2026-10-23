"""Pytest configuration and shared test fixtures with isolated SQLite and temporary storage."""

from pathlib import Path
from typing import Generator
import pytest
import sqlite3

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import get_db, init_db
from app.main import app
from app.storage.local import LocalFileSystemStorage


@pytest.fixture
def isolated_storage_dir(tmp_path: Path) -> Path:
    """Create and return a temporary directory for local file storage."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def test_db_conn(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Provide an isolated, schema-initialized SQLite database connection for unit tests."""
    db_file = tmp_path / "test_cloud_backup.db"
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def local_storage(isolated_storage_dir: Path) -> LocalFileSystemStorage:
    """Provide a LocalFileSystemStorage driver operating inside an isolated temp dir."""
    return LocalFileSystemStorage(base_path=str(isolated_storage_dir))


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> Generator[TestClient, None, None]:
    """TestClient fixture connected to an isolated test database and temp storage."""
    db_path = tmp_path / "client_test.db"
    storage_dir = tmp_path / "client_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Monkeypatch settings
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_PATH", str(storage_dir))
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")

    # Initialize test database
    test_conn = sqlite3.connect(str(db_path), check_same_thread=False)
    test_conn.row_factory = sqlite3.Row
    test_conn.execute("PRAGMA foreign_keys = ON;")
    init_db(test_conn)

    def override_get_db():
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    test_conn.close()
