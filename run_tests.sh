#!/bin/bash
echo "========================================"
echo "   Log Manager - Test Suite Runner"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Activate venv if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[1/3] Running Backend Tests..."
echo "----------------------------------------"
cd backend
pip install -r requirements-dev.txt -q
pytest tests/ -v --tb=short
BACKEND_EXIT=$?
cd ..

echo ""
echo "[2/3] Running Frontend Tests..."
echo "----------------------------------------"
cd frontend
npm install --silent
npm run test:run
FRONTEND_EXIT=$?
cd ..

echo ""
echo "========================================"
echo "   Test Results Summary"
echo "========================================"
if [ $BACKEND_EXIT -eq 0 ]; then
    echo -e "Backend Tests:  ${GREEN}PASSED${NC}"
else
    echo -e "Backend Tests:  ${RED}FAILED${NC}"
fi

if [ $FRONTEND_EXIT -eq 0 ]; then
    echo -e "Frontend Tests: ${GREEN}PASSED${NC}"
else
    echo -e "Frontend Tests: ${RED}FAILED${NC}"
fi
echo "========================================"

# Exit with error if any tests failed
if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_EXIT -ne 0 ]; then
    exit 1
fi
