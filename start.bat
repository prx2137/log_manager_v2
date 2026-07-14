@echo off
  chcp 65001 >nul
  setlocal EnableExtensions EnableDelayedExpansion

  rem Zawsze pracuj w katalogu, w ktorym znajduje sie start.bat.
  cd /d "%~dp0"

  rem Obsluga procesow uruchamianych w osobnych oknach.
  if /I "%~1"=="--backend" goto RUN_BACKEND_CHILD
  if /I "%~1"=="--frontend" goto RUN_FRONTEND_CHILD

  rem Wykryj nowa lub starsza skladnie Docker Compose.
  docker compose version >nul 2>&1
  if not errorlevel 1 (
      set "COMPOSE=docker compose"
  ) else (
      docker-compose version >nul 2>&1
      if not errorlevel 1 (
          set "COMPOSE=docker-compose"
      ) else (
          set "COMPOSE="
      )
  )

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

  set "choice="
  set /p "choice=Wybierz opcje: "

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
  call :CHECK_DOCKER
  if errorlevel 1 goto MENU
  call :CHECK_BACKEND
  if errorlevel 1 goto MENU
  call :CHECK_FRONTEND
  if errorlevel 1 goto MENU

  echo.
  echo [*] Usuwam kontenery pozostawione przez stara konfiguracje...
  call :REMOVE_LEGACY_CONTAINERS

  echo [*] Uruchamiam Docker (Elasticsearch + Kibana)...
  %COMPOSE% -f docker-compose-dev.yml up -d --remove-orphans
  if errorlevel 1 (
      echo [BLAD] Nie udalo sie uruchomic kontenerow Docker.
      pause
      goto MENU
  )

  echo.
  echo [*] Czekam na Elasticsearch (30s)...
  timeout /t 30 /nobreak >nul

  echo [*] Uruchamiam Backend...
  start "Log Manager - Backend" cmd /k call "%~f0" --backend

  echo [*] Uruchamiam Frontend...
  start "Log Manager - Frontend" cmd /k call "%~f0" --frontend

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
  call :CHECK_BACKEND
  if errorlevel 1 goto MENU
  start "Log Manager - Backend" cmd /k call "%~f0" --backend
  goto MENU

  :RUN_BACKEND_CHILD
  cd /d "%~dp0backend"
  echo [*] Uruchamiam Backend...
  "venv\Scripts\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
  if errorlevel 1 echo [BLAD] Backend zakonczyl dzialanie z bledem.
  pause
  exit /b

  :RUN_FRONTEND
  call :CHECK_FRONTEND
  if errorlevel 1 goto MENU
  start "Log Manager - Frontend" cmd /k call "%~f0" --frontend
  goto MENU

  :RUN_FRONTEND_CHILD
  cd /d "%~dp0frontend"
  echo [*] Uruchamiam Frontend...
  call npm run dev
  if errorlevel 1 echo [BLAD] Frontend zakonczyl dzialanie z bledem.
  pause
  exit /b

  :RUN_DOCKER
  call :CHECK_DOCKER
  if errorlevel 1 goto MENU

  echo.
  echo [*] Usuwam kontenery pozostawione przez stara konfiguracje...
  call :REMOVE_LEGACY_CONTAINERS

  echo [*] Uruchamiam Docker (Elasticsearch + Kibana)...
  %COMPOSE% -f docker-compose-dev.yml up -d --remove-orphans
  if errorlevel 1 (
      echo [BLAD] Nie udalo sie uruchomic kontenerow Docker.
      pause
      goto MENU
  )

  echo.
  echo [OK] Docker uruchomiony.
  echo      Elasticsearch: http://localhost:9200
  echo      Kibana:        http://localhost:5601
  pause
  goto MENU

  :STOP_DOCKER
  call :CHECK_DOCKER
  if errorlevel 1 goto MENU

  echo.
  echo [*] Zatrzymuje kontenery Docker...
  %COMPOSE% -f docker-compose-dev.yml down --remove-orphans
  call :REMOVE_LEGACY_CONTAINERS
  echo [OK] Kontenery Docker zatrzymane.
  pause
  goto MENU

  :STATUS
  echo.
  echo === STATUS ===
  echo.

  echo [Docker]
  if defined COMPOSE (
      %COMPOSE% -f docker-compose-dev.yml ps 2>nul
  ) else (
      echo Docker Compose jest niedostepny.
  )

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

  where py >nul 2>&1
  if errorlevel 1 (
      echo [BLAD] Nie znaleziono Python Launcher ^(py.exe^).
      echo Zainstaluj Python 3.12 z python.org i sprobuj ponownie.
      pause
      goto MENU
  )

  where npm >nul 2>&1
  if errorlevel 1 (
      echo [BLAD] Nie znaleziono npm. Zainstaluj Node.js LTS.
      pause
      goto MENU
  )

  echo [1/3] Tworzenie backend\venv...
  pushd backend
  py -3.12 -m venv venv
  if errorlevel 1 (
      popd
      echo [BLAD] Nie udalo sie utworzyc backend\venv.
      pause
      goto MENU
  )

  echo.
  echo [2/3] Instalacja pakietow Python...
  "venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 goto SETUP_PYTHON_ERROR
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto SETUP_PYTHON_ERROR
  popd

  echo.
  echo [3/3] Instalacja pakietow Node.js...
  pushd frontend
  call npm install
  if errorlevel 1 (
      popd
      echo [BLAD] Instalacja pakietow Node.js nie powiodla sie.
      pause
      goto MENU
  )
  popd

  echo.
  echo ====================================================
  echo   SETUP ZAKONCZONY!
  echo   Teraz wybierz opcje 1.
  echo ====================================================
  pause
  goto MENU

  :SETUP_PYTHON_ERROR
  popd
  echo [BLAD] Instalacja pakietow Python nie powiodla sie.
  pause
  goto MENU

  :CHECK_DOCKER
  if not defined COMPOSE (
      echo.
      echo [BLAD] Nie znaleziono Docker Compose.
      echo Uruchom Docker Desktop i sprawdz jego instalacje.
      pause
      exit /b 1
  )
  if not exist "docker-compose-dev.yml" (
      echo.
      echo [BLAD] Nie znaleziono pliku docker-compose-dev.yml.
      pause
      exit /b 1
  )
  docker info >nul 2>&1
  if errorlevel 1 (
      echo.
      echo [BLAD] Docker Desktop nie jest uruchomiony lub nie odpowiada.
      pause
      exit /b 1
  )
  exit /b 0

  :CHECK_BACKEND
  if not exist "backend\venv\Scripts\python.exe" (
      echo.
      echo [BLAD] Nie znaleziono backend\venv\Scripts\python.exe.
      echo Wybierz najpierw opcje 7 - SETUP.
      pause
      exit /b 1
  )
  exit /b 0

  :CHECK_FRONTEND
  where npm >nul 2>&1
  if errorlevel 1 (
      echo.
      echo [BLAD] Nie znaleziono npm. Zainstaluj Node.js LTS.
      pause
      exit /b 1
  )
  if not exist "frontend\package.json" (
      echo.
      echo [BLAD] Nie znaleziono frontend\package.json.
      pause
      exit /b 1
  )
  exit /b 0

  :REMOVE_LEGACY_CONTAINERS
  rem Te trzy nazwy pochodza ze starego docker-compose.yml.
  rem Ich usuniecie zapobiega uruchamianiu lacznie pieciu kontenerow.
  docker rm -f log-manager-es log-manager-kibana log-manager-backend >nul 2>&1
  exit /b 0

  :END
  echo.
  echo Do zobaczenia!
  endlocal
  exit /b 0
