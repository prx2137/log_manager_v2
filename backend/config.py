"""
Config - Ładowanie konfiguracji z YAML
Prosty i działający.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Config:
    """Zarządzanie konfiguracją aplikacji."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Ładuje konfigurację z pliku YAML."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Załadowano konfigurację z {self.config_path}")
            else:
                logger.warning(f"Plik konfiguracji nie istnieje: {self.config_path}")
                self._config = {}
        except Exception as e:
            logger.error(f"Błąd ładowania konfiguracji: {e}")
            self._config = {}
    
    def save(self) -> bool:
        """Zapisuje konfigurację do pliku YAML."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Zapisano konfigurację do {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd zapisywania konfiguracji: {e}")
            return False
    
    @property
    def sources(self) -> List[Dict[str, Any]]:
        """Zwraca listę źródeł."""
        return self._config.get('sources', [])
    
    @sources.setter
    def sources(self, value: List[Dict[str, Any]]) -> None:
        """Ustawia listę źródeł."""
        self._config['sources'] = value
    
    @property
    def agent(self) -> Dict[str, Any]:
        """Zwraca konfigurację agenta."""
        return self._config.get('agent', {})
    
    @property
    def storage(self) -> Dict[str, Any]:
        """Zwraca konfigurację storage."""
        return self._config.get('storage', {})
    
    @property
    def elasticsearch(self) -> Dict[str, Any]:
        """Zwraca konfigurację Elasticsearch."""
        return self.storage.get('elasticsearch', {})
    
    def get_source(self, name: str) -> Optional[Dict[str, Any]]:
        """Zwraca konfigurację źródła po nazwie."""
        for source in self.sources:
            if source.get('name') == name:
                return source
        return None
    
    def add_source(self, source_config: Dict[str, Any]) -> bool:
        """Dodaje nowe źródło."""
        name = source_config.get('name')
        if not name:
            return False
        
        # Usuń istniejące źródło o tej samej nazwie
        self._config['sources'] = [s for s in self.sources if s.get('name') != name]
        self._config['sources'].append(source_config)
        return self.save()
    
    def update_source(self, name: str, updates: Dict[str, Any]) -> bool:
        """Aktualizuje źródło."""
        for source in self._config.get('sources', []):
            if source.get('name') == name:
                source.update(updates)
                return self.save()
        return False
    
    def delete_source(self, name: str) -> bool:
        """Usuwa źródło."""
        original_len = len(self.sources)
        self._config['sources'] = [s for s in self.sources if s.get('name') != name]
        
        if len(self._config['sources']) < original_len:
            return self.save()
        return False
    
    def toggle_source(self, name: str) -> Optional[bool]:
        """Przełącza enabled źródła. Zwraca nowy stan lub None."""
        for source in self._config.get('sources', []):
            if source.get('name') == name:
                source['enabled'] = not source.get('enabled', True)
                self.save()
                return source['enabled']
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Zwraca pełną konfigurację jako słownik."""
        return self._config.copy()
