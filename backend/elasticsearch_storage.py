"""
Elasticsearch Storage - Zapis i odczyt logow
Kompatybilny z ES 7.x i 8.x
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ElasticsearchStorage:
    """Klasa do obslugi Elasticsearch"""
    
    def __init__(self, hosts: List[str], index_prefix: str = "logs"):
        self.hosts = hosts
        self.index_prefix = index_prefix
        self.es = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Polacz z Elasticsearch"""
        try:
            from elasticsearch import Elasticsearch
            
            self.es = Elasticsearch(
                self.hosts,
                verify_certs=False,
                request_timeout=30
            )
            
            # Test polaczenia
            if self.es.ping():
                self.is_connected = True
                logger.info("Polaczono z Elasticsearch")
                return True
            else:
                logger.warning("Elasticsearch nie odpowiada")
                return False
        except Exception as e:
            logger.error(f"Blad polaczenia z ES: {e}")
            return False
    
    async def disconnect(self):
        """Rozlacz"""
        if self.es:
            self.es.close()
            self.is_connected = False
    
    def _get_index_name(self, date: Optional[datetime] = None) -> str:
        """Nazwa indexu dla daty"""
        if date is None:
            date = datetime.now()
        return f"{self.index_prefix}-{date.strftime('%Y.%m.%d')}"
    
    async def _ensure_index(self):
        """Upewnij sie ze index istnieje"""
        index_name = self._get_index_name()
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(
                index=index_name,
                body={
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "severity": {"type": "keyword"},
                            "level": {"type": "keyword"},
                            "source": {"type": "keyword"},
                            "source_type": {"type": "keyword"},
                            "event_type": {"type": "keyword"},
                            "operation": {"type": "keyword"},
                            "message": {"type": "text"},
                            "raw": {"type": "text"},
                            "database": {"type": "keyword"},
                            "table_name": {"type": "keyword"},
                            "user": {"type": "keyword"},
                            "collected_at": {"type": "date"}
                        }
                    }
                }
            )
            logger.info(f"Utworzono index: {index_name}")
    
    async def save_log(self, log_entry: Dict[str, Any]) -> bool:
        """Zapisz pojedynczy log"""
        if not self.is_connected:
            return False
        
        try:
            if "timestamp" in log_entry:
                if isinstance(log_entry["timestamp"], datetime):
                    log_entry["timestamp"] = log_entry["timestamp"].isoformat()
            else:
                log_entry["timestamp"] = datetime.now().isoformat()
            
            await self._ensure_index()
            self.es.index(index=self._get_index_name(), document=log_entry)
            return True
        except Exception as e:
            logger.error(f"Blad zapisu do ES: {e}")
            return False
    
    async def save_logs_bulk(self, logs: List[Dict[str, Any]]) -> int:
        """Zapisz wiele logow na raz"""
        if not self.is_connected or not logs:
            return 0
        
        try:
            await self._ensure_index()
            index_name = self._get_index_name()
            
            operations = []
            for log in logs:
                if "timestamp" in log and isinstance(log["timestamp"], datetime):
                    log["timestamp"] = log["timestamp"].isoformat()
                elif "timestamp" not in log:
                    log["timestamp"] = datetime.now().isoformat()
                
                operations.append({"index": {"_index": index_name}})
                operations.append(log)
            
            if operations:
                result = self.es.bulk(operations=operations)
                saved = sum(1 for item in result["items"] if item["index"]["status"] in [200, 201])
                logger.info(f"Zapisano {saved}/{len(logs)} logow do ES")
                return saved
            return 0
        except Exception as e:
            logger.error(f"Blad bulk zapisu do ES: {e}")
            return 0
    
    async def search_logs(
        self,
        query: Optional[str] = None,
        level: Optional[str] = None,
        source: Optional[str] = None,
        operation: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Szukaj logow"""
        if not self.is_connected:
            return []
        
        try:
            from elasticsearch import NotFoundError
            
            # Buduj query
            must_conditions = []
            
            if query:
                must_conditions.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["message", "raw", "source"]
                    }
                })
            
            if level:
                # Szukaj w 'severity' (ParsedLog) lub 'level'
                must_conditions.append({
                    "bool": {
                        "should": [
                            {"term": {"severity": level.upper()}},
                            {"term": {"level": level.upper()}}
                        ],
                        "minimum_should_match": 1
                    }
                })
            
            if source:
                must_conditions.append({"term": {"source": source}})
            
            if operation:
                # Szukaj w 'event_type' (ParsedLog) lub 'operation'
                must_conditions.append({
                    "bool": {
                        "should": [
                            {"term": {"event_type": operation.upper()}},
                            {"term": {"operation": operation.upper()}}
                        ],
                        "minimum_should_match": 1
                    }
                })
            
            # Filtr czasowy
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["gte"] = start_time.isoformat()
                if end_time:
                    time_filter["lte"] = end_time.isoformat()
                must_conditions.append({"range": {"timestamp": time_filter}})
            
            # Zbuduj finalne query - ES 8.x kompatybilne
            index_pattern = f"{self.index_prefix}-*"
            
            if must_conditions:
                # Z warunkami - uzyj bool query
                result = self.es.search(
                    index=index_pattern,
                    query={"bool": {"must": must_conditions}},
                    sort=[{"timestamp": {"order": "desc"}}],
                    size=limit
                )
            else:
                # Bez warunkow - pobierz wszystko
                result = self.es.search(
                    index=index_pattern,
                    query={"match_all": {}},
                    sort=[{"timestamp": {"order": "desc"}}],
                    size=limit
                )
            
            logs = []
            for hit in result["hits"]["hits"]:
                log = hit["_source"]
                log["_id"] = hit["_id"]
                logs.append(log)
            
            return logs
        except NotFoundError:
            logger.warning("Index nie istnieje - brak logow")
            return []
        except Exception as e:
            logger.error(f"Blad szukania w ES: {e}")
            return []
    
    async def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """Pobierz pojedynczy log po ID"""
        if not self.is_connected:
            return None
        
        try:
            index_pattern = f"{self.index_prefix}-*"
            result = self.es.search(
                index=index_pattern,
                query={"ids": {"values": [log_id]}},
                size=1
            )
            
            if result["hits"]["hits"]:
                log = result["hits"]["hits"][0]["_source"]
                log["_id"] = result["hits"]["hits"][0]["_id"]
                return log
            return None
        except Exception as e:
            logger.error(f"Blad pobierania loga: {e}")
            return None
    
    async def delete_all_logs(self) -> int:
        """Usun wszystkie logi"""
        if not self.is_connected:
            return 0
        
        try:
            index_pattern = f"{self.index_prefix}-*"
            result = self.es.delete_by_query(
                index=index_pattern,
                query={"match_all": {}},
                conflicts="proceed"
            )
            deleted = result.get("deleted", 0)
            logger.info(f"Usunieto {deleted} logow z ES")
            return deleted
        except Exception as e:
            logger.error(f"Blad usuwania logow: {e}")
            return 0
    
    async def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Pobierz statystyki"""
        if not self.is_connected:
            return {}
        
        try:
            from_time = datetime.now() - timedelta(hours=hours)
            index_pattern = f"{self.index_prefix}-*"
            
            # Agregacje - uzywamy severity i event_type (struktura ParsedLog)
            result = self.es.search(
                index=index_pattern,
                query={
                    "range": {
                        "timestamp": {"gte": from_time.isoformat()}
                    }
                },
                aggs={
                    "by_level": {
                        "terms": {"field": "severity", "size": 10}
                    },
                    "by_operation": {
                        "terms": {"field": "event_type", "size": 10}
                    },
                    "by_source": {
                        "terms": {"field": "source", "size": 20}
                    },
                    "timeline": {
                        "date_histogram": {
                            "field": "timestamp",
                            "fixed_interval": "1h"
                        }
                    }
                },
                size=0
            )
            
            # Parsuj wyniki
            aggs = result.get("aggregations", {})
            
            by_level = {}
            for bucket in aggs.get("by_level", {}).get("buckets", []):
                by_level[bucket["key"]] = bucket["doc_count"]
            
            by_operation = {}
            for bucket in aggs.get("by_operation", {}).get("buckets", []):
                by_operation[bucket["key"]] = bucket["doc_count"]
            
            by_source = {}
            for bucket in aggs.get("by_source", {}).get("buckets", []):
                by_source[bucket["key"]] = bucket["doc_count"]
            
            timeline = []
            for bucket in aggs.get("timeline", {}).get("buckets", []):
                timeline.append({
                    "time": bucket["key_as_string"],
                    "count": bucket["doc_count"]
                })
            
            return {
                "total": result["hits"]["total"]["value"],
                "by_level": by_level,
                "by_operation": by_operation,
                "by_source": by_source,
                "timeline": timeline
            }
        except Exception as e:
            logger.error(f"Blad statystyk ES: {e}")
            return {}
    
    async def get_es_status(self) -> Dict[str, Any]:
        """Status Elasticsearch"""
        if not self.is_connected or not self.es:
            return {"connected": False}
        
        try:
            info = self.es.info()
            return {
                "connected": True,
                "version": info["version"]["number"],
                "cluster_name": info["cluster_name"]
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
