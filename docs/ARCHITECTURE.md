# Architecture: Scheduler, Worker, and System Design

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI (Async), SQLAlchemy (Async), Pydantic |
| **Database** | PostgreSQL (production), SQLite (development/testing) |
| **Task Queue** | Redis + Arq |
| **Scheduling** | asyncio.sleep() + custom cron parser + Redis version polling |
| **AI/LLM** | OpenAI, Anthropic, DeepSeek, OpenRouter, Gemini, Ollama, LM Studio |
| **Frontend** | Server-side rendered Jinja2 + TailwindCSS + Vanilla JS |
| **Infrastructure** | Docker & Docker Compose |
| **CI/CD** | Woodpecker CI (`.woodpecker.yml`) |

---

## Project Structure

```
hn-ai-summarizer/
├── app/
│   ├── api/           # FastAPI routes (REST endpoints)
│   ├── core/          # Config, database, dependency injection
│   ├── models/        # SQLAlchemy models (Story, Setting, Preference)
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic (fetcher, AI service, provider registry)
│   ├── tasks/         # Background jobs (worker, scheduler)
│   ├── templates/     # Jinja2 HTML templates
│   ├── utils/         # Scraping utilities
│   └── cli.py         # CLI entry point
├── docs/              # Documentation
├── migrations/        # Alembic database migrations
├── tests/             # Test suite
├── docker-compose.yml # Docker Compose (production)
├── docker-compose.dev.yml # Docker Compose (development)
├── Dockerfile
├── start.ps1          # Windows native startup script
├── start.sh           # Unix native startup script
└── pyproject.toml     # Python project configuration
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories/` | Paginated story list |
| GET | `/api/stories/{id}` | Single story detail |
| POST | `/api/stories/feedback/negative/{story_id}` | Mark story as irrelevant |
| GET | `/api/settings/schedule-status` | Current schedule status |
| POST | `/api/settings/` | Update settings (AI provider, schedule) |
| GET | `/api/preferences/` | User keyword preferences |
| GET | `/health` | Health check |

---

## CI/CD

The project uses [Woodpecker CI](.woodpecker.yml) for continuous integration and delivery, with Docker image publishing.

---

## System Architecture Overview

The application is built as a **three-process asynchronous system** connected through Redis. Each process runs independently and communicates via two Redis channels:

1. **Arq Task Queue** — For enqueuing background jobs (worker consumes these)
2. **Schedule State Store** — For sharing schedule configuration between processes

```
┌───────────────────────────────────────────────────────────────────┐
│                        DOCKER / HOST                              │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐     │
│  │   SERVER     │    │  SCHEDULER   │    │     WORKER       │     │
│  │ (FastAPI)    │    │ (asyncio     │    │   (Arq Worker)   │     │
│  │              │    │  sleep loop) │    │                  │     │
│  │  Web UI      │    │  Cron Check  │    │  Process Story   │     │
│  │  REST API    │    │  Version     │    │  AI Translate    │     │
│  │  Settings    │    │  Polling     │    │  Summarize       │     │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘     │
│         │                   │                     │               │
│         └──────────┬────────┴──────────┬──────────┘               │
│                    │                   │                          │
│                    ▼                   ▼                          │
│         ┌─────────────────────────────────────┐                   │
│         │              REDIS                  │                   │
│         │  ┌────────────────┬──────────────┐  │                   │
│         │  │  Arq Queue     │  Schedule    │  │                   │
│         │  │  (jobs)        │  State Store │  │                   │
│         │  └────────────────┴──────────────┘  │                   │
│         └─────────────────────────────────────┘                   │
│                                                                   │
│         ┌─────────────────────────────────────┐                   │
│         │          DATABASE                   │                   │
│         │  (PostgreSQL / SQLite)              │                   │
│         │   Stories │ Settings │ Preferences  │                   │
│         └─────────────────────────────────────┘                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 1. Scheduler (`app/tasks/scheduler.py`)

### 1.1 Purpose

The scheduler is a long-running, **self-contained** Python process that runs a simple `asyncio.sleep()` loop with built-in cron parsing. It periodically checks whether it's time to fetch new stories, monitors Redis for real-time schedule changes, and handles periodic cleanup of old activity logs. No external scheduling library is used.

### 1.2 Lifecycle

```
[Scheduler Start]
       │
       ▼
