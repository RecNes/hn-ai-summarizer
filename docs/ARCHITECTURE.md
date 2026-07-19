# Architecture: Scheduler, Worker, and System Design

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI (Async), SQLAlchemy (Async), Pydantic |
| **Database** | PostgreSQL (production), SQLite (development/testing) |
| **Task Queue** | Redis + Arq |
| **Scheduling** | aioschedule + Redis-based ScheduleManager |
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
│   ├── tasks/         # Background jobs (worker, scheduler, schedule manager)
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
│  │ (FastAPI)    │    │ (aioschedule)│    │   (Arq Worker)   │     │
│  │              │    │              │    │                  │     │
│  │  Web UI      │    │  Cron Check  │    │  Process Story   │     │
│  │  REST API    │    │  Monitor     │    │  AI Translate    │     │
│  │  Settings    │    │  Catch-up    │    │  Summarize       │     │
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

The scheduler is a long-running Python process that periodically checks whether it's time to fetch new stories based on a cron schedule stored in Redis. It also handles **catch-up logic** (if the scheduled time has already passed when the scheduler starts) and **monitors** the Redis schedule state for real-time changes.

### 1.2 Lifecycle

```
[Scheduler Start]
       │
       ▼
┌──────────────────┐
│ Initialize       │──── Reads cron from DB → stores in Redis
│ Schedule from DB │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Catch-up Check   │──── If today's scheduled time passed → enqueue fetch immediately
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Monitor Changes  │──── Background task: polls Redis every 5s for version changes
│ (async task)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Main Loop        │──── Every 30s: run pending aioschedule jobs
│ (while True)     │
└──────────────────┘
```

### 1.3 Key Functions

#### `run_scheduler()`
The main entry point called via `python -m app.cli scheduler`.

```python
async def run_scheduler():
    # 1. Read cron schedule from DB, store in Redis
    await initialize_schedule_from_db()

    # 2. Check if today's fetch time has already passed
    await catch_up_if_needed()

    # 3. Start background monitor for schedule changes
    monitor_task = asyncio.create_task(monitor_schedule_changes())

    # 4. Run the scheduling loop
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(30)  # Check every 30 seconds
```

#### `initialize_schedule_from_db()`
Reads the `cron_schedule` field from the `Setting` model in the database and stores it in Redis using the `ScheduleManager`. Default: `"0 9 * * *"` (daily at 09:00).

#### Catch-Up Logic
On startup, the scheduler calculates:
- Today's cron weekday (converting from Python's 0=Monday to cron's 0=Sunday format)
- The scheduled time in minutes (e.g., 09:00 → 540 minutes)
- The current time in minutes

If today is a scheduled day AND the current time has passed the scheduled time, it immediately enqueues a `fetch_and_process_stories` job. This ensures that if the scheduler restarts after the scheduled time, no stories are missed.

#### `schedule_worker(cron_schedule)`
Called either:
- With a new cron schedule (from API settings update)
- Without arguments (applies existing Redis schedule locally)

Uses `ScheduleManager.apply_schedule_from_redis()` to update local `aioschedule.jobs`.

### 1.4 Cron Parsing Utilities

#### `parse_cron_to_time(cron_schedule: str) -> str`
Extracts minute and hour from a 5-field cron expression and returns `"HH:MM"` format.

| Cron | Output |
|------|--------|
| `"0 9 * * 1-5"` | `"09:00"` |
| `"30 14 * * 1"` | `"14:30"` |
| `"* * * * *"` | `"09:00"` (default fallback) |

#### `parse_cron_to_days(cron_schedule: str) -> list`
Extracts the weekday field and returns a list of cron weekdays (0=Sunday..6=Saturday).

| Cron Weekday | Output | Meaning |
|-------------|--------|---------|
| `"1-5"` | `[1,2,3,4,5]` | Weekdays |
| `"1,3,5"` | `[1,3,5]` | Mon, Wed, Fri |
| `"*"` | `[]` | No scheduling (every day) |
| `"1"` | `[1]` | Monday only |

#### `format_days_to_cron(days: list, hour: int, minute: int) -> str`
Reverse operation: converts day list + time back to cron format.

---

## 2. ScheduleManager (`app/tasks/schedule_manager.py`)

