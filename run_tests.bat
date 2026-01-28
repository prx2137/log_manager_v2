@echo off
echo ========================================
echo    Log Manager - Test Suite Runner
echo ========================================
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [1/3] Running Backend Tests...
echo ----------------------------------------
cd backend
pip install -r requirements-dev.txt -q
pytest tests/ -v --tb=short
set BACKEND_EXIT=%ERRORLEVEL%
cd ..

echo.
echo [2/3] Running Frontend Tests...
echo ----------------------------------------
cd frontend
call npm install
call npm run test:run
set FRONTEND_EXIT=%ERRORLEVEL%
cd ..

echo.
echo ========================================
echo    Test Results Summary
echo ========================================
if %BACKEND_EXIT%==0 (
    echo Backend Tests:  PASSED
) else (
    echo Backend Tests:  FAILED
)

if %FRONTEND_EXIT%==0 (
    echo Frontend Tests: PASSED
) else (
    echo Frontend Tests: FAILED
)
echo ========================================

pause