┌──────────────────┐
│ Load Schedule    │──── Reads cron from Redis; falls back to DB → writes to Redis
│ & Version        │
└────────┬─────────┘
          │
          ▼
┌──────────────────┐
│ Calculate        │──── _calculate_next_run(cron, tz) → next fire datetime
│ Next Run         │
└────────┬─────────┘
          │
          ▼
┌──────────────────┐
│ Cleanup Old      │──── Delete AiActivityLog records older than 30 days
│ Logs             │
└────────┬─────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│ Main Loop (while True)                                       │
│                                                              │
│  1. Calculate sleep_seconds = next_run - now                 │
│  2. Sleep in 30s chunks → check Redis version each chunk     │
│  3. If version changed → reload cron from Redis/DB           │
│  4. When sleep ends → enqueue fetch_and_process_stories      │
│  5. Calculate next run time                                  │
│  6. Periodic: cleanup old logs at ~03:00                     │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 Key Functions

#### `run_scheduler()`
The main entry point — runs forever.

```python
async def run_scheduler():
    tz = get_tz()
    # 1. Load cron: Redis first, fallback DB → write to Redis
    redis_config = await get_schedule_from_redis()
    cron = redis_config["cron_schedule"] if redis_config else await get_schedule_from_db()

    # 2. Calculate initial next run
    next_run = calculate_next_run(cron, tz)

    # 3. Cleanup old logs
    await cleanup_old_logs()

    # 4. Main loop
    while True:
        sleep_seconds = max(0, (next_run - now).total_seconds())
        cron, version, next_run, sleep_seconds = \
            await sleep_with_schedule_check(sleep_seconds, cron, version, tz, next_run)
        await asyncio.sleep(sleep_seconds)
        await enqueue_worker_job()
        next_run = calculate_next_run(cron, tz, now=datetime.now(tz))
```

#### `_sleep_with_schedule_check(sleep_seconds, cron, version, tz, next_run)`
Sleeps in 30-second chunks. After each chunk, checks Redis version key. If version changed, reloads cron schedule from Redis (or DB fallback). Returns updated state.

**Version change fix (July 2026):** Even if the cron string hasn't changed, the version counter is updated to prevent the same version change from being re-detected every 30 seconds (infinite log spam bug).

#### `_calculate_next_run(cron, tz, now=None)`
Pure function — calculates the next fire datetime based on:
- Cron hour/minute fields
- Optional day-of-week filter (0=Sunday)
- Current time (default `datetime.now(tz)`)

If today's time hasn't passed → return today. Otherwise → walk forward up to 7 days.

#### `_enqueue_worker_job()`
Enqueues `fetch_and_process_stories` into the Arq Redis queue. Returns `True` on success.

#### `_cleanup_old_logs()`
Deletes `AiActivityLog` records older than 30 days. Called at startup and periodically around 03:00.

### 1.4 Cron Parsing Utilities

#### `_parse_cron_time(cron: str) -> tuple[int, int] | None`
Extracts hour and minute from a 5-field cron expression. Returns `(hour, minute)` or `None`.

| Cron | Output |
|------|--------|
| `"0 9 * * 1-5"` | `(9, 0)` |
| `"30 14 * * 1"` | `(14, 30)` |
| `"0 9 * * *"` | `(9, 0)` |

#### `_parse_cron_days(cron: str) -> list[int]`
Extracts the weekday field (5th position). Returns list of cron weekdays (0=Sunday..6=Saturday). Empty list means every day.

