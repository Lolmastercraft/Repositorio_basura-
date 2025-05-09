# Dockerfile
FROM python:3.11-slim

# 1 – Dependencias de sistema mínimas
RUN apt-get update && apt-get install -y gcc build-essential && rm -rf /var/lib/apt/lists/*

# 2 – Crear directorio de trabajo
WORKDIR /app

# 3 – Copiar requirements e instalar
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4 – Copiar el resto del código
COPY backend/ backend/
COPY public/ public/

# 5 – Variables de entorno (no metas credenciales aquí)
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    AWS_REGION=us-east-1

EXPOSE 5000

# 6 – Comando final (Gunicorn)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "backend.app:app"]