"""
Sources - Klasy do czytania logow z roznych zrodel
"""

import os
import time
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from smart_parser import parse_log, parse_and_filter, ParsedLog


@dataclass
class SourceStatus:
    """Status zrodla"""
    name: str
    type: str
    enabled: bool
    running: bool = False
    last_check: Optional[str] = None
    logs_collected: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class BaseSource(ABC):
    """Bazowa klasa dla zrodel logow"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.running = False
        self.last_check: Optional[datetime] = None
        self.logs_collected = 0
        self.last_error: Optional[str] = None
        
        # Filtrowanie
        self.filter_important = config.get('filter_important', False)
    
    @abstractmethod
    def collect(self) -> List[ParsedLog]:
        """Zbierz nowe logi"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Testuj polaczenie"""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Typ zrodla"""
        pass
    
    def get_status(self) -> SourceStatus:
        return SourceStatus(
            name=self.name,
            type=self.source_type,
            enabled=self.enabled,
            running=self.running,
            last_check=self.last_check.isoformat() if self.last_check else None,
            logs_collected=self.logs_collected,
            last_error=self.last_error
        )
    
    def reset_tracking(self):
        """Reset tracking - pozwoli na ponowne zebranie logow"""
        pass  # Domyslnie nic - podklasy moga nadpisac
    
    def _parse_and_filter(self, raw: str, event_type: str = None) -> Optional[ParsedLog]:
        """Parsuj log i filtruj jesli wlaczone"""
        if self.filter_important:
            return parse_and_filter(raw, self.name)
        else:
            parsed = parse_log(raw, self.name)
            if parsed and event_type:
                parsed.event_type = event_type
            return parsed


class FileSource(BaseSource):
    """Zrodlo: pliki logow"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # Normalizuj sciezke - obsluga Windows
        raw_path = config.get('path', '')
        self.path = self._normalize_path(raw_path)
        self.patterns = config.get('patterns', ['*.log', '*.txt'])
        
        # Tracking - pozycja w plikach
        self._file_positions: Dict[str, int] = {}
        self._file_inodes: Dict[str, int] = {}
        
        print(f"[FileSource] Sciezka: {self.path}")
    
    def reset_tracking(self):
        """Reset tracking - ponownie czytaj pliki od poczatku"""
        self._file_positions.clear()
        self._file_inodes.clear()
        print(f"[FileSource] Reset tracking dla {self.name}")
    
    def _normalize_path(self, path: str) -> str:
        """Normalizuj sciezke - obsluga Windows i Unix"""
        if not path:
            return ''
        
        # Usun biale znaki
        path = path.strip()
        
        # Usun cudzyslowy jesli sa
        if (path.startswith('"') and path.endswith('"')) or \
           (path.startswith("'") and path.endswith("'")):
            path = path[1:-1]
        
        # Uzyj pathlib do normalizacji
        try:
            normalized = str(Path(path).resolve())
            return normalized
        except Exception:
            # Fallback - prosta normalizacja
            return path.replace('/', os.sep).replace('\\\\', '\\')
    
    @property
    def source_type(self) -> str:
        return "file"
    
    def test_connection(self) -> bool:
        """Sprawdz czy sciezka istnieje"""
        try:
            if not self.path:
                self.last_error = "Sciezka jest pusta"
                return False
            
            # Debug
            print(f"[FileSource] Test sciezki: {self.path}")
            print(f"[FileSource] os.path.exists: {os.path.exists(self.path)}")
            
            if os.path.isfile(self.path):
                if os.access(self.path, os.R_OK):
                    self.last_error = None
                    return True
                else:
                    self.last_error = f"Brak uprawnien do odczytu: {self.path}"
                    return False
            elif os.path.isdir(self.path):
                if os.access(self.path, os.R_OK):
                    self.last_error = None
                    return True
                else:
                    self.last_error = f"Brak uprawnien do odczytu katalogu: {self.path}"
                    return False
            else:
                # Sprawdz czy sciezka w ogole istnieje
                parent = os.path.dirname(self.path)
                if parent and os.path.exists(parent):
                    self.last_error = f"Plik nie istnieje: {self.path} (katalog {parent} istnieje)"
                else:
                    self.last_error = f"Sciezka nie istnieje: {self.path}"
                return False
                
        except Exception as e:
            self.last_error = f"Blad sprawdzania sciezki: {str(e)}"
            return False
    
    def collect(self) -> List[ParsedLog]:
        """Zbierz nowe logi z plikow"""
        logs = []
        self.running = True
        self.last_check = datetime.now()
        
        try:
            files = self._get_files()
            
            for filepath in files:
                try:
                    new_logs = self._read_new_lines(filepath)
                    logs.extend(new_logs)
                except Exception as e:
                    self.last_error = f"Blad czytania {filepath}: {e}"
            
            self.logs_collected += len(logs)
            if logs:
                self.last_error = None
                print(f"[File] Zebrano {len(logs)} logow z {self.path}")
                
        except Exception as e:
            self.last_error = str(e)
        
        return logs
    
    def _get_files(self) -> List[str]:
        """Pobierz liste plikow do monitorowania"""
        import glob
        
        files = []
        
        if os.path.isfile(self.path):
            files.append(self.path)
        elif os.path.isdir(self.path):
            for pattern in self.patterns:
                search_path = os.path.join(self.path, '**', pattern)
                files.extend(glob.glob(search_path, recursive=True))
        
        return files
    
    def _read_new_lines(self, filepath: str) -> List[ParsedLog]:
        """Czytaj nowe linie z pliku"""
        logs = []
        
        try:
            stat = os.stat(filepath)
            file_size = stat.st_size
            
            # Windows nie ma inode, uzyj mtime + size jako identyfikator
            try:
                current_inode = stat.st_ino
            except AttributeError:
                current_inode = hash((stat.st_mtime, stat.st_size))
            
            # Reset pozycji jesli plik zostal zrotowany
            if filepath in self._file_inodes:
                if self._file_inodes[filepath] != current_inode:
                    self._file_positions[filepath] = 0
            
            self._file_inodes[filepath] = current_inode
            
            # Pobierz poprzednia pozycje
            position = self._file_positions.get(filepath, 0)
            
            # Jesli pierwszy raz - czytaj ostatnie 50KB (lub calosc jesli mniejszy)
            if filepath not in self._file_positions:
                # Czytaj ostatnie 50KB pliku lub caly jesli mniejszy
                max_initial_read = 50 * 1024  # 50KB
                if file_size > max_initial_read:
                    position = file_size - max_initial_read
                else:
                    position = 0
                print(f"[File] Inicjalizacja {filepath} - czytam od pozycji {position} (rozmiar: {file_size})")
            
            # Jesli plik sie zmniejszyl (np. wymazany) - reset
            if position > file_size:
                position = 0
                self._file_positions[filepath] = 0
            
            # Czytaj nowe linie
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(position)
                
                for line in f:
                    line = line.strip()
                    if line:
                        parsed = self._parse_and_filter(line)
                        if parsed:
                            logs.append(parsed)
                
                self._file_positions[filepath] = f.tell()
        
        except FileNotFoundError:
            self._file_positions.pop(filepath, None)
            self._file_inodes.pop(filepath, None)
        except Exception as e:
            self.last_error = f"Blad czytania {filepath}: {e}"
        
        return logs