### 2.1 Purpose

The `ScheduleManager` is the **shared state coordinator** between the server and scheduler processes. It uses Redis to store and synchronize schedule configurations, ensuring that both processes always use the same cron expression.

### 2.2 Redis Key Schema

| Redis Key | Type | Purpose |
|-----------|------|---------|
| `hn_reader:schedule:config` | String (JSON) | Current schedule configuration |
| `hn_reader:schedule:version` | String (integer) | Version counter for cache invalidation |
| `hn_reader:schedule:lock` | String ("1" or nil) | Distributed lock for atomic updates |

### 2.3 Schedule Config JSON Structure

```json
{
  "cron_schedule": "0 9 * * 1,2,3,4,5",
  "updated_at": 1734567890.123
}
```

### 2.4 Distributed Lock Mechanism

To prevent race conditions when both the server API and scheduler try to update the schedule simultaneously, the `ScheduleManager` implements a **Redis-based distributed lock**:

1. **Lock Acquisition**: Uses `SET key "1" NX EX 10` — atomically creates the key only if it doesn't exist, with a 10-second TTL
2. **Lock Release**: Deletes the key after the operation
3. **Timeout Safety**: If a process crashes while holding the lock, the TTL ensures automatic cleanup

```python
async def acquire_lock(self) -> bool:
    result = await self.redis_pool.set(
        SCHEDULE_LOCK_KEY, "1", nx=True, ex=LOCK_TIMEOUT  # 10 seconds
    )
    return result is True
```

### 2.5 Version-Based Cache Invalidation

Each time the schedule is updated, the version counter is incremented. Both processes compare their local version with Redis's version to detect changes:

```
Schedule Update Flow:
  1. Server API receives new cron schedule
  2. ScheduleManager acquires Redis lock
  3. Writes new config JSON to `hn_reader:schedule:config`
  4. Increments `hn_reader:schedule:version` (e.g., "3" → "4")
  5. Releases lock

Change Detection Flow (both processes):
  1. Read `hn_reader:schedule:version`
  2. Compare with local `_schedule_version`
  3. If different → call `apply_schedule_from_redis()`
  4. Update local version
```

### 2.6 Monitoring Loop

The scheduler runs a background task that polls Redis every 5 seconds:

```python
async def monitor_schedule_changes(self):
    while True:
        current_version = await self.get_schedule_version()

        if self._schedule_version is None:
            # First run — apply current schedule
            await self.apply_schedule_from_redis()
        elif current_version != self._schedule_version:
            # Schedule changed — reload
            await self.apply_schedule_from_redis()

        self._schedule_version = current_version
        await asyncio.sleep(5)
```

### 2.7 Schedule Application (`apply_schedule_from_redis()`)

When a schedule change is detected, the following happens:

1. **Clear existing** `aioschedule.jobs`
2. **Parse** the cron expression (time + days)
3. For each scheduled day, create an `aioschedule` job:
   ```python
   getattr(aioschedule.every(), day_name).at(scheduled_time).do(
       lambda: asyncio.create_task(create_job_closure())
   )
   ```
4. Each job calls `create_job_for_day()` which opens a Redis connection and enqueues `fetch_and_process_stories`

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
  ├── Call schedule_manager.update_schedule("0 14 * * 1,3,5")
  │     ├── Acquire Redis lock (NX EX 10)
  │     ├── Write config to hn_reader:schedule:config
  │     ├── Increment version: hn_reader:schedule:version → "5"
  │     ├── Release lock
  │     └── Apply schedule locally (update aioschedule.jobs)
  │
  └── Response: 200 OK
  │
  ▼
Scheduler process (monitoring every 5s):
  ├── Read hn_reader:schedule:version → "5"
  ├── Compare with local version "4" → different!
  ├── Call apply_schedule_from_redis()
  │     ├── Clear old aioschedule.jobs
  │     ├── Parse new cron: "0 14 * * 1,3,5"
  │     ├── Schedule: Monday at 14:00, Wednesday at 14:00, Friday at 14:00
  │     └── Update local version to "5"
  │
  └── Next fetch will happen at 14:00 on the next scheduled day
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
| **Scheduler** | Asyncio (single process) | `aioschedule` + Redis polling |
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