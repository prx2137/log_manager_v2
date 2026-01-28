@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

cd /d "%~dp0"

:MENU
cls
echo ====================================================
echo           LOG MANAGER v2
echo ====================================================
echo.
echo   [1] Uruchom wszystko (Docker + Backend + Frontend)
echo   [2] Tylko Backend
echo   [3] Tylko Frontend
echo   [4] Docker (Elasticsearch + Kibana)
echo   [5] Zatrzymaj Docker
echo   [6] Status
echo   [7] SETUP (instalacja)
echo   [0] Wyjscie
echo.
echo ====================================================

set /p choice="Wybierz opcje: "

if "%choice%"=="1" goto RUN_ALL
if "%choice%"=="2" goto RUN_BACKEND
if "%choice%"=="3" goto RUN_FRONTEND
if "%choice%"=="4" goto RUN_DOCKER
if "%choice%"=="5" goto STOP_DOCKER
if "%choice%"=="6" goto STATUS
if "%choice%"=="7" goto SETUP
if "%choice%"=="0" goto END

goto MENU

:RUN_ALL
echo.
echo [*] Uruchamiam Docker...
docker-compose up -d
echo.
echo [*] Czekam na Elasticsearch (30s)...
timeout /t 30 /nobreak > nul

echo.
echo [*] Uruchamiam Backend...
start "Backend" cmd /k "cd backend && call venv\Scripts\activate && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo [*] Uruchamiam Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================================
echo   GOTOWE!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   Kibana:   http://localhost:5601
echo   Elastic:  http://localhost:9200
echo ====================================================
pause
goto MENU

:RUN_BACKEND
echo.
echo [*] Uruchamiam Backend...
cd backend
call venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd ..
pause
goto MENU

:RUN_FRONTEND
echo.
echo [*] Uruchamiam Frontend...
cd frontend
npm run dev
cd ..
pause
goto MENU

:RUN_DOCKER
echo.
echo [*] Uruchamiam Docker (Elasticsearch + Kibana)...
docker-compose up -d
echo.
echo [*] Czekam na uruchomienie...
timeout /t 30 /nobreak
echo.
echo [OK] Docker uruchomiony
echo     Elasticsearch: http://localhost:9200
echo     Kibana: http://localhost:5601
pause
goto MENU

:STOP_DOCKER
echo.
echo [*] Zatrzymuje Docker...
docker-compose down
echo [OK] Docker zatrzymany
pause
goto MENU

:STATUS
echo.
echo === STATUS ===
echo.

echo [Docker]
docker-compose ps 2>nul
echo.

echo [Elasticsearch]
curl -s http://localhost:9200/_cluster/health 2>nul || echo Niedostepny
echo.

echo [Backend]
curl -s http://localhost:8000/api/health 2>nul || echo Niedostepny
echo.

pause
goto MENU

:SETUP
echo.
echo ====================================================
echo              SETUP - Instalacja
echo ====================================================
echo.

echo [1/3] Tworzenie venv Python...
cd backend
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/3] Instalacja pakietow Python...
pip install --upgrade pip
pip install fastapi uvicorn[standard] pyyaml pydantic mysql-connector-python pymongo elasticsearch python-multipart aiofiles

echo.
echo [3/3] Instalacja pakietow Node.js...
cd ..\frontend
call npm install

cd ..

echo.
echo ====================================================
echo   SETUP ZAKONCZONY!
echo.
echo   Teraz wybierz opcje 1 aby uruchomic aplikacje.
echo ====================================================
pause
goto MENU

:END
echo.
echo Do zobaczenia!
exit /b 0