| Cron Field | Output | Meaning |
|-----------|--------|---------|
| `"1-5"` | `[1,2,3,4,5]` | Weekdays |
| `"1,3,5"` | `[1,3,5]` | Mon, Wed, Fri |
| `"*"` | `[]` | Every day |
| `"1"` | `[1]` | Monday only |

---

## 2. Redis Schedule Helpers (`app/tasks/scheduler.py` — inline)

### 2.1 Purpose

The scheduler uses Redis directly (without a separate `ScheduleManager` class) to store and synchronize the cron schedule between the server and scheduler processes.

### 2.2 Redis Key Schema

| Redis Key | Type | Purpose |
|-----------|------|---------|
| `hn_reader:schedule:config` | String (JSON) | Current schedule configuration: `{"cron_schedule": "..."}` |
| `hn_reader:schedule:version` | String (integer) | Monotonically increasing version counter for change detection |

### 2.3 Helper Functions

All Redis interaction is done through short-lived connection pools (created/closed per call):

| Function | Purpose |
|----------|---------|
| `_get_redis_pool()` | Creates a short-lived Arq Redis connection pool |
| `_get_schedule_from_redis() -> dict` | Reads and parses `hn_reader:schedule:config` |
| `_get_schedule_version() -> str` | Reads `hn_reader:schedule:version` |
| `_write_schedule_to_redis(cron)` | Writes config JSON + bumps version counter |

### 2.4 Version-Based Change Detection

The scheduler polls Redis version **inline during sleep** (every 30 seconds in `_sleep_with_schedule_check`), not via a separate background task:

1. Sleep 30 seconds → read `hn_reader:schedule:version`
2. Compare with local `current_version`
3. If changed → reload cron from Redis (or DB fallback) → recalculate `next_run`
4. Update local `current_version` to match Redis (prevents re-detection)
5. Repeat until target sleep time reached

---

## 3. Worker (`app/tasks/worker.py`)

### 3.1 Purpose

The worker is an **Arq**-based background process that consumes jobs from the Redis queue. It processes Hacker News stories through the AI pipeline: fetching content, translating titles, summarizing articles, and analyzing comments.

### 3.2 Arq Worker Configuration

```python
class WorkerSettings:
    functions = [
        process_story,
        fetch_and_process_stories,
        reprocess_untranslated_stories,
        debug_untranslated_stories,
        reprocess_all_stories,
    ]

    redis_settings = RedisSettings(host=..., port=..., ...)
    max_jobs = 10                    # Concurrent job limit
    job_timeout = 600                # 10 minutes per job
```

### 3.3 Job Queue Flow

```
fetch_and_process_stories (triggered by scheduler)
                    │
                    ▼
          ┌──────────────────┐
          │ Fetch top 100    │──── HN Firebase API
          │ story IDs        │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ Process each     │──── Concurrent fetcher.process_story()
          │ story            │     - Fetch details
          │                  │     - Scrape content (trafilatura)
          │                  │     - Fetch comments
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ Filter by        │──── Skip stories below min_score
          │ min_score        │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────────────────────────────┐
          │ Enqueue individual process_story jobs    │──── One job per story
          │ via ctx["redis"].enqueue_job(...)        │     in Redis queue
          └──────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
          ┌──────────────────┐                ┌──────────────────┐
          │ process_story    │                │ process_story    │
          │ (Story #1)       │                │ (Story #2)       │
          │                  │                │                  │
          │ 1. Check DB      │                │ 1. Check DB      │
          │ 2. AI Translate  │                │ 2. AI Translate  │
          │ 3. AI Summarize  │                │ 3. AI Summarize  │
          │ 4. Save to DB    │                │ 4. Save to DB    │
          └──────────────────┘                └──────────────────┘
```

### 3.4 `fetch_and_process_stories(ctx)`

This is the **main entry point** triggered by the scheduler. It:

1. Reads `min_score` from database settings (default: 100)
2. Calls `FetcherService.fetch_and_process_stories(min_score)` which:
   - Fetches top 100 story IDs from HN Firebase API
   - Concurrently processes each story (`asyncio.gather`)
   - Filters by minimum score
