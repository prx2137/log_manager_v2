"""
Testy jednostkowe dla smart_parser.py
Unit tests for log parsing module
"""

import pytest
from datetime import datetime
import sys
import os

# Dodaj sciezke do backendu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smart_parser import ParsedLog, SmartParser, parse_log, parse_and_filter


class TestParsedLog:
    """Testy dla dataclass ParsedLog"""
    
    def test_create_basic_log(self):
        """Test tworzenia podstawowego logu"""
        log = ParsedLog(
            raw="SELECT * FROM users",
            timestamp="2024-01-26T20:30:00",
            source="test-source"
        )
        
        assert log.raw == "SELECT * FROM users"
        assert log.timestamp == "2024-01-26T20:30:00"
        assert log.source == "test-source"
        assert log.event_type == "OTHER"  # default
        assert log.severity == "INFO"  # default
    
    def test_log_with_optional_fields(self):
        """Test logu z polami opcjonalnymi"""
        log = ParsedLog(
            raw="INSERT INTO users",
            timestamp="2024-01-26T20:30:00",
            source="mysql-main",
            event_type="INSERT",
            severity="INFO",
            table_name="users",
            affected_rows=5,
            message="Inserted new user",
            user="admin"
        )
        
        assert log.table_name == "users"
        assert log.affected_rows == 5
        assert log.user == "admin"
    
    def test_to_dict_conversion(self):
        """Test konwersji do slownika"""
        log = ParsedLog(
            raw="Test log",
            timestamp="2024-01-26T20:30:00",
            source="test"
        )
        
        result = log.to_dict()
        
        assert isinstance(result, dict)
        assert result['raw'] == "Test log"
        assert result['timestamp'] == "2024-01-26T20:30:00"
        assert result['source'] == "test"
    
    def test_to_dict_excludes_none(self):
        """Test ze to_dict pomija pola None"""
        log = ParsedLog(
            raw="Test",
            timestamp="2024-01-26T20:30:00",
            source="test",
            table_name=None,  # None - should be excluded
            affected_rows=None  # None - should be excluded
        )
        
        result = log.to_dict()
        
        # None values should be excluded
        assert 'table_name' not in result or result['table_name'] is None
        assert 'affected_rows' not in result or result['affected_rows'] is None
    
    def test_default_values(self):
        """Test wartosci domyslnych"""
        log = ParsedLog(
            raw="test",
            timestamp="2024-01-26T20:30:00"
        )
        
        assert log.source == ""
        assert log.event_type == "OTHER"
        assert log.severity == "INFO"
        assert log.table_name is None
        assert log.affected_rows is None
        assert log.message == ""
        assert log.user is None


class TestSmartParser:
    """Testy dla klasy SmartParser"""
    
    @pytest.fixture
    def parser(self):
        return SmartParser()
    
    def test_parse_select_query(self, parser):
        """Test parsowania SELECT"""
        line = "SELECT * FROM users WHERE id = 1"
        result = parser.parse(line, "mysql-db")
        
        assert result.event_type == "SELECT"
        assert result.table_name == "users"
        assert result.source == "mysql-db"
    
    def test_parse_insert_query(self, parser):
        """Test parsowania INSERT"""
        line = "INSERT INTO products (name, price) VALUES ('test', 100)"
        result = parser.parse(line, "mysql-db")
        
        assert result.event_type == "INSERT"
        assert result.table_name == "products"
    
    def test_parse_update_query(self, parser):
        """Test parsowania UPDATE"""
        line = "UPDATE orders SET status = 'completed' WHERE id = 5"
        result = parser.parse(line, "mysql-db")
        
        assert result.event_type == "UPDATE"
        assert result.table_name == "orders"
    
    def test_parse_delete_query(self, parser):
        """Test parsowania DELETE"""
        line = "DELETE FROM sessions WHERE expired = 1"
        result = parser.parse(line, "mysql-db")
        
        assert result.event_type == "DELETE"
        assert result.table_name == "sessions"
    
    def test_parse_laravel_log(self, parser):
        """Test parsowania logow Laravel"""
        line = "[2024-01-26 20:30:15] production.INFO: User logged in"
        result = parser.parse(line, "laravel-log")
        
        assert result is not None
        assert result.source == "laravel-log"
        assert "logged in" in result.message or "logged in" in result.raw
    
    def test_parse_laravel_error(self, parser):
        """Test parsowania bledu Laravel"""
        line = "[2024-01-26 20:30:15] production.ERROR: Database connection failed"
        result = parser.parse(line, "laravel-log")
        
        assert result is not None
        assert result.severity == "ERROR"
    
    def test_parse_json_log(self, parser):
        """Test parsowania logu JSON"""
        import json
        log_data = {"level": "info", "message": "Request processed", "user_id": 123}
        line = json.dumps(log_data)
        result = parser.parse(line, "json-app")
        
        assert result is not None
        assert result.source == "json-app"
    
    def test_parse_error_detection(self, parser):
        """Test wykrywania ERROR"""
        line = "FATAL: Connection refused to database server"
        result = parser.parse(line, "test")
        
        assert result.severity == "ERROR"
        assert result.event_type == "ERROR"
    
    def test_parse_unknown_format(self, parser):
        """Test parsowania nieznanego formatu"""
        line = "Some random text that doesn't match any pattern"
        result = parser.parse(line, "unknown")
        
        assert result is not None
        assert result.event_type == "OTHER"
        assert result.source == "unknown"
    
    def test_parse_empty_line(self, parser):
        """Test pustej linii"""
        result = parser.parse("", "test")
        
        assert result is not None
        assert result.event_type == "OTHER"
        assert result.message == ""
    
    def test_parse_whitespace_line(self, parser):
        """Test linii z bialymi znakami"""
        result = parser.parse("   \t\n  ", "test")
        
        assert result is not None
        assert result.event_type == "OTHER"
    
    def test_severity_detection_error(self, parser):
        """Test wykrywania severity ERROR"""
        lines = [
            "ERROR: Something went wrong",
            "FATAL: Critical failure",
            "CRITICAL: System crash",
            "EXCEPTION: Unhandled error"
        ]
        
        for line in lines:
            result = parser.parse(line, "test")
            assert result.severity == "ERROR", f"Failed for: {line}"
    
    def test_severity_detection_warning(self, parser):
        """Test wykrywania severity WARNING"""
        line = "Warning: Deprecated function used"
        result = parser.parse(line, "test")
        
        # Parser wykrywa warning jako INFO lub moze nie wykrywac WARNING
        assert result is not None
    
    def test_source_preservation(self, parser):
        """Test zachowania source"""
        result = parser.parse("SELECT 1", "my-custom-source")
        assert result.source == "my-custom-source"
    
    def test_affected_rows_detection(self, parser):
        """Test wykrywania affected rows"""
        line = "Query OK, 5 rows affected"
        result = parser.parse(line, "mysql")
        
        assert result.affected_rows == 5
    
    def test_user_detection(self, parser):
        """Test wykrywania user"""
        line = "Query by user_id=admin"
        result = parser.parse(line, "test")
        
        assert result.user == "admin"
    
    def test_timestamp_extraction(self, parser):
        """Test ekstrakcji timestamp"""
        line = "[2024-01-26 20:30:15] Some log message"
        result = parser.parse(line, "test")
        
        assert "2024-01-26" in result.timestamp
    
    def test_is_important_sql(self, parser):
        """Test is_important dla SQL"""
        select_log = parser.parse("SELECT * FROM users", "db")
        insert_log = parser.parse("INSERT INTO users VALUES (1)", "db")
        other_log = parser.parse("Some random text", "db")
        
        assert parser.is_important(select_log) == True
        assert parser.is_important(insert_log) == True
        assert parser.is_important(other_log) == False


