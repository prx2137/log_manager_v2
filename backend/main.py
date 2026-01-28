"""
Log Manager - Backend API z Elasticsearch
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import asyncio
import time
import os

from config import Config
from sources import FileSource, MySQLSource, MongoDBSource
from smart_parser import ParsedLog
from elasticsearch_storage import ElasticsearchStorage

# ============================================
# GLOBALNE DANE
# ============================================

config = Config()
sources: Dict[str, Any] = {}
all_logs: List[Dict] = []
MAX_LOGS = 10000

# Elasticsearch
es_storage: Optional[ElasticsearchStorage] = None
ES_ENABLED = True

# ============================================
# LIFESPAN (startup/shutdown)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("\n" + "="*50)
    print("  LOG MANAGER - START")
    print("="*50 + "\n")
    
    # Elasticsearch
    await init_elasticsearch()
    
    # Sources
    init_sources()
    
    # Collector
    start_collector()
    
    print(f"\n[OK] Zaladowano {len(sources)} zrodel")
    print("[OK] Collector uruchomiony")
    if es_storage and es_storage.is_connected:
        print("[OK] Elasticsearch polaczony")
    else:
        print("[WARN] Elasticsearch niedostepny - logi tylko w pamieci")
    print("\n" + "="*50 + "\n")
    
    yield
    
    # SHUTDOWN
    stop_collector()
    if es_storage:
        await es_storage.disconnect()
    print("Log Manager zatrzymany")

app = FastAPI(title="Log Manager API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ELASTICSEARCH
# ============================================

async def init_elasticsearch():
    """Inicjalizuj polaczenie z Elasticsearch"""
    global es_storage, ES_ENABLED
    
    if not ES_ENABLED:
        print("[INFO] Elasticsearch wylaczony")
        return
    
    # Pobierz host z env lub domyslnie localhost
    es_host = os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200')
    
    print(f"[INFO] Laczenie z Elasticsearch: {es_host}")
    
    es_storage = ElasticsearchStorage(
        hosts=[es_host],
        index_prefix="log-manager"
    )
    
    connected = await es_storage.connect()
    if connected:
        print("[OK] Elasticsearch polaczony")
    else:
        print("[WARN] Nie mozna polaczyc z Elasticsearch")

# ============================================
# SOURCES
# ============================================

def create_source(name: str, cfg: Dict) -> Any:
    """Utworz zrodlo na podstawie konfiguracji"""
    source_type = cfg.get('type', 'file')
    
    if source_type == 'file':
        return FileSource(name, cfg)
    elif source_type == 'mysql':
        return MySQLSource(name, cfg)
    elif source_type == 'mongodb':
        return MongoDBSource(name, cfg)
    else:
        print(f"[WARN] Nieznany typ zrodla: {source_type}")
        return None

def init_sources():
    """Inicjalizuj zrodla z konfiguracji"""
    global sources
    
    sources_list = config.sources or []
    for src_cfg in sources_list:
        name = src_cfg.get('name', 'unnamed')
        if src_cfg.get('enabled', True):
            source = create_source(name, src_cfg)
            if source:
                sources[name] = source
                print(f"[OK] Zrodlo: {name} ({src_cfg.get('type', 'file')})")

# ============================================
# COLLECTOR
# ============================================

collector_running = False
collector_thread = None

def collector_loop():
    """Glowna petla zbierajaca logi"""
    global all_logs
    
    print("[COLLECTOR] Start")
    
    while collector_running:
        for name, source in list(sources.items()):
            if not source.enabled or not source.running:
                continue
            
            try:
                new_logs = source.collect()
                
                if new_logs:
                    # Konwertuj ParsedLog na slowniki i dodaj metadane
                    processed_logs = []
                    for log in new_logs:
                        # Konwertuj ParsedLog na dict
                        if hasattr(log, 'to_dict'):
                            log_dict = log.to_dict()
                        elif hasattr(log, '__dict__'):
                            log_dict = dict(log.__dict__)
                        else:
                            log_dict = dict(log) if isinstance(log, dict) else {'raw': str(log)}
                        
                        # Dodaj metadane
                        log_dict['source'] = name
                        log_dict['source_type'] = source.config.get('type', 'unknown')
                        log_dict['collected_at'] = datetime.now().isoformat()
                        
                        # Upewnij sie ze timestamp istnieje
                        if 'timestamp' not in log_dict or not log_dict['timestamp']:
                            log_dict['timestamp'] = log_dict['collected_at']
                        
                        processed_logs.append(log_dict)
                    
                    # Zapisz do pamieci
                    all_logs.extend(processed_logs)
                    # Uzyj slice assignment zamiast = zeby nie tworzyc nowej zmiennej!
                    if len(all_logs) > MAX_LOGS:
                        del all_logs[:-MAX_LOGS]
                    
                    # Zapisz do Elasticsearch (async w osobnym watku)
                    if es_storage and es_storage.is_connected:
                        try:
                            # Uruchom async w nowym event loop
                            loop = asyncio.new_event_loop()
                            saved_count = loop.run_until_complete(es_storage.save_logs_bulk(processed_logs))
                            loop.close()
                            print(f"[ES] Zapisano {saved_count}/{len(processed_logs)} logow (source_type: {processed_logs[0].get('source_type', 'unknown')})")
                        except Exception as e:
                            print(f"[ES] Blad zapisu: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"[ES] Pominięto zapis - ES nie polaczony (is_connected={es_storage.is_connected if es_storage else 'None'})")
                    
                    print(f"[{name}] Zebrano {len(processed_logs)} logow")
                
                source.last_check = datetime.now()
                source.last_error = None
                
            except Exception as e:
                source.last_error = str(e)
                print(f"[ERROR] {name}: {e}")
        
        time.sleep(2)
    
    print("[COLLECTOR] Stop")

def start_collector():
    """Uruchom collector w tle"""
    global collector_running, collector_thread
    
    if collector_running:
        return
    
    collector_running = True
    collector_thread = threading.Thread(target=collector_loop, daemon=True)
    collector_thread.start()

def stop_collector():
    global collector_running
    collector_running = False

# ============================================
# MODELE API
# ============================================

class SourceConfig(BaseModel):
    name: str
    type: str = 'file'
    enabled: bool = True
    path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    uri: Optional[str] = None
    collection: Optional[str] = None
    # MySQL specific
    monitor_table: Optional[str] = None
    monitor_column: Optional[str] = None
    timestamp_column: Optional[str] = None

# ============================================
# ENDPOINTY API
# ============================================

@app.get("/api")
def root():
    return {"status": "ok", "message": "Log Manager API"}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "sources_count": len(sources),
        "logs_count": len(all_logs),
        "collector_running": collector_running,
        "elasticsearch": {
            "connected": es_storage.is_connected if es_storage else False
        }
    }

@app.get("/api/agent/status")
def agent_status():
    """Status agenta zbierajacego logi"""
    active = sum(1 for s in sources.values() if s.enabled and s.running)
    return {
        "running": collector_running,
        "sources_count": len(sources),
        "active_sources": active,
        "logs_in_cache": len(all_logs),
        "elasticsearch": {
            "enabled": ES_ENABLED,
            "connected": es_storage.is_connected if es_storage else False
        }
    }

# --- ZRODLA ---

@app.get("/api/sources")
def get_sources() -> List[Dict]:
    """Lista wszystkich zrodel"""
    result = []
    for name, source in sources.items():
        result.append({
            "name": name,
            "type": source.config.get('type', 'unknown'),
            "enabled": source.enabled,
            "running": source.running,
            "last_check": source.last_check.isoformat() if source.last_check else None,
            "logs_collected": source.logs_collected,
            "last_error": source.last_error
        })
    return result

@app.post("/api/sources")
def add_source(cfg: SourceConfig) -> Dict:
    """Dodaj nowe zrodlo"""
    if cfg.name in sources:
        raise HTTPException(400, "Zrodlo o tej nazwie juz istnieje")
    
    source_config = cfg.model_dump(exclude_none=True)
    source = create_source(cfg.name, source_config)
    
    if not source:
        raise HTTPException(400, "Nie udalo sie utworzyc zrodla")
    
    # Automatycznie uruchom zrodlo
    source.enabled = True
    source.running = True
    
    sources[cfg.name] = source
    
    # Upewnij sie, ze collector dziala
    start_collector()
    
    return {
        "name": cfg.name,
        "type": source.config.get('type', 'unknown'),
        "enabled": source.enabled,
        "running": source.running,
        "last_check": None,
        "logs_collected": 0,
        "last_error": None
    }

@app.delete("/api/sources/{name}")
def delete_source(name: str) -> Dict:
    """Usun zrodlo"""
    if name not in sources:
        raise HTTPException(404, "Zrodlo nie istnieje")
    
    del sources[name]
    return {"status": "ok"}

@app.post("/api/sources/{name}/toggle")
def toggle_source(name: str) -> Dict:
    """Przelacz stan zrodla"""
    if name not in sources:
        raise HTTPException(404, "Zrodlo nie istnieje")
    
    source = sources[name]
    
    if source.enabled and source.running:
        source.enabled = False
        source.running = False
    else:
        source.enabled = True
        source.running = True
        start_collector()
    
    return {
        "name": name,
        "type": source.config.get('type', 'unknown'),
        "enabled": source.enabled,
        "running": source.running,
        "last_check": source.last_check.isoformat() if source.last_check else None,
        "logs_collected": source.logs_collected,
        "last_error": source.last_error
    }

@app.post("/api/sources/{name}/start")
def start_source(name: str) -> Dict:
    """Uruchom zbieranie z zrodla"""
    if name not in sources:
        raise HTTPException(404, "Zrodlo nie istnieje")
    
    sources[name].running = True
    sources[name].enabled = True
    start_collector()
    return {"status": "ok", "running": True}

@app.post("/api/sources/{name}/stop")
def stop_source(name: str) -> Dict:
    """Zatrzymaj zbieranie z zrodla"""
    if name not in sources:
        raise HTTPException(404, "Zrodlo nie istnieje")
    
    sources[name].running = False
    return {"status": "ok", "running": False}

@app.post("/api/sources/{name}/test")
def test_source(name: str) -> Dict:
    """Testuj polaczenie ze zrodlem"""
    if name not in sources:
        raise HTTPException(404, "Zrodlo nie istnieje")
    
    source = sources[name]
    try:
        success = source.test_connection()
        if success:
            return {
                "success": True,
                "message": "Polaczenie OK"
            }
        else:
            return {
                "success": False,
                "error": source.last_error or "Nieznany blad"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# --- LOGI ---

@app.get("/api/logs")
async def get_logs(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    # Legacy params for backward compatibility
    level: Optional[str] = None,
    operation: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict:
    """
    Pobierz logi z filtrami i paginacja
    
    Params:
        source: Filtruj po zrodle
        severity: Filtruj po poziomie (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        event_type: Filtruj po typie zdarzenia
        query: Wyszukaj w tresci
        page: Numer strony (1-indexed)
        page_size: Ilosc logow na strone (default: 50, max: 500)
    
    Returns:
        logs: Lista logow dla danej strony
        total: Calkowita ilosc logow (po filtrowaniu)
        page: Aktualna strona
        page_size: Rozmiar strony
        total_pages: Calkowita ilosc stron
    """
    
    # Backward compatibility - use severity/event_type if level/operation provided
    if level and not severity:
        severity = level
    if operation and not event_type:
        event_type = operation
    
    # Validate pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 500)  # Max 500 per page
    
    # If legacy limit is used, convert to page_size
    if limit and not page_size:
        page_size = min(limit, 500)
    
    print(f"[API /logs] Logi w pamieci: {len(all_logs)}, page={page}, page_size={page_size}")
    
    # Start with all logs
    result = list(all_logs)
    
    # Apply filters
    if source:
        result = [l for l in result if l.get('source') == source or l.get('source_type') == source]
    
    if severity:
        severity_upper = severity.upper()
        result = [l for l in result if 
                  l.get('severity', '').upper() == severity_upper or 
                  l.get('level', '').upper() == severity_upper]
    
    if event_type:
        et_upper = event_type.upper()
        result = [l for l in result if 
                  l.get('event_type', '').upper() == et_upper or 
                  l.get('operation', '').upper() == et_upper]
    
    if query:
        query_lower = query.lower()
        result = [l for l in result if 
                  query_lower in str(l.get('message', '')).lower() or
                  query_lower in str(l.get('raw', '')).lower() or
                  query_lower in str(l.get('source', '')).lower()]
    
    # Sort by timestamp (newest first)
    result = sorted(result, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Calculate pagination
    total_filtered = len(result)
    total_pages = max(1, (total_filtered + page_size - 1) // page_size)
    
    # Ensure page is within bounds
    page = min(page, total_pages)
    
    # Calculate offset and slice
    offset = (page - 1) * page_size
    paginated = result[offset:offset + page_size]
    
    print(f"[API /logs] Filtered: {total_filtered}, returning: {len(paginated)}")
    
    return {
        "logs": paginated,
        "total": total_filtered,
        "total_all": len(all_logs),
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@app.get("/api/debug/logs")
def debug_logs() -> Dict:
    """Debug - pokaz stan logow"""
    return {
        "logs_count": len(all_logs),
        "sources_count": len(sources),
        "collector_running": collector_running,
        "es_connected": es_storage.is_connected if es_storage else False,
        "last_10_logs": all_logs[-10:] if all_logs else [],
        "sources_status": {
            name: {
                "enabled": s.enabled,
                "running": s.running,
                "logs_collected": s.logs_collected,
                "last_error": s.last_error
            }
            for name, s in sources.items()
        }
    }

@app.get("/api/debug/elasticsearch")
async def debug_elasticsearch() -> Dict:
    """Debug - szczegolowy stan Elasticsearch"""
    if not es_storage:
        return {"status": "disabled", "message": "ES storage nie zainicjalizowany"}
    
    if not es_storage.is_connected:
        return {"status": "disconnected", "message": "ES nie polaczony"}
    
    try:
        # Sprawdz ile dokumentow jest w ES
        index_pattern = "log-manager-*"
        
        # Count all documents
        count_result = es_storage.es.count(index=index_pattern)
        total_docs = count_result.get("count", 0)
        
        # Get breakdown by source_type
        agg_result = es_storage.es.search(
            index=index_pattern,
            size=0,
            aggs={
                "by_source_type": {
                    "terms": {"field": "source_type.keyword", "size": 100}
                },
                "by_source": {
                    "terms": {"field": "source.keyword", "size": 100}
                }
            }
        )
        
        source_types = {
            b["key"]: b["doc_count"] 
            for b in agg_result.get("aggregations", {}).get("by_source_type", {}).get("buckets", [])
        }
        sources_breakdown = {
            b["key"]: b["doc_count"] 
            for b in agg_result.get("aggregations", {}).get("by_source", {}).get("buckets", [])
        }
        
        # Get last 5 docs
        last_docs = es_storage.es.search(
            index=index_pattern,
            size=5,
            sort=[{"timestamp": {"order": "desc"}}]
        )
        recent = [hit["_source"] for hit in last_docs.get("hits", {}).get("hits", [])]
        
        return {
            "status": "connected",
            "total_documents": total_docs,
            "by_source_type": source_types,
            "by_source": sources_breakdown,
            "recent_logs": recent,
            "index_pattern": index_pattern
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/debug/sync-to-es")
async def sync_to_elasticsearch() -> Dict:
    """Reczne przeslanie wszystkich logow z pamieci do ES"""
    if not es_storage or not es_storage.is_connected:
        return {"status": "error", "message": "ES nie polaczony"}
    
    try:
        saved = await es_storage.save_logs_bulk(list(all_logs))
        return {
            "status": "ok",
            "synced": saved,
            "total_in_memory": len(all_logs)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/logs/{log_id}")
async def get_log_details(log_id: str) -> Dict:
    """Pobierz szczegoly pojedynczego loga"""
    
    # Probuj z Elasticsearch
    if es_storage and es_storage.is_connected:
        try:
            log = await es_storage.get_log_by_id(log_id)
            if log:
                return log
        except Exception as e:
            print(f"[ES] Blad pobierania loga: {e}")
    
    # Fallback - szukaj w pamieci po id
    for log in all_logs:
        if log.get('_id') == log_id:
            return log
    
    raise HTTPException(404, "Log nie znaleziony")

# --- FRONTEND LOGS ---

class FrontendLogEntry(BaseModel):
    level: str  # debug, info, warn, error
    message: str
    context: Optional[Dict[str, Any]] = None
    component: Optional[str] = None
    stack: Optional[str] = None

class FrontendLogsRequest(BaseModel):
    logs: List[FrontendLogEntry]

@app.post("/api/logs/frontend")
async def receive_frontend_logs(request: FrontendLogsRequest) -> Dict:
    """Odbiera logi z frontendu Vue"""
    global all_logs
    
    received = 0
    
    for log_entry in request.logs:
        # Mapuj level frontendu na severity
        severity_map = {
            'debug': 'DEBUG',
            'info': 'INFO',
            'warn': 'WARNING',
            'error': 'ERROR'
        }
        
        log_dict = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'frontend',
            'source_type': 'frontend',
            'severity': severity_map.get(log_entry.level.lower(), 'INFO'),
            'event_type': 'LOG',
            'message': log_entry.message,
            'component': log_entry.component or 'Unknown',
            'context': log_entry.context or {},
            'stack_trace': log_entry.stack,
            'raw': f"[{log_entry.level.upper()}] {log_entry.message}"
        }
        
        all_logs.append(log_dict)
        received += 1
        
        # Zapisz do ES
        if es_storage and es_storage.is_connected:
            try:
                await es_storage.save_log(log_dict)
            except Exception as e:
                print(f"[ES] Blad zapisu frontend log: {e}")
    
    # Ogranicz rozmiar listy
    if len(all_logs) > MAX_LOGS:
        del all_logs[:-MAX_LOGS]
    
    print(f"[FRONTEND] Otrzymano {received} logow z frontendu")
    
    return {"status": "ok", "received": received}

@app.delete("/api/logs")
async def clear_logs() -> Dict:
    """Wyczysc wszystkie logi (pamiec + Elasticsearch)"""
    global all_logs
    
    memory_count = len(all_logs)
    all_logs = []
    
    # Reset tylko licznikow, NIE trackingu - stare logi nie beda ponownie zbierane
    for source in sources.values():
        source.logs_collected = 0
        # NIE resetujemy trackingu - dzieki temu po resecie zbierane beda tylko NOWE logi
    
    # Wyczysc tez Elasticsearch
    es_count = 0
    if es_storage and es_storage.is_connected:
        try:
            es_count = await es_storage.delete_all_logs()
        except Exception as e:
            print(f"[ES] Blad czyszczenia: {e}")
    
    print(f"[RESET] Wyczyszczono {memory_count} logow z pamieci, {es_count} z ES. Tracking zachowany.")
    
    return {
        "status": "ok", 
        "cleared_memory": memory_count,
        "cleared_es": es_count
    }

# --- STATYSTYKI ---

@app.get("/api/stats")
async def get_stats(hours: int = 24) -> Dict:
    """Statystyki logow"""
    
    # Probuj z ES
    if es_storage and es_storage.is_connected:
        try:
            stats = await es_storage.get_stats(hours=hours)
            if stats:
                return stats
        except Exception as e:
            print(f"[ES] Blad statystyk: {e}")
    
    # Fallback do pamieci
    logs = all_logs
    
    by_level = {}
    by_operation = {}
    by_source = {}
    
    for log in logs:
        # Uzywamy severity (z ParsedLog) z fallback do level
        level = log.get('severity', log.get('level', 'INFO'))
        by_level[level] = by_level.get(level, 0) + 1
        
        # Uzywamy event_type (z ParsedLog) z fallback do operation
        operation = log.get('event_type', log.get('operation', 'OTHER'))
        by_operation[operation] = by_operation.get(operation, 0) + 1
        
        src = log.get('source', 'unknown')
        by_source[src] = by_source.get(src, 0) + 1
    
    return {
        "total": len(logs),
        "by_level": by_level,
        "by_operation": by_operation,
        "by_source": by_source,
        "timeline": [],
        "level_timeline": [],
        "operation_timeline": []
    }

# --- ELASTICSEARCH STATUS ---

@app.get("/api/elasticsearch/status")
def elasticsearch_status() -> Dict:
    """Status Elasticsearch"""
    if not es_storage:
        return {
            "enabled": False,
            "connected": False,
            "message": "Elasticsearch nie jest skonfigurowany"
        }
    
    return {
        "enabled": ES_ENABLED,
        "connected": es_storage.is_connected,
        "hosts": es_storage.hosts,
        "index_prefix": es_storage.index_prefix
    }