3. Enqueues each story as a separate `process_story` job in the Arq queue
4. Returns a summary string: `"New: 5, Skipped: 2, Errors: 0"`

### 3.5 `process_story(ctx, story_data)`

This function processes a single story through the AI pipeline:

```python
async def process_story(ctx, story_data):
    # 1. Check DB for existing story
    existing = await db.execute(select(Story).where(...))

    if existing and not existing.is_translated:
        # 2. AI: Translate title
        title_tr = await ai_service.translate_title(story.title, target_language)
        
        # 3. AI: Summarize content → 3 bullet points
        content_tr = await ai_service.summarize_content(story.content, target_language)
        
        # 4. AI: Analyze comments → meta-summary
        comments_summary = await ai_service.summarize_comments(story.comments, target_language)
        
        # 5. Save to DB
        story.is_translated = ai_service.check_translation_complete(story)
        await db.commit()

    elif not existing:
        # New story: full pipeline + negative feedback check
        is_blocked = await ai_service.check_negative_feedback(content, title)
        if not is_blocked:
            # Translate + summarize + save
            ...
```

### 3.6 AI Service Multi-Provider Architecture

The AI service (`app/services/ai_service.py`) supports seven providers through a unified interface:

```
AIService._call_ai(system_prompt, user_prompt)
    │
    ├── type == "openai-compat"  → _call_openai_compat()
    │     (OpenAI, DeepSeek, OpenRouter, LM Studio)
    │
    ├── type == "anthropic"      → _call_anthropic()
    │     (Claude SDK)
    │
    └── type == "ollama-http"    → _call_ollama()
          (Local LLM via HTTP API)
```

**Provider auto-detection:**
1. Read user's selected provider from DB (`Setting.ai_provider`)
2. If not set → detect available API keys from `.env`
3. If no keys → fall back to Ollama at `http://localhost:11434`

---

## 4. Data Flow: End-to-End Story Lifecycle

```
00:00  Scheduler checks cron: "0 9 * * 1-5" → today is Monday → time to fetch
  │
  ├── Scheduler enqueues: fetch_and_process_stories
  │
  ▼
Worker picks up fetch_and_process_stories
  │
  ├── Fetcher gets top 100 HN story IDs
  ├── For each ID: fetch details, scrape content, get comments
  ├── Filter: score >= 100
  │
  ├── Enqueue process_story for each filtered story
  │
  ▼
Worker picks up process_story #1
  │
  ├── Check DB: exists? → yes, needs translation?
  ├── AI: translate title → "AI Advances in 2026"
  ├── AI: summarize content → "- Point 1\n- Point 2\n- Point 3"
  ├── AI: summarize comments → "Discussion focused on..."
  │
  └── Save to DB → is_translated = True
  │
  ▼
User opens http://localhost:8000
  │
  ├── Jinja2 renders story list
  ├── Shows translated title, summary, comment analysis
  │
  └── User reads stories in their preferred language
```

---

## 5. Schedule Update Flow (API → Redis → Scheduler Sync)

When a user updates the schedule via the web interface:

```
User: changes cron to "0 14 * * 1,3,5" (14:00 on Mon/Wed/Fri)
  │
  ▼
POST /api/settings/ { cron_schedule: "0 14 * * 1,3,5" }
  │
  ▼
Server process:
  ├── Save to database (Setting.cron_schedule)
  ├── Write to Redis directly:
  │     ├── SET hn_reader:schedule:config = {"cron_schedule": "0 14 * * 1,3,5"}
  │     ├── INCR hn_reader:schedule:version
  │
  └── Response: 200 OK
  │
  ▼
Scheduler process (checking every 30s during sleep):
  ├── GET hn_reader:schedule:version → "5"
  ├── Compare with local version "4" → different!
  ├── GET hn_reader:schedule:config → {"cron_schedule": "0 14 * * 1,3,5"}
  ├── Calculate new next_run with updated cron
  ├── Update local version to "5"
  │
  └── Next fetch will happen at 14:00 on the next scheduled day (Mon/Wed/Fri)
```

