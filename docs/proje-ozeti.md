# HN-AI-Summerizer — Proje Özeti

## Nedir?

**HN-AI-Summerizer**, Hacker News'teki popüler hikâyeleri her gün otomatik olarak çeken, bunları yapay zekâ ile Türkçe'ye çevirip özetleyen ve kullanıcıya sade, mobil uyumlu bir arayüzle sunan bir web uygulamasıdır.

Proje, özellikle 40+ yaş grubu ve mobil kullanıcılar için erişilebilirlik odaklı tasarlanmıştır.

---

## Mimari Genel Bakış

```
HN Firebase API
      ↓
  Fetcher (app/services/fetcher.py)
      ↓
  Scraper (app/utils/scraper.py) — trafilatura ile makale içeriğini çeker
      ↓
  AI Service (app/services/ai_service.py) — çeviri + özet + yorum analizi
      ↓
  PostgreSQL / SQLite (Story, Setting, Preference, Feedback modelleri)
      ↓
  FastAPI + Jinja2 Templates → Kullanıcı Arayüzü
```

**İki ayrı süreç birlikte çalışır:**
- **Web sunucusu:** FastAPI ile REST API + Jinja2 şablonları sunar
- **Worker + Scheduler:** Arq (Redis) kuyruğu üzerinden arka planda hikâye çekme ve AI işleme yapar

---

## Teknolojiler

| Katman       | Teknoloji                                                    |
|-------------|--------------------------------------------------------------|
| Backend     | Python 3.11+, FastAPI, SQLAlchemy (Async), Pydantic          |
| Veritabanı  | PostgreSQL (üretim), SQLite (geliştirme/test)                 |
| İş Kuyruğu  | Redis + Arq                                                  |
| Zamanlama   | aioschedule + Redis tabanlı ScheduleManager                  |
| AI/LLM      | OpenAI (GPT-3.5) veya Ollama (yerel) — modüler geçiş desteği |
| Frontend    | Sunucu taraflı Jinja2 + TailwindCSS + Vanilla JS             |
| Altyapı     | Docker & Docker Compose                                      |

---

## Bileşenler

### 1. Veri Çekme ve İşleme Hattı

- **Fetcher** (`app/services/fetcher.py`): Hacker News Firebase API'sinden en çok oy alan hikâyeleri çeker.
- **Scraper** (`app/utils/scraper.py`): `trafilatura` kütüphanesiyle her hikâyenin bağlantısındaki makale içeriğini ayıklar.
- **AI Service** (`app/services/ai_service.py`): Üç ana işlevi vardır:
  - **translate_title()** — Başlığı Türkçe'ye çevirir
  - **summarize_content()** — Makale içeriğini 3 maddelik Türkçe özete dönüştürür
  - **summarize_comments()** — HN yorumlarını analiz edip tartışma özeti çıkarır
  - OpenAI varsa onu kullanır, yoksa Ollama (yerel LLM) ile devam eder

### 2. API Katmanı

- `GET /api/stories/` — Sayfalanmış hikâye listesi
- `GET /api/stories/{id}` — Tek hikâye detayı
- `POST /api/stories/feedback/negative/{story_id}` — Beğenilmedi bildirimi
- `GET /api/settings/schedule-status` — Zamanlama durumu
- `POST /api/settings/` — Ayarları güncelle (AI, zamanlama)
- `GET /api/preferences/` — Kullanıcı tercihleri (anahtar kelime filtreleme)
- `GET /health` — Sağlık kontrolü
- Web arayüzü: `/` (index), `/settings` (ayarlar)

### 3. Veritabanı Modelleri

- **Story** — HN hikâyesi (başlık, URL, puan, çeviri, özet, yorum özeti, engellenmiş mi?)
- **Setting** — Uygulama ayarları (AI sağlayıcı, Ollama URL/model, zamanlama cron'u)
- **UserPreference** — Kullanıcının ilgi alanlarına göre filtreleme için anahtar kelimeler
- **NegativeFeedback** — Beğenilmeyen içeriklerin kaydı

### 4. Zamanlama ve Senkronizasyon

- **ScheduleManager** (`app/tasks/schedule_manager.py`): Redis üzerinde cron zamanlamasını tutar
- **Worker** (`app/tasks/worker.py`): Arq kuyruğundan gelen işleri yürütür
- **Scheduler** (`app/tasks/scheduler.py`): `aioschedule` ile periyodik kontroller yapar
- İki ayrı süreç (web sunucusu ve scheduler) Redis üzerinden aynı zamanlamayı kullanır
- Herhangi bir süreç zamanlama değişikliğini Redis'teki versiyon numarası ile algılar

### 5. CLI

Proje, `hn-ai-summerizer` komutuyla tek bir noktadan yönetilir:
- `hn-ai-summerizer all` — Tüm servisleri başlatır
- `hn-ai-summerizer server` — Web sunucusu
- `hn-ai-summerizer worker` — Arq worker
- `hn-ai-summerizer scheduler` — Zamanlayıcı
- `hn-ai-summerizer test-schedule` — Zamanlama senkronizasyon testi

---

## Geliştirme Ortamı

```bash
# Kurulum
cp .env.example .env
docker-compose up

# Veya yerel geliştirme
pip install -r requirements.txt
# SQLite ile çalışır, PostgreSQL gerektirmez
```

---

## Öne Çıkan Tasarım Kararları

1. **AI sağlayıcı soyutlaması:** OpenAI yoksa otomatik olarak Ollama'ya düşer. Kullanıcı arayüzden hangi sağlayıcının kullanılacağını seçebilir.
2. **Çift süreçli mimari:** Web sunucusu ve scheduler ayrı process'lerde çalışır; Redis sayesinde zamanlama bilgisini paylaşırlar.
3. **Negatif geri bildirim:** Kullanıcı beğenmediği bir hikâyeyi işaretleyebilir, böylece benzer içeriklerin tekrar gelmesi engellenir.
4. **Erişilebilirlik:** Arayüz büyük fontlar, yüksek kontrast ve mobil öncelikli olarak 40+ yaş grubu düşünülerek tasarlanmıştır.
5. **Önce veri, sonra AI:** Hikâyeler önce ham halleriyle çekilip kaydedilir, ardından worker üzerinden AI işlemesi yapılır. Bu sayede API hemen yanıt verebilir.