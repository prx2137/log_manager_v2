# =====================================================
# LOG MANAGER - BACKEND DOCKERFILE
# =====================================================

FROM python:3.11-slim

WORKDIR /app

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopiuj requirements i zainstaluj
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiuj kod aplikacji
COPY . .

# Expose port
EXPOSE 8000

# Uruchom
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