---

## 6. Startup Scripts

### 6.1 Windows (`start.ps1`)

The PowerShell start script provides intelligent service management:

| Parameter | Behavior |
|-----------|----------|
| `-Mode server` | Starts only the FastAPI web server |
| `-Mode worker` | Starts only the Arq worker |
| `-Mode scheduler` | Starts only the scheduler |
| `-Mode all` | Starts server + worker + scheduler (requires Redis) |
| `-Mode full` (default) | Starts all services + auto-starts Redis container |
| `-NoMigration` | Skips Alembic migration on startup |

**Redis auto-detection:**
1. Checks TCP connectivity to `REDIS_HOST:REDIS_PORT`
2. If Redis is not running and Docker is available → starts a Redis container (`docker run -d --name hn-redis -p 6379:6379 redis:6-alpine`)
3. If Docker is not available → warns the user

### 6.2 Unix (`start.sh`)

Bash equivalent for Linux/macOS/Git Bash. Same service modes, with `--no-mig` flag for skipping migrations. Uses `/dev/tcp` for Redis connectivity checks (if `timeout` command is available).

---

## 7. Database Models

### 7.1 `Story`
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `hacker_news_id` | String (unique) | Original HN item ID |
| `title` | Text | Original English title |
| `title_tr` | Text | AI-translated title |
| `url` | Text | Story URL |
| `score` | Integer | HN upvote score |
| `author` | String | HN username |
| `content` | Text | Scraped article content |
| `content_tr` | Text | AI-summarized content in target language |
| `comments_summary` | Text | AI-generated discussion summary |
| `is_translated` | Boolean | Whether AI processing is complete |
| `is_blocked` | Boolean | Filtered by negative feedback |
| `created_at` | DateTime | When the story was fetched |

### 7.2 `Setting`
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `min_score` | Integer | Minimum HN score threshold |
| `cron_schedule` | String | Cron expression for scheduling |
| `ai_provider` | String | Selected AI provider ID |
| `ai_model` | String | Selected model name |
| `ai_provider_config` | JSON | Provider-specific config (base URL, etc.) |

### 7.3 `UserPreference`
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `keywords` | JSON | List of interest keywords for filtering |
| `translation_language` | String | Target language code (e.g., "en", "tr") |

### 7.4 `NegativeFeedback`
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer (PK) | Auto-increment ID |
| `story_id` | Integer (FK → Story) | Referenced story |
| `reason` | Text | Optional user feedback |

---

## 8. Concurrency Model

| Component | Concurrency Model | Details |
|-----------|------------------|---------|
| **FastAPI Server** | Asyncio (single process) | Async endpoints, async DB with SQLAlchemy |
| **Arq Worker** | Asyncio + multiprocessing | `max_jobs=10` concurrent jobs per worker |
| **Scheduler** | Asyncio (single process) | `asyncio.sleep()` + Redis version polling |
| **Fetcher** | Asyncio | `asyncio.gather` for concurrent HN API calls |
| **AI Service** | Blocking I/O in async | OpenAI/Anthropic SDKs called with timeouts |

---

## 9. Error Handling & Resilience

### Distributed Lock Safety
- Lock TTL: 10 seconds (prevents deadlocks from crashed processes)
- Lock retry: immediate failure (no busy-waiting)

### Job Timeouts
- Arq `job_timeout`: 600 seconds per job
- AI API calls: 300-600 second timeouts
- Network requests: 30 second timeouts

### Graceful Degradation
- AI provider unavailable → falls back to next available provider
- Redis unavailable → scheduler logs warning, worker skips processing
- Database unavailable → server returns 503, worker rolls back transaction

### Startup Resilience
- Catch-up fetch on scheduler restart ensures no stories are missed
- Schedule persists in Redis across container restarts
- Alembic migrations run automatically on startup