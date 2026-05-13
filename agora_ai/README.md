# Agora AI — Geçmişin Bilgeleriyle Dijital Diyalog

Sokrates'i sorgula, Kant'la tartış, Nietzsche'nin aforizmalarını keşfet.
Gemini AI destekli RAG mimarisiyle filozofların gerçek eserlerinden beslenen otantik diyaloglar.

---

## 📋 İçindekiler

- [Proje Mimarisi](#mimari)
- [Hızlı Başlangıç (Docker)](#hizli-baslangic)
- [Manuel Kurulum](#manuel-kurulum)
- [Çevre Değişkenleri](#cevre-degiskenleri)
- [Management Commands](#management-commands)
- [Testleri Çalıştırma](#testler)
- [Proje Yapısı](#proje-yapisi)

---

## Mimari

```
Kullanıcı → Django View → PromptBuilder
                               ↓          ↓
                          ChromaDB    Philosopher.system_prompt_template
                         (RAG Chunks)        ↓
                                       Gemini API (streaming)
                                             ↓
                                     SSE → Tarayıcı (EventSource)
```

**Tech Stack:**
- **Backend:** Django 5.0, DRF, Celery + Redis
- **AI:** Google Gemini 1.5 Flash (`google-generativeai`)
- **Vektör DB:** ChromaDB (persistent)
- **Ana DB:** PostgreSQL 16
- **Frontend:** Bootstrap 5.3 + Vanilla JS (SSE / EventSource)
- **Reverse Proxy:** Nginx (proxy_buffering off — SSE için kritik)

---

## Hızlı Başlangıç (Docker)

### Ön Koşullar
- Docker 24+
- Docker Compose v2+
- Gemini API anahtarı ([makersuite.google.com](https://makersuite.google.com/app/apikey))

### 1. Depoyu Klonla

```bash
git clone https://github.com/yourorg/agora-ai.git
cd agora-ai
```

### 2. `.env` Dosyasını Oluştur

```bash
cp .env.example .env
```

`.env` dosyasını düzenle, **zorunlu** alanları doldur:

```env
SECRET_KEY=your-very-secret-django-key-change-this
GEMINI_API_KEY=your-gemini-api-key-here
DB_PASSWORD=agora_password
```

### 3. Konteynerleri Başlat

```bash
docker compose up -d --build
```

### 4. Veritabanı & İlk Veriler

```bash
# Migration'ları uygula
docker compose exec web python manage.py migrate

# İlk 6 filozofu yükle
docker compose exec web python manage.py load_philosophers

# Süper kullanıcı oluştur
docker compose exec web python manage.py createsuperuser

# Statik dosyaları topla
docker compose exec web python manage.py collectstatic --noinput
```

### 5. Uygulamayı Aç

```
http://localhost
```

Admin paneli: `http://localhost/admin/`

---

## Manuel Kurulum

### Ön Koşullar
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- ChromaDB için yeterli disk alanı

### 1. Sanal Ortam

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows
```

### 2. Bağımlılıkları Kur

```bash
pip install -r requirements.txt
```

### 3. `.env` Ayarla

```bash
cp .env.example .env
# .env dosyasını düzenle
```

### 4. Veritabanı Hazırla

```bash
# PostgreSQL'de veritabanı ve kullanıcı oluştur
createuser -P agora_user
createdb -O agora_user agora_ai

python manage.py migrate --settings=config.settings.development
python manage.py load_philosophers --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
```

### 5. Sunucuları Başlat

**Terminal 1 — Django:**
```bash
python manage.py runserver --settings=config.settings.development
```

**Terminal 2 — Celery Worker:**
```bash
celery -A config worker -l info --concurrency 2
```

**Terminal 3 — Redis (gerekirse):**
```bash
redis-server
```

---

## Çevre Değişkenleri

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `SECRET_KEY` | Django gizli anahtar | — (zorunlu) |
| `DEBUG` | Hata ayıklama modu | `True` |
| `GEMINI_API_KEY` | Google Gemini API anahtarı | — (zorunlu) |
| `DB_NAME` | PostgreSQL veritabanı adı | `agora_ai` |
| `DB_USER` | PostgreSQL kullanıcısı | `agora_user` |
| `DB_PASSWORD` | PostgreSQL şifresi | — (zorunlu) |
| `DB_HOST` | PostgreSQL host | `db` (Docker) / `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_URL` | Redis bağlantı URL'i | `redis://redis:6379/0` |
| `CHROMA_PERSIST_DIR` | ChromaDB veri dizini | `/data/chromadb` |

---

## Management Commands

### `ingest_works` — Felsefi Eserleri İşle

```bash
# Tüm pending eserleri Celery kuyruğuna al
python manage.py ingest_works

# Belirli filozofun eserlerini işle
python manage.py ingest_works --philosopher immanuel-kant

# Senkron çalıştır (Celery olmadan, test/geliştirme için)
python manage.py ingest_works --sync

# Tamamlanmış eserleri de yeniden işle
python manage.py ingest_works --force

# Belirli bir eseri işle
python manage.py ingest_works --work-id 3 --sync
```

### `load_philosophers` — Filozofları Yükle

```bash
# İlk 6 filozofu fixture'dan yükle
python manage.py load_philosophers

# Sıfırlayarak yükle (mevcut filozofları sil)
python manage.py load_philosophers --reset
```

---

## Testleri Çalıştırma

```bash
# Tüm testleri çalıştır
pytest

# Hızlı testler (sadece birim)
pytest -m unit

# Entegrasyon testleri
pytest -m integration

# Belirli bir modül
pytest tests/test_rag.py -v

# Kapsam raporu ile
pytest --cov=apps --cov-report=html
```

---

## Filozoflara Eser Ekleme

1. **Admin paneline** giriş yap: `/admin/`
2. **Philosophers → Philosophical Works → Ekle**
3. Filozofu seç, başlığı gir, PDF veya TXT yükle
4. Kaydet — Celery worker otomatik olarak işleme başlar
5. **İzleme:** `/rag/upload/<filozof-slug>/` sayfasından durum takip edilebilir

**Desteklenen formatlar:** `.pdf`, `.txt` — Maksimum: **50 MB**

---

## Proje Yapısı

```
agora_ai/
├── apps/
│   ├── accounts/          # CustomUser, kayıt, giriş, profil
│   ├── conversations/     # Sohbet motoru, Gemini SSE, PromptBuilder
│   ├── glossary/          # Felsefi kavram sözlüğü
│   ├── philosophers/      # Filozof profilleri, eserler
│   ├── rag/               # ChromaDB, ingestion pipeline, Celery tasks
│   └── symposium/         # Çok-aktörlü tartışma modu
├── config/
│   ├── settings/
│   │   ├── base.py        # Ortak ayarlar
│   │   ├── development.py # Geliştirme
│   │   └── production.py  # Üretim
│   ├── celery.py
│   └── urls.py
├── static/
│   ├── css/main.css       # Agora koyu tema
│   └── js/main.js         # Global JS, tooltip, SSE yardımcıları
├── templates/
│   ├── base.html          # Global layout
│   └── home.html          # Landing sayfası
├── tests/                 # pytest test suite
├── nginx/nginx.conf       # SSE için proxy_buffering off
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## SSE (Server-Sent Events) Akışı

Doküman Bölüm 5.3 mimarisi:

```
POST /conversations/<id>/send/
  → Message(role=user) kaydet
  → {"stream_url": "/conversations/<id>/stream/<msg_id>/"}

GET /conversations/<id>/stream/<msg_id>/
  → RAG: query_chunks(philosopher, user_query)
  → PromptBuilder.build_system_prompt(rag_chunks)
  → gemini.send_message(stream=True)
  → StreamingHttpResponse(content_type="text/event-stream")
    data: "token1"\n\n
    data: "token2"\n\n
    ...
    data: [DONE]\n\n
  → Message(role=assistant) kaydet
```

**Nginx ayarı** (`nginx.conf`):
```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
```

---

## Lisans

MIT License — © 2025 Agora AI
