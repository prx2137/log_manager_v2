# 📊 Log Manager v2

**Prosty system monitorowania baz danych i plików logów**

Monitoruje: **SELECT, INSERT, UPDATE, DELETE, ERROR**

---

## 🚀 Szybki Start (Windows)

### 1. Uruchom `start.bat`

### 2. Wybierz opcję **7 - SETUP** (tylko pierwszy raz)
   - Tworzy wirtualne środowisko Python (venv)
   - Instaluje wszystkie zależności

### 3. Wybierz opcję **1 - Uruchom WSZYSTKO**

### 4. Otwórz http://localhost:5173

---

## 📁 Struktura

```
log_manager_v2/
├── backend/
│   ├── venv/           <- wirtualne środowisko (po setup)
│   ├── main.py         <- API
│   ├── sources.py      <- źródła danych
│   ├── smart_parser.py <- parser logów
│   ├── config.yaml     <- konfiguracja
│   └── requirements.txt
├── frontend/
│   ├── node_modules/   <- (po npm install)
│   └── src/
├── start.bat           <- URUCHOM TO
└── docker-compose-dev.yml
```

---

## ⚙️ Wymagania

- **Python 3.10+**
- **Node.js 18+**
- **Docker Desktop** (dla Elasticsearch + Kibana)

---

## 🔧 Konfiguracja źródeł

Edytuj `backend/config.yaml`:

```yaml
sources:
  # Plik logów
  - name: "app-logs"
    type: file
    path: "C:/logs/app.log"

  # MySQL
  - name: "mysql-prod"
    type: mysql
    host: localhost
    port: 3306
    user: root
    password: haslo
    database: general_log

  # MongoDB
  - name: "mongo-audit"
    type: mongodb
    uri: "mongodb://localhost:27017"
    database: admin
    collection: system.profile
```

---

## 🌐 Adresy

| Serwis | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Kibana | http://localhost:5601 |
| Elasticsearch | http://localhost:9200 |

---

## 📊 Funkcje

- ✅ Monitorowanie plików .log/.txt
- ✅ Monitorowanie MySQL (general_log)
- ✅ Monitorowanie MongoDB (profiler)
- ✅ Automatyczne wykrywanie operacji SQL
- ✅ Statystyki per agent
- ✅ Czyszczenie logów jednym klikiem
- ✅ Kibana dashboards

---

## 🐛 Problemy?

**"No module named uvicorn"**
→ Uruchom opcję 7 (SETUP) w start.bat

**Docker nie działa**
→ Uruchom Docker Desktop

**Kibana nie łączy**
→ Poczekaj ~30 sekund i odśwież
