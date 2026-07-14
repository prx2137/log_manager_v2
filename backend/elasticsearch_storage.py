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

            # Dla ES 8.x - wylacz weryfikacje SSL i dodaj timeout
            self.es = Elasticsearch(
                self.hosts,
                verify_certs=False,
                ssl_show_warn=False,
                request_timeout=10,
                retry_on_timeout=True,
                max_retries=3
            )

            # Test polaczenia z lepszym error handling
            try:
                info = self.es.info()
                print(f"[ES] Polaczono z Elasticsearch {info.get('version', {}).get('number', 'unknown')}")
                self.is_connected = True
                logger.info("Polaczono z Elasticsearch")
                return True
            except Exception as ping_error:
                print(f"[ES] Blad ping: {type(ping_error).__name__}: {ping_error}")

                # Sprobuj ponownie z innymi ustawieniami
                try:
                    # Moze ES wymaga basic auth?
                    health = self.es.cluster.health(request_timeout=5)
                    if health:
                        print(f"[ES] Cluster health: {health.get('status', 'unknown')}")
                        self.is_connected = True
                        return True
                except Exception as health_error:
                    print(f"[ES] Blad cluster.health: {type(health_error).__name__}: {health_error}")

                logger.warning("Elasticsearch nie odpowiada")
                return False

        except ImportError as e:
            print(f"[ES] Brak biblioteki elasticsearch: {e}")
            print("[ES] Zainstaluj: pip install elasticsearch>=8.0.0")
            logger.error(f"Brak biblioteki elasticsearch: {e}")
            return False
        except Exception as e:
            print(f"[ES] Blad polaczenia: {type(e).__name__}: {e}")
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
            must = []

            if query:
                must.append({"multi_match": {"query": query, "fields": ["message", "raw", "*"]}})

            if level:
                must.append({"term": {"severity": level}})

            if source:
                must.append({"term": {"source": source}})

            if operation:
                must.append({"term": {"operation": operation}})

            if start_time or end_time:
                time_range = {}
                if start_time:
                    time_range["gte"] = start_time.isoformat()
                if end_time:
                    time_range["lte"] = end_time.isoformat()
                must.append({"range": {"timestamp": time_range}})

            body = {
                "query": {"bool": {"must": must}} if must else {"match_all": {}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }

            # Szukaj w ostatnich 7 dniach
            indices = []
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                indices.append(self._get_index_name(date))

            index_pattern = ",".join(indices)

            try:
                result = self.es.search(index=index_pattern, body=body)
                return [hit["_source"] for hit in result["hits"]["hits"]]
            except NotFoundError:
                # Index nie istnieje - to OK
                return []

        except Exception as e:
            logger.error(f"Blad wyszukiwania w ES: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Statystyki z ES"""
        if not self.is_connected:
            return {}

        try:
            from elasticsearch import NotFoundError

            index_pattern = f"{self.index_prefix}-*"

            try:
                # Liczba dokumentow
                count = self.es.count(index=index_pattern)

                # Agregacje
                aggs_body = {
                    "size": 0,
                    "aggs": {
                        "by_severity": {"terms": {"field": "severity", "size": 10}},
                        "by_source": {"terms": {"field": "source", "size": 50}},
                        "by_source_type": {"terms": {"field": "source_type", "size": 10}},
                        "by_event_type": {"terms": {"field": "event_type", "size": 20}}
                    }
                }

                result = self.es.search(index=index_pattern, body=aggs_body)

                return {
                    "total_logs": count["count"],
                    "by_severity": {b["key"]: b["doc_count"] for b in result["aggregations"]["by_severity"]["buckets"]},
                    "by_source": {b["key"]: b["doc_count"] for b in result["aggregations"]["by_source"]["buckets"]},
                    "by_source_type": {b["key"]: b["doc_count"] for b in
                                       result["aggregations"]["by_source_type"]["buckets"]},
                    "by_event_type": {b["key"]: b["doc_count"] for b in
                                      result["aggregations"]["by_event_type"]["buckets"]}
                }
            except NotFoundError:
                return {"total_logs": 0}

        except Exception as e:
            logger.error(f"Blad statystyk ES: {e}")
            return {}

    async def delete_old_logs(self, days: int = 30) -> int:
        """Usun stare logi"""
        if not self.is_connected:
            return 0

        try:
            deleted = 0
            cutoff = datetime.now() - timedelta(days=days)

            # Usun stare indexy
            indices = self.es.indices.get(index=f"{self.index_prefix}-*")
            for index_name in indices:
                # Wyciagnij date z nazwy
                try:
                    date_str = index_name.replace(f"{self.index_prefix}-", "")
                    index_date = datetime.strptime(date_str, "%Y.%m.%d")
                    if index_date < cutoff:
                        self.es.indices.delete(index=index_name)
                        deleted += 1
                        logger.info(f"Usunieto index: {index_name}")
                except ValueError:
                    pass

            return deleted
        except Exception as e:
            logger.error(f"Blad usuwania starych logow: {e}")
            return 0

    async def clear_all(self) -> bool:
        """Wyczysc wszystkie logi"""
        if not self.is_connected:
            return False

        try:
            # Usun wszystkie indexy z prefixem
            self.es.indices.delete(index=f"{self.index_prefix}-*", ignore_unavailable=True)
            logger.info("Wyczyszczono wszystkie logi z ES")
            return True
        except Exception as e:
            logger.error(f"Blad czyszczenia ES: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Status Elasticsearch"""
        if not self.is_connected or not self.es:
            return {"connected": False}

        try:
            health = self.es.cluster.health()
            return {
                "connected": True,
                "cluster_name": health.get("cluster_name"),
                "status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes")
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