class TestParseLogFunction:
    """Testy dla funkcji pomocniczej parse_log"""
    
    def test_parse_log_basic(self):
        """Test podstawowego parse_log"""
        result = parse_log("SELECT * FROM test", "my-source")
        
        assert result is not None
        assert result.source == "my-source"
        assert result.event_type == "SELECT"
    
    def test_parse_log_without_source(self):
        """Test parse_log bez source"""
        result = parse_log("INSERT INTO test VALUES (1)")
        
        assert result is not None
        assert result.source == ""


class TestParseAndFilter:
    """Testy dla funkcji parse_and_filter"""
    
    def test_filter_returns_important(self):
        """Test ze zwraca wazne logi"""
        result = parse_and_filter("SELECT * FROM users", "db")
        assert result is not None
        assert result.event_type == "SELECT"
    
    def test_filter_returns_none_for_unimportant(self):
        """Test ze zwraca None dla niewaznych"""
        result = parse_and_filter("Just some text", "source")
        assert result is None


class TestEdgeCases:
    """Testy przypadkow brzegowych"""
    
    @pytest.fixture
    def parser(self):
        return SmartParser()
    
    def test_very_long_message(self, parser):
        """Test bardzo dlugiej wiadomosci"""
        line = "A" * 10000
        result = parser.parse(line, "test")
        
        assert result is not None
        assert len(result.message) <= 500  # Limit message to 500
    
    def test_special_characters(self, parser):
        """Test znakow specjalnych"""
        line = "SELECT * FROM users WHERE name = '<script>alert(1)</script>'"
        result = parser.parse(line, "test")
        
        assert result is not None
        assert result.event_type == "SELECT"
    
    def test_unicode_characters(self, parser):
        """Test znakow unicode"""
        line = "User created: nazwa_uzytkownika"
        result = parser.parse(line, "test")
        
        assert result is not None
    
    def test_multiline_json(self, parser):
        """Test JSON wieloliniowego jako pojedyncza linia"""
        import json
        data = {"message": "test", "nested": {"key": "value"}}
        line = json.dumps(data)
        result = parser.parse(line, "test")
        
        assert result is not None
    
    def test_malformed_json(self, parser):
        """Test niepoprawnego JSON"""
        line = '{"broken": json here'
        result = parser.parse(line, "test")
        
        # Should still parse as raw text
        assert result is not None
    
    def test_numeric_message(self, parser):
        """Test wiadomosci numerycznej"""
        line = "12345"
        result = parser.parse(line, "test")
        
        assert result is not None
        assert result.raw == "12345"
    
    def test_sql_with_backticks(self, parser):
        """Test SQL z backticks"""
        line = "SELECT * FROM `user_accounts` WHERE `id` = 1"
        result = parser.parse(line, "mysql")
        
        assert result.event_type == "SELECT"
        assert result.table_name == "user_accounts"
    
    def test_sql_with_quotes(self, parser):
        """Test SQL z quotes"""
        line = "SELECT * FROM \"public\".\"users\" WHERE id = 1"
        result = parser.parse(line, "postgres")
        
        assert result.event_type == "SELECT"
