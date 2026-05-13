# PATH: Dockerfile
# Agora AI — Django Uygulama Konteyner İmajı
# Doküman Bölüm 2.4: Docker + Docker Compose

FROM python:3.10-slim

# Çalışma ortamı değişkenleri
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Sistem bağımlılıklarını kur
# PyMuPDF (fitz) ve Pillow için gerekli kütüphaneler dahil
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libmupdf-dev \
    mupdf-tools \
    netcat-traditional \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini oluştur
WORKDIR /app

# Python bağımlılıklarını kur (önce bu katman — değişmediğinde cache kullanılır)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Statik dosyalar için dizin oluştur
RUN mkdir -p /app/staticfiles /app/media /data/chromadb /var/log/agora_ai

# Gerekli portları dışarı aç
EXPOSE 8000

# Varsayılan komut (docker-compose'da override edilir)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