class MySQLSource(BaseSource):
    """Zrodlo: MySQL - monitorowanie zapytan przez general_log"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.user = config.get('user', 'root')
        self.password = config.get('password', '')
        self.database = config.get('database', '')
        
        # Opcje monitorowania
        self.monitor_table = config.get('monitor_table', '')
        self.monitor_column = config.get('monitor_column', 'id')
        self.timestamp_column = config.get('timestamp_column', 'created_at')
        
        # Tracking
        self._last_event_time = None
        self._last_id = 0
        self._connection = None
        self._initialized = False
    
    @property
    def source_type(self) -> str:
        return "mysql"
    
    def reset_tracking(self):
        """Reset tracking - ponownie zbierz logi"""
        self._last_event_time = None
        self._last_id = 0
        self._initialized = False
        print(f"[MySQL] Reset tracking dla {self.name}")
    
    def _get_connection(self):
        """Pobierz lub utworz polaczenie"""
        try:
            import mysql.connector
            
            if self._connection is None or not self._connection.is_connected():
                self._connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database if self.database else None,
                    connection_timeout=10
                )
            
            return self._connection
        except Exception as e:
            self.last_error = str(e)
            raise
    
    def test_connection(self) -> bool:
        """Testuj polaczenie z MySQL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def collect(self) -> List[ParsedLog]:
        """Zbierz logi z MySQL"""
        logs = []
        self.running = True
        self.last_check = datetime.now()
        
        try:
            # Opcja 1: Custom tabela z logami
            if self.monitor_table:
                logs = self._collect_from_table()
            # Opcja 2: general_log MySQL
            else:
                logs = self._collect_from_general_log()
            
            self.logs_collected += len(logs)
            
        except Exception as e:
            self.last_error = str(e)
            print(f"[MySQL ERROR] {e}")
        
        return logs
    
    def _collect_from_table(self) -> List[ParsedLog]:
        """Zbierz logi z custom tabeli"""
        logs = []
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT * FROM {self.monitor_table}
                WHERE {self.monitor_column} > %s
                ORDER BY {self.monitor_column} ASC
                LIMIT 1000
            """
            
            cursor.execute(query, (self._last_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                if self.monitor_column in row:
                    self._last_id = max(self._last_id, row[self.monitor_column])
                
                # Utworz log
                raw = str(row)
                timestamp = datetime.now().isoformat()
                
                if self.timestamp_column in row and row[self.timestamp_column]:
                    ts = row[self.timestamp_column]
                    if isinstance(ts, datetime):
                        timestamp = ts.isoformat()
                    else:
                        timestamp = str(ts)
                
                parsed = self._parse_and_filter(raw, 'DB_RECORD')
                if parsed:
                    parsed.timestamp = timestamp
                    logs.append(parsed)
            
            cursor.close()
            self.last_error = None
            
        except Exception as e:
            self.last_error = str(e)
        
        return logs
    
    def _collect_from_general_log(self) -> List[ParsedLog]:
        """Zbierz logi z mysql.general_log"""
        logs = []
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Sprawdz czy general_log jest wlaczony
            cursor.execute("SHOW VARIABLES LIKE 'general_log'")
            result = cursor.fetchone()
            
            if not result or result.get('Value') != 'ON':
                self.last_error = "general_log jest wylaczony. Uruchom w MySQL: SET GLOBAL general_log = 'ON'; SET GLOBAL log_output = 'TABLE';"
                cursor.close()
                return []
            
            # Sprawdz log_output
            cursor.execute("SHOW VARIABLES LIKE 'log_output'")
            result = cursor.fetchone()
            
            if not result or 'TABLE' not in result.get('Value', ''):
                self.last_error = "log_output musi byc 'TABLE'. Uruchom: SET GLOBAL log_output = 'TABLE';"
                cursor.close()
                return []
            
            # Czas startowy - przy pierwszym uruchomieniu od teraz
            if self._last_event_time is None:
                self._last_event_time = datetime.now() - timedelta(seconds=5)
                self._initialized = True
                print(f"[MySQL] Inicjalizacja - start od {self._last_event_time}")
            
            # Pobierz nowe logi - filtruj tylko wazne operacje
            query = """
                SELECT event_time, user_host, command_type, argument
                FROM mysql.general_log
                WHERE event_time > %s
                AND command_type IN ('Query', 'Execute')
                ORDER BY event_time ASC
                LIMIT 500
            """
            
            cursor.execute(query, (self._last_event_time,))
            rows = cursor.fetchall()
            
            for row in rows:
                event_time = row.get('event_time')
                if event_time and event_time > self._last_event_time:
                    self._last_event_time = event_time
                
                argument = row.get('argument', '')
                if isinstance(argument, bytes):
                    argument = argument.decode('utf-8', errors='ignore')
                
                # Filtruj - tylko INSERT, UPDATE, DELETE, SELECT
                arg_upper = argument.upper().strip()
                
                # Pomijaj wewnetrzne zapytania MySQL
                if arg_upper.startswith('SHOW ') or arg_upper.startswith('SET '):
                    continue
                if 'general_log' in argument.lower():
                    continue
                if 'information_schema' in argument.lower():
                    continue
                
                # Okresl typ operacji
                event_type = 'QUERY'
                severity = 'INFO'
                
                if arg_upper.startswith('INSERT'):
                    event_type = 'INSERT'
                    severity = 'INFO'
                elif arg_upper.startswith('UPDATE'):
                    event_type = 'UPDATE'
                    severity = 'WARN'
                elif arg_upper.startswith('DELETE'):
                    event_type = 'DELETE'
                    severity = 'WARN'
                elif arg_upper.startswith('SELECT'):
                    event_type = 'SELECT'
                    severity = 'DEBUG'
                elif arg_upper.startswith('CREATE'):
                    event_type = 'CREATE'
                    severity = 'INFO'
                elif arg_upper.startswith('DROP'):
                    event_type = 'DROP'
                    severity = 'ERROR'
                elif arg_upper.startswith('ALTER'):
                    event_type = 'ALTER'
                    severity = 'WARN'
                
                # Utworz ParsedLog
                parsed = ParsedLog(
                    timestamp=event_time.isoformat() if isinstance(event_time, datetime) else str(event_time),
                    source=self.name,
                    event_type=event_type,
                    severity=severity,
                    message=argument[:500],  # Skroc dlugie zapytania
                    raw=argument,
                    user=str(row.get('user_host', ''))
                )
                
                logs.append(parsed)
            
            cursor.close()
            
            if logs:
                self.last_error = None
                print(f"[MySQL] Zebrano {len(logs)} logow")
            
        except Exception as e:
            self.last_error = str(e)
            print(f"[MySQL ERROR] {e}")
        
        return logs


class MongoDBSource(BaseSource):
    """Zrodlo: MongoDB (w tym Atlas)"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.uri = config.get('uri', 'mongodb://localhost:27017')
        self.database = config.get('database', '')
        self.collection = config.get('collection', '')
        
        self._client = None
        self._last_id = None
        self._doc_hashes: Dict[str, str] = {}  # doc_id -> hash dla wykrywania zmian
        self._initial_load_done = False
        
        print(f"[MongoDB] URI: {self._mask_uri(self.uri)}")
    
    def _mask_uri(self, uri: str) -> str:
        """Maskuj haslo w URI do wyswietlania"""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', uri)
    
    @property
    def source_type(self) -> str:
        return "mongodb"
    
    def _get_client(self):
        """Pobierz klienta MongoDB - obsluga Atlas SRV"""
        try:
            from pymongo.mongo_client import MongoClient
            from pymongo.server_api import ServerApi
            
            if self._client is None:
                # Sprawdz czy to Atlas (mongodb+srv)
                if 'mongodb+srv' in self.uri or 'mongodb.net' in self.uri:
                    # MongoDB Atlas - uzyj ServerApi
                    print("[MongoDB] Laczenie z Atlas...")
                    self._client = MongoClient(
                        self.uri,
                        server_api=ServerApi('1'),
                        serverSelectionTimeoutMS=10000,
                        connectTimeoutMS=10000
                    )
                else:
                    # Zwykly MongoDB
                    self._client = MongoClient(
                        self.uri,
                        serverSelectionTimeoutMS=5000
                    )
            
            return self._client
        except ImportError:
            self.last_error = "Brak biblioteki pymongo. Zainstaluj: pip install 'pymongo[srv]'"
            raise
        except Exception as e:
            self.last_error = str(e)
            raise
    
    def test_connection(self) -> bool:
        """Testuj polaczenie z MongoDB"""
        try:
            client = self._get_client()
            # Ping do sprawdzenia polaczenia
            client.admin.command('ping')
            
            # Pokaz dostepne bazy i kolekcje
            try:
                dbs = client.list_database_names()
                print(f"[MongoDB] Dostepne bazy danych: {dbs}")
                
                if self.database:
                    db = client[self.database]
                    collections = db.list_collection_names()
                    print(f"[MongoDB] Kolekcje w '{self.database}': {collections}")
                    
                    if self.collection:
                        if self.collection in collections:
                            count = db[self.collection].count_documents({})
                            print(f"[MongoDB] Kolekcja '{self.collection}' zawiera {count} dokumentow")
                            if count == 0:
                                self.last_error = f"Kolekcja '{self.collection}' jest pusta - brak dokumentow do monitorowania"
                        else:
                            self.last_error = f"Kolekcja '{self.collection}' nie istnieje. Dostepne: {collections}"
                            print(f"[MongoDB WARN] {self.last_error}")
                    elif not collections:
                        self.last_error = f"Baza '{self.database}' nie ma zadnych kolekcji"
                        print(f"[MongoDB WARN] {self.last_error}")
            except Exception as list_err:
                print(f"[MongoDB] Nie mozna wylistowac baz: {list_err}")
            
            print("[MongoDB] Polaczenie OK!")
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[MongoDB ERROR] {e}")
            return False
    
    def collect(self) -> List[ParsedLog]:
        """Zbierz logi z MongoDB"""
        logs = []
        self.running = True
        self.last_check = datetime.now()
        
        try:
            if not self.database:
                self.last_error = "Nie podano nazwy bazy danych (database)"
                return []
            
            if self.collection:
                logs = self._collect_from_collection()
            else:
                # Bez kolekcji - probuj z profiler lub wyswietl blad
                self.last_error = "Podaj nazwe kolekcji (collection) do monitorowania. Bez niej mozna tylko monitorowac system.profile (wymaga db.setProfilingLevel(2))"
                logs = self._collect_from_profiler()
            
            self.logs_collected += len(logs)
            if logs:
                self.last_error = None
                print(f"[MongoDB] Zebrano {len(logs)} logow")
            
        except Exception as e:
            self.last_error = str(e)
            print(f"[MongoDB ERROR] {e}")
        
        return logs
    
    def reset_tracking(self):
        """Reset tracking - ponownie zbierz wszystkie dokumenty"""
        self._last_id = None
        self._doc_hashes.clear()
        self._initial_load_done = False
        print(f"[MongoDB] Reset tracking dla {self.name}")
    
    def _collect_from_collection(self) -> List[ParsedLog]:
        """Zbierz z kolekcji - wykrywa nowe dokumenty I zmiany w istniejacych"""
        logs = []
        
        try:
            from bson import ObjectId
            from bson.json_util import dumps as bson_dumps
            
            client = self._get_client()
            
            if not self.database:
                self.last_error = "Nie podano nazwy bazy danych"
                return []
            
            if not self.collection:
                self.last_error = "Nie podano nazwy kolekcji"
                return []
            
            db = client[self.database]
            
            # Sprawdz czy kolekcja istnieje
            if self.collection not in db.list_collection_names():
                self.last_error = f"Kolekcja '{self.collection}' nie istnieje w bazie '{self.database}'"
                return []
            
            coll = db[self.collection]
            
            # Pobierz wszystkie dokumenty (limit 1000)
            cursor = coll.find({}).limit(1000)
            
            current_docs = {}
            for doc in cursor:
                doc_id = str(doc['_id'])
                # Utworz hash dokumentu (bez _id)
                doc_copy = dict(doc)
                del doc_copy['_id']
                doc_hash = hashlib.md5(bson_dumps(doc_copy).encode()).hexdigest()
                current_docs[doc_id] = (doc, doc_hash)
            
            # Pierwsze uruchomienie - zaloguj wszystkie dokumenty
            if not self._initial_load_done:
                print(f"[MongoDB] Pierwsze uruchomienie - pobieram {len(current_docs)} dokumentow")
                for doc_id, (doc, doc_hash) in current_docs.items():
                    self._doc_hashes[doc_id] = doc_hash
                    logs.append(self._doc_to_log(doc, 'INITIAL_LOAD'))
                self._initial_load_done = True
                return logs
            
            # Sprawdz nowe i zmienione dokumenty
            for doc_id, (doc, doc_hash) in current_docs.items():
                if doc_id not in self._doc_hashes:
                    # Nowy dokument
                    print(f"[MongoDB] Nowy dokument: {doc_id}")
                    logs.append(self._doc_to_log(doc, 'INSERT'))
                    self._doc_hashes[doc_id] = doc_hash
                elif self._doc_hashes[doc_id] != doc_hash:
                    # Zmieniony dokument
                    print(f"[MongoDB] Zmieniony dokument: {doc_id}")
                    logs.append(self._doc_to_log(doc, 'UPDATE'))
                    self._doc_hashes[doc_id] = doc_hash
            
            # Sprawdz usuniete dokumenty
            deleted_ids = set(self._doc_hashes.keys()) - set(current_docs.keys())
            for doc_id in deleted_ids:
                print(f"[MongoDB] Usuniety dokument: {doc_id}")
                logs.append(ParsedLog(
                    timestamp=datetime.now().isoformat(),
                    source=self.name,
                    event_type='DELETE',
                    severity='WARN',
                    message=f'Usuniety dokument: {doc_id}',
                    raw=f'{{"_id": "{doc_id}", "action": "deleted"}}'
                ))
                del self._doc_hashes[doc_id]
            
        except Exception as e:
            self.last_error = str(e)
            print(f"[MongoDB ERROR] {e}")
        
        return logs
    
    def _doc_to_log(self, doc: dict, event_type: str) -> ParsedLog:
        """Konwertuj dokument MongoDB na ParsedLog"""
        raw = str(doc)
        
        # Dla INSERT/UPDATE/DELETE - uzyj aktualnego czasu (kiedy wykryto zmiane)
        # Dla INITIAL_LOAD - uzyj timestamp z dokumentu lub aktualny czas
        if event_type in ['INSERT', 'UPDATE', 'DELETE']:
            timestamp = datetime.now().isoformat()
        else:
            # INITIAL_LOAD - szukaj timestamp w dokumencie
            timestamp = datetime.now().isoformat()
            for ts_field in ['timestamp', 'created_at', 'createdAt', 'date', 'time', 'updatedAt', 'updated_at']:
                if ts_field in doc and doc[ts_field]:
                    ts = doc[ts_field]
                    if isinstance(ts, datetime):
                        timestamp = ts.isoformat()
                    elif isinstance(ts, str):
                        # Waliduj format daty
                        try:
                            datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            timestamp = ts
                        except ValueError:
                            pass  # Niepoprawny format - zostaw domyslny
                    break
        
        # Szukaj message/level w dokumencie
        message = doc.get('message', doc.get('msg', doc.get('name', doc.get('title', str(doc)))))
        level = doc.get('level', doc.get('severity', 'INFO'))
        
        return ParsedLog(
            timestamp=timestamp,
            source=self.name,
            event_type=event_type,
            severity=str(level).upper(),
            message=str(message)[:500],
            raw=raw
        )
    
    def _collect_from_profiler(self) -> List[ParsedLog]:
        """Zbierz z system.profile"""
        logs = []
        
        try:
            client = self._get_client()
            
            if not self.database:
                self.last_error = "Nie podano nazwy bazy danych"
                return []
            
            db = client[self.database]
            
            # Sprawdz czy profiling jest wlaczony
            try:
                profile = db.command('profile', -1)
                if profile.get('was', 0) == 0:
                    self.last_error = "Profiling jest wylaczony. Uruchom w MongoDB: db.setProfilingLevel(2)"
                    return []
            except Exception:
                self.last_error = "Nie mozna sprawdzic profiling level"
                return []
            
            coll = db['system.profile']
            
            query = {}
            if self._last_id:
                from bson import ObjectId
                try:
                    query['_id'] = {'$gt': ObjectId(self._last_id)}
                except Exception:
                    pass
            
            cursor = coll.find(query).sort('ts', 1).limit(1000)
            
            for doc in cursor:
                if '_id' in doc:
                    self._last_id = str(doc['_id'])
                
                op = doc.get('op', 'unknown')
                ns = doc.get('ns', '')
                
                event_type = op.upper()
                if op == 'query':
                    event_type = 'SELECT'
                elif op == 'insert':
                    event_type = 'INSERT'
                elif op == 'update':
                    event_type = 'UPDATE'
                elif op == 'remove':
                    event_type = 'DELETE'
                
                ts = doc.get('ts', datetime.now())
                timestamp = ts.isoformat() if isinstance(ts, datetime) else str(ts)
                
                parsed = ParsedLog(
                    timestamp=timestamp,
                    source=self.name,
                    event_type=event_type,
                    severity='INFO',
                    message=f"{op} on {ns}",
                    raw=str(doc)
                )
                logs.append(parsed)
            
        except Exception as e:
            self.last_error = str(e)
        
        return logs
