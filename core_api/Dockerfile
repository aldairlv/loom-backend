# 1. Imagen base
FROM python:3.13-slim

# 2. Optimización de Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 3. Dependencias del sistema
#RUN apt-get update && apt-get install -y \
#    libpq-dev \
 #   gcc \
  #  && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    ffmpeg \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# 4. Instalación de librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar proyecto
COPY . .

# 6. Exponer puerto
EXPOSE 8000

# 7. COMANDO AUTOMATIZADO
# Usamos sh -c para encadenar: migrate + runserver
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]