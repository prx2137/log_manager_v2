"""
Smart Parser - Uproszczony parser do monitorowania baz danych
Wykrywa tylko: SELECT, INSERT, UPDATE, DELETE, ERROR
Cel: monitorowanie co robią użytkownicy w bazie
"""

import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ParsedLog:
    """Sparsowany log z wykrytym typem zdarzenia"""
    
    # Podstawowe
    raw: str                              # Oryginalny tekst
    timestamp: str                        # ISO format
    source: str = ""                      # Nazwa źródła
    
    # Wykryte
    event_type: str = "OTHER"             # SELECT/INSERT/UPDATE/DELETE/ERROR/OTHER
    severity: str = "INFO"                # INFO/WARNING/ERROR
    
    # SQL
    table_name: Optional[str] = None      # Wykryta tabela
    affected_rows: Optional[int] = None   # Ile wierszy
    
    # Ekstra
    message: str = ""                     # Oczyszczona wiadomość
    user: Optional[str] = None            # User jeśli wykryty
    
    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class SmartParser:
    """
    Uproszczony parser - tylko to co ważne:
    - SELECT, INSERT, UPDATE, DELETE
    - ERROR
    """
    
    # Wzorce SQL
    SQL_PATTERNS = {
        'INSERT': re.compile(r'\bINSERT\s+INTO\s+[`"\']?(\w+)[`"\']?', re.IGNORECASE),
        'UPDATE': re.compile(r'\bUPDATE\s+[`"\']?(\w+)[`"\']?', re.IGNORECASE),
        'DELETE': re.compile(r'\bDELETE\s+FROM\s+[`"\']?(\w+)[`"\']?', re.IGNORECASE),
        'SELECT': re.compile(r'\bSELECT\b.+?\bFROM\s+[`"\']?(\w+)[`"\']?', re.IGNORECASE | re.DOTALL),
    }
    
    # Wzorce błędów
    ERROR_PATTERNS = [
        re.compile(r'\b(ERROR|FATAL|CRITICAL|EXCEPTION)\b', re.IGNORECASE),
        re.compile(r'\b(failed|failure|error|exception)\b', re.IGNORECASE),
    ]
    
    # Wzorzec affected rows
    ROWS_PATTERN = re.compile(r'(\d+)\s*(rows?|records?)\s*(affected|changed|deleted|inserted|updated)', re.IGNORECASE)
    
    # Wzorzec user
    USER_PATTERN = re.compile(r'(?:user[_\s]?(?:id)?|uid|username)[=:\s]+["\']?(\w+)["\']?', re.IGNORECASE)
    
    # Wzorce timestamp
    TIMESTAMP_PATTERNS = [
        # ISO format
        re.compile(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})'),
        # Log format [2024-01-26 20:30:15]
        re.compile(r'\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]'),
        # MySQL format
        re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z?)'),
        # Simple date
        re.compile(r'(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2})'),
    ]
    
    def parse(self, raw: str, source: str = "") -> ParsedLog:
        """Parsuj log i wykryj typ zdarzenia"""
        
        raw = raw.strip()
        if not raw:
            return ParsedLog(
                raw="",
                timestamp=datetime.now().isoformat(),
                source=source,
                event_type="OTHER",
                message=""
            )
        
        # Wykryj timestamp lub użyj aktualnego
        timestamp = self._extract_timestamp(raw)
        
        # Wykryj typ zdarzenia SQL
        event_type = "OTHER"
        table_name = None
        severity = "INFO"
        
        # Sprawdź SQL
        for sql_type, pattern in self.SQL_PATTERNS.items():
            match = pattern.search(raw)
            if match:
                event_type = sql_type
                table_name = match.group(1) if match.groups() else None
                break
        
        # Sprawdź ERROR (nadpisuje jeśli jest)
        for pattern in self.ERROR_PATTERNS:
            if pattern.search(raw):
                severity = "ERROR"
                if event_type == "OTHER":
                    event_type = "ERROR"
                break
        
        # Affected rows
        affected_rows = None
        rows_match = self.ROWS_PATTERN.search(raw)
        if rows_match:
            try:
                affected_rows = int(rows_match.group(1))
            except:
                pass
        
        # User
        user = None
        user_match = self.USER_PATTERN.search(raw)
        if user_match:
            user = user_match.group(1)
        
        # Oczyszczona wiadomość (bez timestampa)
        message = raw
        for pattern in self.TIMESTAMP_PATTERNS:
            message = pattern.sub('', message)
        message = re.sub(r'^\s*[\[\]]+\s*', '', message).strip()
        
        return ParsedLog(
            raw=raw,
            timestamp=timestamp,
            source=source,
            event_type=event_type,
            severity=severity,
            table_name=table_name,
            affected_rows=affected_rows,
            message=message[:500],  # Limit długości
            user=user
        )
    
    def _extract_timestamp(self, text: str) -> str:
        """Wyciągnij timestamp z tekstu lub zwróć aktualny"""
        
        for pattern in self.TIMESTAMP_PATTERNS:
            match = pattern.search(text)
            if match:
                ts_str = match.group(1)
                # Parsuj różne formaty
                for fmt in [
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%d/%m/%Y %H:%M:%S',
                ]:
                    try:
                        dt = datetime.strptime(ts_str.replace('Z', ''), fmt.replace('Z', ''))
                        return dt.isoformat()
                    except:
                        continue
                # Jeśli parsowanie nie zadziałało, zwróć jak jest
                return ts_str
        
        # Brak timestamp - użyj aktualnego
        return datetime.now().isoformat()
    
    def is_important(self, log: ParsedLog) -> bool:
        """Czy log jest ważny (do filtrowania)"""
        return log.event_type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ERROR')


# Globalny parser
parser = SmartParser()


def parse_log(raw: str, source: str = "") -> ParsedLog:
    """Funkcja pomocnicza"""
    return parser.parse(raw, source)


def parse_and_filter(raw: str, source: str = "") -> Optional[ParsedLog]:
    """Parsuj i zwróć tylko jeśli ważny (SQL/ERROR)"""
    log = parser.parse(raw, source)
    return log if parser.is_important(log) else None
