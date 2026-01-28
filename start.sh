#!/bin/bash

# Log Manager - Starter dla Linux/Mac

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           📊 LOG MANAGER - STARTER                   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  1. Uruchom wszystko (Docker + Backend + Frontend)   ║"
echo "║  2. Tylko Docker (Elasticsearch + Kibana)            ║"
echo "║  3. Tylko Backend (Python)                           ║"
echo "║  4. Tylko Frontend (Vue)                             ║"
echo "║  5. Zatrzymaj Docker                                 ║"
echo "║  0. Wyjście                                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "Wybierz opcję: " choice

case $choice in
  1)
    echo ""
    echo "[1/3] Uruchamiam Docker..."
    docker-compose -f docker-compose-dev.yml up -d
    
    echo "Czekam 30 sekund na Elasticsearch..."
    sleep 30
    
    echo ""
    echo "[2/3] Uruchamiam Backend..."
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    cd ..
    
    sleep 5
    
    echo ""
    echo "[3/3] Uruchamiam Frontend..."
    cd frontend
    npm install
    npm run dev &
    cd ..
    
    echo ""
    echo "✅ Wszystko uruchomione!"
    echo ""
    echo "📊 Frontend:     http://localhost:5173"
    echo "🔧 Backend API:  http://localhost:8000"
    echo "📈 Kibana:       http://localhost:5601"
    ;;
  
  2)
    echo "Uruchamiam Docker..."
    docker-compose -f docker-compose-dev.yml up -d
    echo "✅ Docker uruchomiony!"
    ;;
  
  3)
    echo "Uruchamiam Backend..."
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ;;
  
  4)
    echo "Uruchamiam Frontend..."
    cd frontend
    npm install
    npm run dev
    ;;
  
  5)
    echo "Zatrzymuję Docker..."
    docker-compose -f docker-compose-dev.yml down
    echo "✅ Docker zatrzymany!"
    ;;
  
  0)
    exit 0
    ;;
  
  *)
    echo "Nieprawidłowa opcja!"
    ;;
esac
