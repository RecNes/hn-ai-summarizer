# Installation Guide

## Prerequisites

### Core Requirements

| Dependency | Version | Required For |
|-----------|---------|-------------|
| Python | 3.11+ | Application runtime |
| Redis | 6.x+ | Task queue & schedule coordination |
| PostgreSQL | 13+ | Production database (optional in dev) |

### Optional

| Dependency | Purpose |
|-----------|---------|
| Docker & Docker Compose | Containerized deployment |
| An AI provider API key | Translation & summarization (OpenAI, Anthropic, etc.) |

---

## 1. Local Installation (No Docker)

### 1.1 Clone the Repository

```bash
git clone https://github.com/yourusername/hn-ai-summarizer.git
cd hn-ai-summarizer
```

### 1.2 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings. At minimum, you need:

```env
# Enable development mode (uses SQLite — no PostgreSQL needed)
DEVELOPMENT=True

# Set at least one AI provider API key
OPENAI_API_KEY=sk-your-key-here
```

### 1.3 Set Up Python Environment

**Using uv (recommended — 10-100x faster than pip):**

```bash
# Install uv if you don't have it
pip install uv

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate   # Linux/macOS
# OR
.venv\Scripts\activate      # Windows (PowerShell)

uv pip install -e .
```

**Using pip:**

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# OR
.venv\Scripts\activate      # Windows (PowerShell)

pip install -e .
```

### 1.4 Install Redis

The application requires Redis for background task processing. If you have Docker available, the startup scripts will automatically start a Redis container. Otherwise, install Redis manually:

**Windows (using Docker):**
```powershell
docker run -d --name hn-redis -p 6379:6379 redis:6-alpine
```

**Linux (apt):**
```bash
sudo apt install redis-server
sudo systemctl start redis
```

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

### 1.5 Run the Application

#### Option A: Quick Start Script (Recommended)

**Windows (PowerShell):**
```powershell
# Start all services (server + worker + scheduler + auto Redis)
.\start.ps1

# Or start only the web server
.\start.ps1 -Mode server

# Start all services except auto-Redis
.\start.ps1 -Mode all
```

**Linux/macOS/Git Bash:**
```bash
chmod +x start.sh

# Start all services (server + worker + scheduler)
./start.sh all

# Or start only the web server
./start.sh server
```

#### Option B: Manual Service Startup

Start each service in a separate terminal:

```bash
# Terminal 1: Database migration (first run only)
alembic upgrade head

# Terminal 2: Web server
hn-ai-summerizer server

# Terminal 3: Worker
hn-ai-summerizer worker

# Terminal 4: Scheduler
hn-ai-summerizer scheduler
```

> **Note:** The `hn-ai-summerizer` CLI command is installed automatically when you run `pip install -e .`

#### Option C: Start Everything with One Command

```bash
# Starts server, worker, and scheduler in separate processes
hn-ai-summerizer all
```

### 1.6 Access the Application

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 2. Docker Deployment

### 2.1 Production Deployment (with external PostgreSQL/Redis)

```bash
# Clone and configure
git clone https://github.com/yourusername/hn-ai-summarizer.git
cd hn-ai-summarizer
cp .env.example .env

# Edit .env with your database and Redis connection details
# Set DEVELOPMENT=False for production mode

# Start the application (expects external db & redis)
docker compose up
```

This starts three containers:
- `hn-reader-app` — FastAPI web server on port 8000
- `hn-reader-worker` — Arq background worker
- `hn-reader-scheduler` — Cron scheduler

All services use `network_mode: host` for direct connectivity to your external services.

### 2.2 All-in-One Deployment (with internal PostgreSQL & Redis)

```bash
docker compose --profile internal up
```

This starts five containers:
- `hn-reader-app` — Web server
- `hn-reader-worker` — Worker
- `hn-reader-scheduler` — Scheduler
- `db` — PostgreSQL 13
- `redis` — Redis 6 Alpine

The `--profile internal` flag activates the database and Redis services that are otherwise disabled in the default profile.

### 2.3 Development with Docker

```bash
docker compose -f docker-compose.dev.yml --profile internal up
```

The development compose file provides:
- Volume mounts for live code reloading
- Hot-reload enabled (`--reload` flag on uvicorn)
- Debug-friendly configuration (DB_ECHO=True for SQL logging)
- All five containers with internal PostgreSQL and Redis

> **Note:** The development compose file uses `profiles: ["internal"]` so all services must be explicitly activated with `--profile internal`.

### 2.4 Custom Docker Registry

If you're using a private Docker registry, set the environment variable:

```bash
export DOCKER_REGISTRY=your-registry.example.com
docker compose up
```

The images will be tagged as `${DOCKER_REGISTRY}/hn-reader:latest`.

---

## 3. Configuration Reference

### 3.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVELOPMENT` | `False` | If `True`, uses SQLite; if `False`, uses PostgreSQL |
| `DB_ECHO` | `False` | Log all SQL queries (debugging) |
| `DATABASE_USER` | `postgres` | PostgreSQL username |
| `DATABASE_PASSWORD` | `postgres` | PostgreSQL password |
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `hn_ai_summerizer_db` | PostgreSQL database name |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_USERNAME` | *(empty)* | Redis username (if using ACL) |
| `REDIS_PASSWORD` | *(empty)* | Redis password |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `DEEPSEEK_API_KEY` | *(empty)* | DeepSeek API key |
| `OPENROUTER_API_KEY` | *(empty)* | OpenRouter API key |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |

### 3.2 AI Provider Configuration

The application supports multiple AI providers simultaneously. API keys are read **exclusively from `.env`** and are never stored in the database or exposed to the frontend.

**Provider Priority:**
1. If no provider is configured in settings, the system auto-detects available API keys from `.env`
2. If multiple keys are available, the first detected provider is used (order: OpenAI, Anthropic, DeepSeek, OpenRouter, Gemini)
3. If no API keys are available, it falls back to local Ollama (http://localhost:11434)

---

## 4. Database Migration

Migrations are handled by Alembic and run automatically on startup in Docker. For manual control:

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 5. Verification

### Health Check

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

### Check Schedule Status

```bash
curl http://localhost:8000/api/settings/schedule-status
```

### Check Stories

```bash
curl http://localhost:8000/api/stories/
```

---

## 6. Troubleshooting

### Redis Connection Issues

```bash
# Test Redis connectivity
redis-cli ping
# Expected: PONG

# Check Redis keys
redis-cli keys 'hn_reader:*'
```

### Worker Not Processing Jobs

```bash
# Check worker logs
hn-ai-summerizer worker

# Test schedule synchronization
hn-ai-summerizer test-schedule
```

### Docker Permission Issues

If you encounter permission errors with the Docker volumes:

```bash
# Reset volume permissions
docker compose down -v
docker compose --profile internal up
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection from inside the container
docker exec -it hn-reader-app psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME