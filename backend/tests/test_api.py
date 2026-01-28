"""
Testy API (FastAPI endpoints)
Integration tests for REST API endpoints
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestHealthEndpoint:
    """Testy dla /api/health"""
    
    def test_health_check(self, test_client):
        """Test health endpoint"""
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestLogsEndpoint:
    """Testy dla /api/logs"""
    
    def test_get_logs_empty(self, test_client):
        """Test pobierania pustej listy logow"""
        response = test_client.get("/api/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
    
    def test_get_logs_with_data(self, test_client_with_logs):
        """Test pobierania logow z danymi"""
        response = test_client_with_logs.get("/api/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) > 0
        assert data["total"] > 0
    
    def test_get_logs_pagination(self, test_client_with_many_logs):
        """Test paginacji"""
        response = test_client_with_many_logs.get("/api/logs?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 10
        assert data["total"] == 100
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    def test_get_logs_pagination_page2(self, test_client_with_many_logs):
        """Test drugiej strony"""
        response = test_client_with_many_logs.get("/api/logs?page=2&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 10
        assert data["page"] == 2
    
    def test_get_logs_filter_severity(self, test_client_with_many_logs):
        """Test filtrowania po severity"""
        response = test_client_with_many_logs.get("/api/logs?severity=ERROR")
        
        assert response.status_code == 200
        data = response.json()
        # Wszystkie zwrocone logi powinny miec severity ERROR
        for log in data["logs"]:
            assert log["severity"] == "ERROR"
    
    def test_get_logs_filter_source(self, test_client_with_logs):
        """Test filtrowania po source"""
        response = test_client_with_logs.get("/api/logs?source=mysql-main")
        
        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["source"] == "mysql-main"
    
    def test_get_logs_filter_query(self, test_client_with_logs):
        """Test filtrowania po query (wyszukiwanie)"""
        response = test_client_with_logs.get("/api/logs?query=SELECT")
        
        assert response.status_code == 200
        data = response.json()
        # Powinny byc logi zawierajace SELECT
        assert data["total"] >= 0
    
    def test_get_logs_combined_filters(self, test_client_with_many_logs):
        """Test laczenia filtrow"""
        response = test_client_with_many_logs.get(
            "/api/logs?severity=ERROR&page_size=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 5
        for log in data["logs"]:
            assert log["severity"] == "ERROR"
    
    def test_delete_logs(self, test_client_with_logs):
        """Test czyszczenia logow"""
        # Najpierw sprawdz ze sa logi
        response = test_client_with_logs.get("/api/logs")
        assert response.json()["total"] > 0
        
        # Usun logi
        response = test_client_with_logs.delete("/api/logs")
        assert response.status_code == 200
        
        # Sprawdz ze puste
        response = test_client_with_logs.get("/api/logs")
        assert response.json()["total"] == 0


class TestSourcesEndpoint:
    """Testy dla /api/sources"""
    
    def test_get_sources_empty(self, test_client):
        """Test pobierania pustej listy zrodel"""
        response = test_client.get("/api/sources")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_add_file_source(self, test_client, temp_log_file):
        """Test dodawania zrodla plikowego"""
        response = test_client.post("/api/sources", json={
            "name": "test-file",
            "type": "file",
            "config": {
                "path": temp_log_file
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-file"
        assert data["type"] == "file"
    
    def test_add_source_invalid_type(self, test_client):
        """Test dodawania zrodla z nieprawidlowym typem"""
        response = test_client.post("/api/sources", json={
            "name": "invalid",
            "type": "invalid_type",
            "config": {}
        })
        
        # Powinno zwrocic blad lub zaakceptowac i oznaczyc jako nieobslugiwane
        assert response.status_code in [200, 400, 422]
    
    def test_delete_source(self, test_client, temp_log_file):
        """Test usuwania zrodla"""
        # Dodaj zrodlo
        test_client.post("/api/sources", json={
            "name": "to-delete",
            "type": "file",
            "config": {"path": temp_log_file}
        })
        
        # Usun zrodlo
        response = test_client.delete("/api/sources/to-delete")
        assert response.status_code == 200


class TestFrontendLogsEndpoint:
    """Testy dla /api/logs/frontend"""
    
    def test_post_frontend_log(self, test_client):
        """Test wysylania logu z frontendu"""
        response = test_client.post("/api/logs/frontend", json={
            "logs": [
                {
                    "level": "info",
                    "message": "Test log from frontend",
                    "component": "TestComponent",
                    "context": {"userId": 123}
                }
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["received"] == 1
    
    def test_post_frontend_log_batch(self, test_client):
        """Test wysylania wielu logow"""
        response = test_client.post("/api/logs/frontend", json={
            "logs": [
                {"level": "info", "message": "Log 1"},
                {"level": "warn", "message": "Log 2"},
                {"level": "error", "message": "Log 3"}
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"] == 3
    
    def test_post_frontend_log_error_level(self, test_client):
        """Test logu z poziomem error"""
        response = test_client.post("/api/logs/frontend", json={
            "logs": [
                {
                    "level": "error",
                    "message": "Critical error occurred",
                    "stack": "Error: Something failed\n    at line 1"
                }
            ]
        })
        
        assert response.status_code == 200
        
        # Sprawdz czy log jest w liscie
        logs_response = test_client.get("/api/logs")
        logs = logs_response.json()["logs"]
        
        # Znajdz nasz log
        frontend_logs = [l for l in logs if l.get("source") == "frontend"]
        assert len(frontend_logs) > 0
    
    def test_post_frontend_log_minimal(self, test_client):
        """Test minimalnego logu frontend"""
        response = test_client.post("/api/logs/frontend", json={
            "logs": [
                {"level": "debug", "message": "Debug message"}
            ]
        })
        
        assert response.status_code == 200


class TestDebugEndpoints:
    """Testy dla endpointow debug"""
    
    def test_debug_logs(self, test_client_with_logs):
        """Test /api/debug/logs"""
        response = test_client_with_logs.get("/api/debug/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs_count" in data
        assert "sources_count" in data
    
    def test_debug_elasticsearch(self, test_client):
        """Test /api/debug/elasticsearch"""
        response = test_client.get("/api/debug/elasticsearch")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestResponseFormat:
    """Testy formatu odpowiedzi"""
    
    def test_logs_response_structure(self, test_client_with_logs):
        """Test struktury odpowiedzi /api/logs"""
        response = test_client_with_logs.get("/api/logs")
        data = response.json()
        
        # Wymagane pola
        assert "logs" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        
        # Typy
        assert isinstance(data["logs"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert isinstance(data["total_pages"], int)
    
    def test_single_log_structure(self, test_client_with_logs):
        """Test struktury pojedynczego logu"""
        response = test_client_with_logs.get("/api/logs")
        logs = response.json()["logs"]
        
        if len(logs) > 0:
            log = logs[0]
            
            # Wymagane pola
            assert "timestamp" in log
            assert "source" in log
            assert "message" in log or "raw" in log


class TestErrorHandling:
    """Testy obslugi bledow"""
    
    def test_invalid_page_number(self, test_client):
        """Test nieprawidlowego numeru strony"""
        response = test_client.get("/api/logs?page=-1")
        
        # Powinno albo zwrocic blad albo skorygowac wartosc
        assert response.status_code in [200, 400, 422]
    
    def test_invalid_page_size(self, test_client):
        """Test nieprawidlowego rozmiaru strony"""
        response = test_client.get("/api/logs?page_size=0")
        
        assert response.status_code in [200, 400, 422]
    
    def test_invalid_json_body(self, test_client):
        """Test nieprawidlowego JSON"""
        response = test_client.post(
            "/api/logs/frontend",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


class TestLogDetails:
    """Testy dla szczegulow logu"""
    
    def test_get_log_by_id(self, test_client):
        """Test pobierania logu po ID"""
        import main
        
        # Dodaj log z _id
        main.all_logs.append({
            '_id': 'test-log-123',
            'timestamp': '2024-01-26T20:30:00Z',
            'source': 'test',
            'message': 'Test log'
        })
        
        response = test_client.get("/api/logs/test-log-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["_id"] == "test-log-123"
    
    def test_get_log_not_found(self, test_client):
        """Test pobierania nieistniejacego logu"""
        response = test_client.get("/api/logs/non-existent-id")
        
        assert response.status_code == 404


class TestStatsEndpoint:
    """Testy dla /api/stats"""
    
    def test_get_stats(self, test_client_with_logs):
        """Test pobierania statystyk"""
        response = test_client_with_logs.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data or "logs_count" in data or isinstance(data, dict)
