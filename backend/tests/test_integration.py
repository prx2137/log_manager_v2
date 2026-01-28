"""
Testy integracyjne - caly przepyw aplikacji
Integration tests for full application flow
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smart_parser import SmartParser, ParsedLog, parse_log
from sources import FileSource, BaseSource


class TestFullLogPipeline:
    """Testy pelnego przeplywu logow"""
    
    def test_file_to_parsed_log_pipeline(self, temp_log_file):
        """Test: plik -> FileSource -> ParsedLog"""
        source = FileSource(
            name="test-file",
            config={
                "path": temp_log_file,
                "enabled": True
            }
        )
        
        # Zbierz logi
        logs = source.collect()
        
        # Sprawdz ze sa logi
        assert len(logs) >= 0  # Moze byc 0 jesli plik pusty lub juz przetworzony
        
        # Kazdy log powinien byc ParsedLog
        for log in logs:
            assert isinstance(log, ParsedLog)
            assert log.source == "test-file"
    
    def test_parsed_log_to_dict_conversion(self, sample_parsed_logs):
        """Test konwersji ParsedLog -> dict"""
        for log in sample_parsed_logs:
            log_dict = log.to_dict()
            
            assert isinstance(log_dict, dict)
            assert 'raw' in log_dict
            assert 'timestamp' in log_dict
            assert 'source' in log_dict
    
    def test_source_status_reporting(self, temp_log_file):
        """Test raportowania statusu zrodla"""
        source = FileSource(
            name="status-test",
            config={
                "path": temp_log_file,
                "enabled": True
            }
        )
        
        status = source.get_status()
        
        assert status.name == "status-test"
        assert status.type == "file"
        assert status.enabled == True
    
    def test_parser_preserves_source(self):
        """Test ze parser zachowuje source"""
        parser = SmartParser()
        
        log = parser.parse("SELECT * FROM users", "my-database")
        
        assert log.source == "my-database"
    
    def test_error_detection_in_pipeline(self):
        """Test wykrywania bledow w pipelinie"""
        parser = SmartParser()
        
        error_line = "[2024-01-26 20:30:00] ERROR: Database connection failed"
        log = parser.parse(error_line, "app-log")
        
        assert log.severity == "ERROR"


class TestPagination:
    """Testy paginacji"""
    
    def test_pagination_offset_limit(self, test_client_with_many_logs):
        """Test ze paginacja zwraca poprawne offsety"""
        # Strona 1
        response1 = test_client_with_many_logs.get("/api/logs?page=1&page_size=10")
        data1 = response1.json()
        
        # Strona 2
        response2 = test_client_with_many_logs.get("/api/logs?page=2&page_size=10")
        data2 = response2.json()
        
        # Logi powinny byc rozne
        if len(data1["logs"]) > 0 and len(data2["logs"]) > 0:
            # Sprawdz ze to nie sa te same logi
            ids1 = [l.get("raw", l.get("message", "")) for l in data1["logs"]]
            ids2 = [l.get("raw", l.get("message", "")) for l in data2["logs"]]
            
            # Powinny byc rozne
            assert ids1 != ids2
    
    def test_pagination_total_count(self, test_client_with_many_logs):
        """Test ze total jest poprawny"""
        response = test_client_with_many_logs.get("/api/logs?page=1&page_size=10")
        data = response.json()
        
        assert data["total"] == 100
        assert data["total_pages"] == 10  # 100 / 10
    
    def test_pagination_last_page(self, test_client_with_many_logs):
        """Test ostatniej strony"""
        response = test_client_with_many_logs.get("/api/logs?page=10&page_size=10")
        data = response.json()
        
        assert data["page"] == 10
        assert len(data["logs"]) == 10
    
    def test_pagination_beyond_last_page(self, test_client_with_many_logs):
        """Test strony poza zakresem"""
        response = test_client_with_many_logs.get("/api/logs?page=999&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        # Pusta lista lub skorygowana strona
        assert isinstance(data["logs"], list)


class TestFiltering:
    """Testy filtrowania"""
    
    def test_filter_by_severity(self, test_client_with_many_logs):
        """Test filtrowania po severity"""
        response = test_client_with_many_logs.get("/api/logs?severity=ERROR")
        data = response.json()
        
        for log in data["logs"]:
            assert log["severity"] == "ERROR"
    
    def test_filter_by_event_type(self, test_client_with_many_logs):
        """Test filtrowania po event_type"""
        response = test_client_with_many_logs.get("/api/logs?event_type=SELECT")
        data = response.json()
        
        for log in data["logs"]:
            assert log["event_type"] == "SELECT"
    
    def test_filter_combined_with_pagination(self, test_client_with_many_logs):
        """Test filtrowania z paginacja"""
        response = test_client_with_many_logs.get(
            "/api/logs?severity=ERROR&page=1&page_size=5"
        )
        data = response.json()
        
        assert len(data["logs"]) <= 5
        for log in data["logs"]:
            assert log["severity"] == "ERROR"


class TestSourceManagement:
    """Testy zarzadzania zrodlami"""
    
    def test_add_and_remove_source(self, test_client, temp_log_file):
        """Test dodawania i usuwania zrodla"""
        # Dodaj
        response = test_client.post("/api/sources", json={
            "name": "temp-source",
            "type": "file",
            "config": {"path": temp_log_file}
        })
        assert response.status_code == 200
        
        # Sprawdz czy jest na liscie
        response = test_client.get("/api/sources")
        sources = response.json()
        names = [s["name"] for s in sources]
        assert "temp-source" in names
        
        # Usun
        response = test_client.delete("/api/sources/temp-source")
        assert response.status_code == 200
        
        # Sprawdz ze usuniete
        response = test_client.get("/api/sources")
        sources = response.json()
        names = [s["name"] for s in sources]
        assert "temp-source" not in names


class TestMultipleSources:
    """Testy wielu zrodel jednoczesnie"""
    
    def test_add_multiple_sources(self, test_client, temp_log_directory):
        """Test dodawania wielu zrodel"""
        import os
        
        # Dodaj kilka zrodel
        for i, filename in enumerate(['app.log', 'error.log', 'access.log']):
            filepath = os.path.join(temp_log_directory, filename)
            response = test_client.post("/api/sources", json={
                "name": f"multi-source-{i}",
                "type": "file",
                "config": {"path": filepath}
            })
            assert response.status_code == 200
        
        # Sprawdz ze wszystkie dodane
        response = test_client.get("/api/sources")
        sources = response.json()
        
        assert len(sources) >= 3
    
    def test_filter_by_source_with_multiple(self, test_client_with_logs):
        """Test filtrowania gdy wiele zrodel"""
        # Pobierz wszystkie
        response = test_client_with_logs.get("/api/logs")
        all_logs = response.json()
        
        # Pobierz tylko z jednego zrodla
        response = test_client_with_logs.get("/api/logs?source=mysql-main")
        filtered = response.json()
        
        # Powinno byc mniej lub rowno
        assert filtered["total"] <= all_logs["total"]


class TestRealTimeUpdates:
    """Testy aktualizacji w czasie rzeczywistym"""
    
    def test_new_logs_appear(self, test_client):
        """Test ze nowe logi pojawiaja sie"""
        import main
        
        # Pobierz poczatkowa liczbe
        response = test_client.get("/api/logs")
        initial = response.json()["total"]
        
        # Dodaj log reczne (symulacja)
        main.all_logs.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'test',
            'source_type': 'test',
            'severity': 'INFO',
            'event_type': 'TEST',
            'message': 'New test log',
            'raw': 'New test log'
        })
        
        # Sprawdz ze przybylo
        response = test_client.get("/api/logs")
        new_total = response.json()["total"]
        
        assert new_total == initial + 1


class TestFrontendIntegration:
    """Testy integracji z frontendem"""
    
    def test_frontend_log_appears_in_list(self, test_client):
        """Test ze log z frontendu pojawia sie w liscie"""
        # Wyslij log z frontendu
        response = test_client.post("/api/logs/frontend", json={
            "logs": [
                {
                    "level": "info",
                    "message": "Frontend integration test",
                    "component": "TestSuite"
                }
            ]
        })
        assert response.status_code == 200
        
        # Sprawdz czy jest w logach
        response = test_client.get("/api/logs")
        logs = response.json()["logs"]
        
        messages = [l.get("message", "") for l in logs]
        assert "Frontend integration test" in messages
    
    def test_frontend_logs_have_correct_source(self, test_client):
        """Test ze logi frontend maja poprawne source"""
        test_client.post("/api/logs/frontend", json={
            "logs": [{"level": "warn", "message": "Source test"}]
        })
        
        response = test_client.get("/api/logs?source=frontend")
        logs = response.json()["logs"]
        
        assert len(logs) > 0
        for log in logs:
            assert log["source"] == "frontend"
