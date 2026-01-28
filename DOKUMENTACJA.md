# Log Manager - Pelna Dokumentacja

## Spis tresci

1. [Wstep](#wstep)
2. [Frontend Logger](#frontend-logger)
2. [Architektura](#architektura)
3. [Wymagania systemowe](#wymagania-systemowe)
4. [Instalacja](#instalacja)
5. [Konfiguracja zrodel](#konfiguracja-zrodel)
6. [Interfejs uzytkownika](#interfejs-uzytkownika)
7. [API Reference](#api-reference)
8. [Elasticsearch i Kibana](#elasticsearch-i-kibana)
9. [Rozwiazywanie problemow](#rozwiazywanie-problemow)
10. [FAQ](#faq)

---

## Wstep

Log Manager to aplikacja do monitorowania i analizy logow z roznych zrodel:
- **Pliki lokalne** (np. logi Laravel, logi systemowe)
- **Bazy danych MySQL** (general_log)
- **MongoDB Atlas** (zdalne kolekcje z wykrywaniem zmian w czasie rzeczywistym)

Aplikacja oferuje:
- Zbieranie logow w czasie rzeczywistym
- Filtrowanie i wyszukiwanie
- Statystyki i wizualizacje
- Integracje z Kibana dla zaawansowanej analizy
- Przechowywanie w Elasticsearch
- **Logi z frontendu Vue** (zbieranie logow z aplikacji frontendowej)

---

## Frontend Logger

Aplikacja zawiera wbudowany system logowania dla frontendu Vue.js. Wszystkie logi z frontendu sa automatycznie wysylane do backendu i przechowywane w Elasticsearch.

### Jak to dziala

```
Vue Frontend  -->  POST /api/logs/frontend  -->  Backend  -->  Elasticsearch
     |                                              |
  Logger service                              source_type: "frontend"
  (przechwytuje console.*, bledy, eventy)
```

### Automatyczne zbieranie

Logger automatycznie przechwytuje:
- `console.log()`, `console.info()`, `console.warn()`, `console.error()`
- Nieobsluzone bledy JavaScript (`window.onerror`)
- Nieobsluzone Promise rejections
- Bledy Vue.js (`app.config.errorHandler`)
- Ostrzezenia Vue.js (`app.config.warnHandler`)

### Uzycie w komponencie Vue

```typescript
<script setup lang="ts">
import { useLogger } from '../services/logger'

// Utworz logger dla komponentu
const log = useLogger('MojKomponent')

// Logowanie
log.debug('Ladowanie danych', { userId: 123 })
log.info('Uzytkownik zalogowany', { email: 'test@example.com' })
log.warn('Sesja wygasa za 5 minut')
log.error('Blad API', { status: 500 }, new Error('Network error'))
</script>
```

### Konfiguracja loggera

W pliku `main.ts`:

```typescript
import { logger, LoggerPlugin } from './services/logger'

// Inicjalizuj logger
logger.init({
  interceptConsole: true,  // Przechwytuj console.log/warn/error
  flushIntervalMs: 3000,   // Wysylaj co 3 sekundy
  enabled: true            // Wlacz/wylacz
})
```

### Filtrowanie logow frontendowych

W dashboardzie mozesz filtrowac logi frontendowe:
- **Source**: `frontend`
- **Severity**: `DEBUG`, `INFO`, `WARNING`, `ERROR`

### Przyklady logow frontendowych

| Timestamp | Severity | Component | Message |
|-----------|----------|-----------|---------|
| 15:30:45 | INFO | App | Application started |
| 15:30:46 | INFO | DashboardView | Dashboard mounted |
| 15:30:47 | DEBUG | DashboardView | Logs refreshed (count: 150) |
| 15:30:50 | ERROR | API | Failed to fetch: Network error |

---

## Architektura

```
+------------------+     +------------------+     +------------------+
|    Frontend      |     |     Backend      |     |  Elasticsearch   |
|   (Vue.js)       | <-> |   (FastAPI)      | <-> |                  |
|   Port: 5173     |     |   Port: 8000     |     |   Port: 9200     |
+------------------+     +------------------+     +------------------+
                                |
                                v
              +----------------------------------+
              |           Zrodla logow           |
              +----------------------------------+
              | - Pliki lokalne (.log)           |
              | - MySQL (general_log)            |
              | - MongoDB Atlas (remote)         |
              | - Frontend Vue.js (console/errors)|
              +----------------------------------+
```

### Stack technologiczny

**Backend:**
- Python 3.11+
- FastAPI (framework webowy)
- Elasticsearch Python Client 8.x
- PyMySQL (MySQL)
- PyMongo + dnspython (MongoDB Atlas)

**Frontend:**
- Vue.js 3 + TypeScript
- Tailwind CSS
- Vite (bundler)
- Vue Router

**Infrastruktura:**
- Docker + Docker Compose
- Elasticsearch 8.x
- Kibana 8.x

---

## Wymagania systemowe

### Minimalne wymagania
- Windows 10/11 lub Linux
- 8 GB RAM (Elasticsearch wymaga min. 4 GB)
- 10 GB wolnego miejsca na dysku
- Docker Desktop (Windows) lub Docker Engine (Linux)
- Node.js 18+ (dla frontendu)
- Python 3.11+ (dla backendu)

### Porty
- `5173` - Frontend (Vue dev server)
- `8000` - Backend (FastAPI)
- `9200` - Elasticsearch
- `5601` - Kibana

---

## Instalacja

### 1. Uruchomienie Docker (Elasticsearch + Kibana)

```bash
docker-compose -f docker-compose-dev.yml up -d
```

Poczekaj 30-60 sekund az Elasticsearch sie uruchomi.

### 2. Uruchomienie aplikacji (Windows)

Kliknij dwukrotnie `start.bat` lub uruchom w terminalu:

```cmd
start.bat
```

### 3. Uruchomienie aplikacji (Linux/Mac)

```bash
chmod +x start.sh
./start.sh
```

### 4. Otworz przegladarke

- **Frontend**: http://localhost:5173
- **Kibana**: http://localhost:5601

---

## Konfiguracja zrodel

### Plik (File)

Monitoruje pliki tekstowe (logi Laravel, systemowe itp.)

**Parametry:**
| Parametr | Opis | Przyklad |
|----------|------|----------|
| Name | Unikalna nazwa zrodla | `laravel-logs` |
| Path | Sciezka do pliku lub katalogu | `C:\laravel\storage\logs\` |

**Wsparcie dla Windows:**
- Sciezki z backslashami: `C:\Users\nazwa\logi\app.log`
- Sciezki z forwardslashami: `C:/Users/nazwa/logi/app.log`
- Automatyczna normalizacja sciezek

**Zachowanie:**
- Przy pierwszym uruchomieniu: czyta ostatnie 50KB pliku
- Potem: monitoruje tylko nowe linie
- Rozpoznaje formaty: Laravel, Apache, Nginx, JSON

---

### MySQL

Monitoruje tabele `mysql.general_log` dla operacji SQL.

**Wymagane ustawienia MySQL:**
```sql
SET GLOBAL general_log = 'ON';
SET GLOBAL log_output = 'TABLE';
```

**Parametry:**
| Parametr | Opis | Przyklad |
|----------|------|----------|
| Name | Nazwa zrodla | `mysql-main` |
| Host | Adres serwera MySQL | `localhost` |
| Port | Port MySQL | `3306` |
| User | Uzytkownik MySQL | `root` |
| Password | Haslo | `secret` |
| Database | Baza (opcjonalnie) | `myapp` |

**Zbierane dane:**
- event_time - czas zapytania
- user_host - uzytkownik i host
- argument - tresc zapytania SQL
- command_type - typ komendy (Query, Connect, Quit)

---

### MongoDB Atlas

Monitoruje kolekcje w MongoDB Atlas (zdalne).

**Parametry:**
| Parametr | Opis | Przyklad |
|----------|------|----------|
| Name | Nazwa zrodla | `mongo-atlas` |
| URI | Pelny connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| Database | Nazwa bazy | `log_manager` |
| Collection | Nazwa kolekcji | `events` |

**Alternatywnie (pola osobno):**
| Parametr | Opis |
|----------|------|
| Username | Uzytkownik Atlas |
| Password | Haslo |
| Cluster | Nazwa clustera (np. `logmanager.nivuikh`) |

**Wazne:**
1. Musisz dodac swoje IP do Network Access w MongoDB Atlas
2. Dla developmentu mozesz dodac `0.0.0.0/0` (wszystkie IP)
3. Utworz baze danych i kolekcje przed polaczeniem

**Wykrywanie zmian:**
Aplikacja wykrywa:
- **INITIAL_LOAD** - wszystkie istniejace dokumenty przy starcie
- **INSERT** - nowe dokumenty
- **UPDATE** - zmiany w istniejacych dokumentach (porownanie hashy)
- **DELETE** - usuniete dokumenty

---

## Interfejs uzytkownika

### Dashboard (Logs)

Glowny widok z lista logow.

**Funkcje:**
- **Tabela logow** - timestamp, source, severity, event_type, message
- **Filtry** - wyszukiwanie tekstowe, severity, event_type, source
- **Refresh** - reczne odswiezenie
- **Auto-refresh** - automatyczne odswiezanie co 3 sekundy
- **Reset Logs** - czysci wszystkie logi (z potwierdzeniem)
- **Szczegoly loga** - kliknij na wiersz aby zobaczyc pelne dane

**Statystyki (na gorze):**
- Total Logs - liczba wszystkich logow
- Errors - liczba bledow
- Warnings - liczba ostrzezen
- Sources - liczba aktywnych zrodel

---

### Statistics

Statystyki i wykresy.

**Sekcje:**
- **Karty podsumowania** - Total, Errors, Warnings, Info
- **Log Levels Distribution** - paski procentowe dla severity
- **Database Operations** - paski dla SELECT/INSERT/UPDATE/DELETE
- **Sources Distribution** - rozklad logow wg zrodel

**Przycisk "Open Kibana"** - otwiera Kibana dla zaawansowanej analizy

**Auto-refresh:** Statystyki odswiezaja sie co 5 sekund

---

### Sources

Zarzadzanie zrodlami logow.

**Funkcje:**
- **Lista zrodel** - nazwa, typ, status, liczba zebranych logow
- **Add Source** - dodaj nowe zrodlo
- **Start/Stop** - wlacz/wylacz monitorowanie
- **Delete** - usun zrodlo

**Formularz dodawania:**
1. Wybierz typ (file/mysql/mongodb)
2. Wypelnij wymagane pola
3. Kliknij Add
4. Kliknij Start przy nowym zrodle

---

## API Reference

### GET /api/logs

Pobierz liste logow.

**Query parameters:**
| Param | Typ | Opis |
|-------|-----|------|
| source | string | Filtruj po nazwie zrodla |
| level | string | Filtruj po severity (ERROR, WARN, INFO, DEBUG) |
| operation | string | Filtruj po event_type |
| query | string | Wyszukiwanie tekstowe |
| limit | int | Max liczba wynikow (domyslnie 200) |

**Response:**
```json
{
  "logs": [...],
  "total": 1234
}
```

---

### DELETE /api/logs

Wyczysc wszystkie logi.

**Response:**
```json
{
  "status": "ok",
  "cleared_memory": 100,
  "cleared_es": 100
}
```

---

### GET /api/sources

Pobierz liste zrodel.

**Response:**
```json
{
  "sources": [
    {
      "name": "laravel",
      "config": {...},
      "enabled": true,
      "running": true,
      "logs_collected": 50
    }
  ]
}
```

---

### POST /api/sources

Dodaj nowe zrodlo.

**Body (file):**
```json
{
  "name": "app-logs",
  "type": "file",
  "path": "C:\\logs\\app.log"
}
```

**Body (mongodb):**
```json
{
  "name": "mongo-events",
  "type": "mongodb",
  "uri": "mongodb+srv://user:pass@cluster.mongodb.net/",
  "database": "mydb",
  "collection": "events"
}
```

---

### POST /api/sources/{name}/start

Uruchom zbieranie z zrodla.

---

### POST /api/sources/{name}/stop

Zatrzymaj zbieranie ze zrodla.

---

### DELETE /api/sources/{name}

Usun zrodlo.

---

### GET /api/debug/logs

Stan debugowania - logi w pamieci, status zrodel.

---

### GET /api/debug/elasticsearch

Szczegolowy stan Elasticsearch:
- Liczba dokumentow
- Podzial wg source_type
- Ostatnie logi

---

### POST /api/debug/sync-to-es

Recznie synchronizuj logi z pamieci do Elasticsearch.

---

## Elasticsearch i Kibana

### Konfiguracja Elasticsearch

Aplikacja automatycznie:
1. Laczy sie z ES na `http://localhost:9200`
2. Tworzy index pattern `log-manager-*`
3. Tworzy indexy dzienne `log-manager-YYYY.MM.DD`

### Mapping (schemat)

```json
{
  "timestamp": "date",
  "message": "text",
  "raw": "text", 
  "severity": "keyword",
  "event_type": "keyword",
  "source": "keyword",
  "source_type": "keyword",
  "collected_at": "date",
  "extra": "object"
}
```

### Konfiguracja Kibana

1. Otworz http://localhost:5601
2. Idz do **Stack Management** > **Data Views**
3. Utworz nowy Data View:
   - Name: `Log Manager`
   - Index pattern: `log-manager-*`
   - Timestamp field: `timestamp`
4. Idz do **Discover** aby przegladac logi
5. **WAZNE:** Zmien zakres czasu z "Last 15 minutes" na wiekszy (np. "Last 7 days")

### Przydatne zapytania KQL (Kibana)

```
# Wszystkie bledy
severity: ERROR

# Logi z konkretnego zrodla
source: "laravel"

# Operacje INSERT/UPDATE
event_type: INSERT OR event_type: UPDATE

# Wyszukiwanie tekstowe
message: *exception*

# Kombinacja
severity: ERROR AND source: "mongodb-atlas"
```

---

## Rozwiazywanie problemow

### Problem: Logi sie nie wyswietlaja

**Sprawdz:**
1. Czy zrodlo jest uruchomione (Sources > Start)
2. Czy Elasticsearch jest dostepny: http://localhost:9200
3. Konsola backendu - powinny byc komunikaty `[ES] Zapisano X logow`
4. Endpoint debug: http://localhost:8000/api/debug/logs

**Rozwiazanie:**
- Kliknij Refresh w Dashboard
- Sprawdz `/api/debug/elasticsearch` - czy sa tam logi

---

### Problem: MongoDB Atlas nie laczy sie

**Bledy:**
- `connection timed out`
- `Authentication failed`

**Sprawdz:**
1. Czy IP jest na whitelist w MongoDB Atlas (Network Access)
2. Czy credentials sa poprawne
3. Czy connection string ma format: `mongodb+srv://user:pass@cluster.mongodb.net/`

**Debug:**
- Otworz endpoint: http://localhost:8000/api/sources
- Sprawdz `last_error` przy zrodle MongoDB

---

### Problem: Elasticsearch nie zapisuje logow

**Sprawdz:**
1. Czy ES jest uruchomiony: `docker ps`
2. Czy kontener ES ma wystarczajaco pamieci
3. Endpoint: http://localhost:8000/api/debug/elasticsearch

**Rozwiazanie:**
- Uzyj `/api/debug/sync-to-es` do recznej synchronizacji
- Zrestartuj kontenery: `docker-compose -f docker-compose-dev.yml restart`

---

### Problem: Pliki Windows - bledna sciezka

**Blad:** `FileNotFoundError`

**Rozwiazanie:**
- Uzyj sciezki absolutnej: `C:\Users\nazwa\logi\app.log`
- Lub uzyj forward slashes: `C:/Users/nazwa/logi/app.log`
- Aplikacja automatycznie normalizuje sciezki

---

### Problem: MySQL general_log pusty

**Sprawdz:**
```sql
SHOW VARIABLES LIKE 'general_log';
SHOW VARIABLES LIKE 'log_output';
SELECT COUNT(*) FROM mysql.general_log;
```

**Wlacz logowanie:**
```sql
SET GLOBAL general_log = 'ON';
SET GLOBAL log_output = 'TABLE';
```

---

## FAQ

### Jak czesto zbierane sa logi?

Collector odpytuje zrodla co 2 sekundy.

### Ile logow przechowuje aplikacja?

- W pamieci: max 10,000 logow
- W Elasticsearch: bez limitu (zalezy od miejsca na dysku)

### Czy moge uzywac bez Elasticsearch?

Tak - aplikacja dziala z logami w pamieci. ES jest opcjonalny ale zalecany dla persistence.

### Jak wyeksportowac logi?

1. Przez Kibana - eksport do CSV/JSON
2. Przez API - `GET /api/logs?limit=10000`
3. Bezposrednio z ES: `GET /log-manager-*/_search`

### Czy aplikacja wspiera HTTPS?

W obecnej wersji - nie. Dla produkcji zaleca sie uzycie reverse proxy (nginx) z certyfikatem SSL.

### Jak dodac nowy typ zrodla?

1. Utworz klase w `sources.py` dziedziczaca z `BaseSource`
2. Zaimplementuj metode `collect() -> List[ParsedLog]`
3. Dodaj do `create_source()` w `main.py`

---

## Changelog

### v2.0.0 (2026-01-27)

- Przebudowa architektury (FastAPI + Vue 3)
- Pelna integracja z Elasticsearch 8.x
- MongoDB Atlas z wykrywaniem zmian w czasie rzeczywistym
- Nowy interfejs uzytkownika (Tailwind CSS)
- Filtrowanie po severity i event_type
- Auto-refresh w Dashboard i Statistics
- Szczegoly logow po kliknieciu
- Debugowanie przez API

---

## Licencja

MIT License

## Kontakt

Problemy i sugestie: [GitHub Issues]

---

## Testy

### Struktura testow

```
log_manager_v2/
├── backend/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Fixtures i konfiguracja pytest
│   │   ├── test_smart_parser.py # Testy parsera logow
│   │   ├── test_api.py          # Testy API REST
│   │   ├── test_sources.py      # Testy zrodel logow
│   │   └── test_integration.py  # Testy integracyjne
│   ├── pytest.ini               # Konfiguracja pytest
│   └── requirements-dev.txt     # Zaleznosci testowe
├── frontend/
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── logger.spec.ts    # Testy loggera
│   │   │   └── components.spec.ts # Testy komponentow
│   │   └── e2e/                  # Testy E2E (opcjonalne)
│   └── vitest.config.ts          # Konfiguracja Vitest
├── run_tests.bat                 # Skrypt testowy (Windows)
└── run_tests.sh                  # Skrypt testowy (Linux/Mac)
```

### Uruchamianie testow

#### Windows
```batch
run_tests.bat
```

#### Linux/Mac
```bash
chmod +x run_tests.sh
./run_tests.sh
```

#### Recznie - Backend
```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

#### Recznie - Frontend
```bash
cd frontend
npm install
npm run test
```

### Rodzaje testow

#### Testy jednostkowe (Unit Tests)
- Testuja pojedyncze funkcje/klasy w izolacji
- Szybkie wykonanie
- Uzycie mockow dla zaleznosci zewnetrznych

**Przyklady:**
- `test_smart_parser.py` - parsowanie roznych formatow logow
- `logger.spec.ts` - logowanie z frontendu

#### Testy integracyjne (Integration Tests)
- Testuja wspolprace wielu komponentow
- Moga wymagac uslug zewnetrznych (ES, bazy danych)

**Przyklady:**
- `test_api.py` - testy endpointow REST
- `test_integration.py` - pelny przeplyw danych

#### Pokrycie kodu (Code Coverage)

Backend:
```bash
pytest tests/ --cov=. --cov-report=html
```

Frontend:
```bash
npm run test:coverage
```

### Pisanie nowych testow

#### Backend (pytest)
```python
import pytest
from smart_parser import SmartParser

class TestMyFeature:
    @pytest.fixture
    def setup(self):
        # Setup fixture
        return SmartParser()
    
    def test_feature_works(self, setup):
        result = setup.parse("test line", "source", "file")
        assert result is not None
        assert result.message == "test line"
```

#### Frontend (Vitest)
```typescript
import { describe, it, expect } from 'vitest'

describe('MyComponent', () => {
  it('should render correctly', () => {
    // Test logic
    expect(true).toBe(true)
  })
})
```

### Fixtures (Backend)

Dostepne fixtures w `conftest.py`:

| Fixture | Opis |
|---------|------|
| `sample_log_lines` | Przykladowe linie logow (Apache, Laravel, syslog, JSON) |
| `sample_parsed_logs` | Lista obiektow ParsedLog |
| `sample_log_dicts` | Logi jako slowniki (jak w ES) |
| `mock_elasticsearch` | Mock klienta ES |
| `mock_mysql_connection` | Mock polaczenia MySQL |
| `mock_mongodb_client` | Mock klienta MongoDB |
| `test_client` | FastAPI TestClient |
| `temp_log_file` | Tymczasowy plik logu |

### CI/CD

Przykladowa konfiguracja GitHub Actions (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      elasticsearch:
        image: elasticsearch:8.11.0
        env:
          discovery.type: single-node
          xpack.security.enabled: false
        ports:
          - 9200:9200
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Backend Dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      
      - name: Run Backend Tests
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=xml
      
      - name: Install Frontend Dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm run test:run -- --coverage
```

---

## Paginacja

### Backend API

Endpoint `/api/logs` obsluguje paginacje:

| Parametr | Typ | Domyslnie | Opis |
|----------|-----|-----------|------|
| `page` | int | 1 | Numer strony (1-indexed) |
| `page_size` | int | 50 | Ilosc logow na strone (max: 500) |
| `severity` | string | - | Filtruj po poziomie |
| `event_type` | string | - | Filtruj po typie zdarzenia |
| `source` | string | - | Filtruj po zrodle |
| `query` | string | - | Wyszukiwanie tekstowe |

### Odpowiedz API

```json
{
  "logs": [...],
  "total": 150,
  "total_all": 500,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

| Pole | Opis |
|------|------|
| `logs` | Lista logow dla danej strony |
| `total` | Ilosc logow po filtrowaniu |
| `total_all` | Calkowita ilosc wszystkich logow |
| `page` | Aktualna strona |
| `page_size` | Rozmiar strony |
| `total_pages` | Calkowita ilosc stron |

### Frontend

Dashboard zawiera:
- Przyciski nawigacji (First, Prev, numery stron, Next, Last)
- Wybor ilosci logow na strone (25, 50, 100, 200)
- Pole "Go to page" do bezposredniego przejscia
- Informacja o zakresie wyswietlanych logow

