"""
Pytest Configuration and Fixtures
Konfiguracja testow i wspolne fixtures
"""

import pytest
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock

# Dodaj sciezke do backendu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smart_parser import ParsedLog


# --- FIXTURES: Dane testowe ---

@pytest.fixture
def sample_log_dict() -> Dict[str, Any]:
    """Pojedynczy log jako slownik"""
    return {
        'timestamp': '2024-01-26T20:30:00Z',
        'source': 'test-source',
        'source_type': 'file',
        'severity': 'INFO',
        'event_type': 'SELECT',
        'message': 'SELECT * FROM users',
        'raw': 'SELECT * FROM users WHERE id = 1',
        'table_name': 'users'
    }


@pytest.fixture
def sample_logs_list() -> List[Dict[str, Any]]:
    """Lista logow testowych jako slowniki"""
    return [
        {
            'timestamp': '2024-01-26T20:30:00Z',
            'source': 'mysql-main',
            'source_type': 'mysql',
            'severity': 'INFO',
            'event_type': 'SELECT',
            'message': 'SELECT * FROM users',
            'raw': 'SELECT * FROM users'
        },
        {
            'timestamp': '2024-01-26T20:30:01Z',
            'source': 'mysql-main',
            'source_type': 'mysql',
            'severity': 'INFO',
            'event_type': 'INSERT',
            'message': 'INSERT INTO orders',
            'raw': 'INSERT INTO orders VALUES (1)'
        },
        {
            'timestamp': '2024-01-26T20:30:02Z',
            'source': 'app-log',
            'source_type': 'file',
            'severity': 'ERROR',
            'event_type': 'ERROR',
            'message': 'Database connection failed',
            'raw': '[ERROR] Database connection failed'
        },
        {
            'timestamp': '2024-01-26T20:30:03Z',
            'source': 'frontend',
            'source_type': 'frontend',
            'severity': 'WARNING',
            'event_type': 'LOG',
            'message': 'API response slow',
            'raw': '[WARN] API response slow'
        }
    ]


@pytest.fixture
def sample_parsed_logs() -> List[ParsedLog]:
    """Lista ParsedLog do testow"""
    return [
        ParsedLog(
            raw="SELECT * FROM users",
            timestamp="2024-01-26T20:30:00",
            source="mysql-main",
            event_type="SELECT",
            severity="INFO",
            table_name="users"
        ),
        ParsedLog(
            raw="INSERT INTO orders VALUES (1)",
            timestamp="2024-01-26T20:30:01",
            source="mysql-main",
            event_type="INSERT",
            severity="INFO",
            table_name="orders"
        ),
        ParsedLog(
            raw="[ERROR] Database connection failed",
            timestamp="2024-01-26T20:30:02",
            source="app-log",
            event_type="ERROR",
            severity="ERROR"
        )
    ]


@pytest.fixture
def many_sample_logs() -> List[Dict[str, Any]]:
    """Duza lista logow do testow paginacji"""
    logs = []
    for i in range(100):
        severity = 'ERROR' if i % 10 == 0 else 'INFO'
        event_type = ['SELECT', 'INSERT', 'UPDATE', 'DELETE'][i % 4]
        logs.append({
            'timestamp': f'2024-01-26T20:{i//60:02d}:{i%60:02d}Z',
            'source': f'source-{i % 5}',
            'source_type': 'mysql',
            'severity': severity,
            'event_type': event_type,
            'message': f'Log message {i}',
            'raw': f'Raw log {i}'
        })
    return logs


# --- FIXTURES: Mocks ---

@pytest.fixture
def mock_elasticsearch():
    """Mock dla Elasticsearch storage"""
    mock = MagicMock()
    mock.is_connected = True
    mock.save_log = AsyncMock(return_value=True)
    mock.get_logs = AsyncMock(return_value=[])
    mock.search_logs = AsyncMock(return_value={'logs': [], 'total': 0})
    mock.delete_all_logs = AsyncMock(return_value=True)
    mock.get_stats = AsyncMock(return_value={'total': 0, 'by_source': {}})
    return mock


@pytest.fixture
def mock_mongodb():
    """Mock dla MongoDB"""
    mock = MagicMock()
    mock.test_connection.return_value = True
    mock.collect.return_value = []
    return mock


# --- FIXTURES: FastAPI TestClient ---

@pytest.fixture
def test_client():
    """TestClient dla FastAPI"""
    from fastapi.testclient import TestClient
    
    # Import app
    import main
    
    # Reset stanu - sources musi byc slownikiem!
    main.all_logs = []
    main.sources = {}
    
    client = TestClient(main.app)
    return client


@pytest.fixture
def test_client_with_logs(test_client, sample_logs_list):
    """TestClient z zaladowanymi logami"""
    import main
    main.all_logs = sample_logs_list.copy()
    return test_client


@pytest.fixture
def test_client_with_many_logs(test_client, many_sample_logs):
    """TestClient z duza iloscia logow"""
    import main
    main.all_logs = many_sample_logs.copy()
    return test_client


# --- FIXTURES: Pliki tymczasowe ---

@pytest.fixture
def temp_log_file(tmp_path):
    """Tymczasowy plik logu"""
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "[2024-01-26 20:30:00] INFO: Application started\n"
        "[2024-01-26 20:30:01] ERROR: Connection failed\n"
        "[2024-01-26 20:30:02] INFO: Retrying...\n"
    )
    return str(log_file)


@pytest.fixture
def temp_log_directory(tmp_path):
    """Tymczasowy katalog z plikami logow"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    (log_dir / "app.log").write_text("App log line 1\nApp log line 2\n")
    (log_dir / "error.log").write_text("ERROR: Something went wrong\n")
    (log_dir / "access.log").write_text("192.168.1.1 - GET /api/users 200\n")
    
    return str(log_dir)


# --- HELPER FUNCTIONS ---

def create_log_dict(
    message: str = "Test message",
    severity: str = "INFO",
    event_type: str = "OTHER",
    source: str = "test",
    source_type: str = "file"
) -> Dict[str, Any]:
    """Helper do tworzenia logow testowych"""
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source': source,
        'source_type': source_type,
        'severity': severity,
        'event_type': event_type,
        'message': message,
        'raw': f'[{severity}] {message}'
    }
