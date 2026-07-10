# HN-AI-Summarizer

> AI-powered Hacker News reader — automatically fetches, summarizes, and translates top stories daily.

**HN-AI-Summarizer** is a self-hosted web application that scrapes top Hacker News stories, processes them through AI services for translation and summarization, and presents them in a clean, readable interface optimized for mobile users and accessibility.

---

## Features

- **Automated Daily Fetching** — Pulls top stories from Hacker News on a configurable schedule (cron-based)
- **AI-Powered Translation** — Translates story titles and content into your preferred language
- **Smart Summarization** — Generates concise 3-bullet-point summaries of article content
- **Comment Analysis** — Summarizes HN discussion threads to give you the gist without scrolling
- **Multi-Provider AI Support** — Works with OpenAI, Anthropic, DeepSeek, OpenRouter, Google Gemini, Ollama, LM Studio
- **Negative Feedback Filtering** — Mark irrelevant stories to prevent similar content from reappearing
- **Keyword Preferences** — Filter stories based on your interests
- **Responsive Design** — Built for readability on mobile, tablet, and desktop (40+ age-friendly)
- **Fully Self-Hosted** — Your data, your API keys, your infrastructure
- **Docker Support** — One-command deployment with Docker Compose

---

## Architecture Overview

```
┌──────────────┐      ┌─────────────┐     ┌──────────────────┐
│  HN Firebase │────▶│   Fetcher   │────▶│   AI Service     │
│    API       │      │  (services) │     │  (OpenAI/etc.)   │
└──────────────┘      └──────┬──────┘     └────────┬─────────┘
                             │                     │
                             ▼                     ▼
                     ┌──────────────────────────────────┐
                     │         PostgreSQL / SQLite      │
                     │   (Story, Setting, Preference)   │
                     └────────────┬─────────────────────┘
                                  │
                                  ▼
                     ┌───────────────────────────────────┐
                     │   FastAPI + Jinja2 + TailwindCSS  │
                     │      Web Server (port 8000)       │
                     └───────────────────────────────────┘
```

The application runs **three separate processes** that work together:

| Process | Role | Command |
|---------|------|---------|
| **Server** | FastAPI web server — serves REST API and UI | `hn-ai-summerizer server` |
| **Worker** | Arq background worker — processes stories with AI | `hn-ai-summerizer worker` |
| **Scheduler** | Cron-based scheduler — triggers daily fetches | `hn-ai-summerizer scheduler` |

All three share state through **Redis**, which acts as the message broker and schedule coordination layer.

---

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

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/RecNes/hn-ai-summarizer.git
cd hn-ai-summarizer

# Copy and configure environment
cp .env.example .env
# Edit .env and set at least one AI provider API key

# Start with internal PostgreSQL and Redis
docker compose --profile internal up
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Local Development (No Docker)

```powershell
# Windows (PowerShell)
cp .env.example .env
# Set DEVELOPMENT=True in .env
.\start.ps1
```

```bash
# Linux / macOS
cp .env.example .env
# Set DEVELOPMENT=True in .env
./start.sh
```

> **Note:** Local mode uses SQLite (no PostgreSQL needed). Redis is still required for the worker and scheduler — the startup script will auto-start a Redis container if Docker is available.

---

## 📸 Screenshots

| Home Page | Settings |
|-----------|----------|
| ![Home](docs/images/screenshot.png) | ![Settings](docs/images/settings.png) |

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

## Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Detailed setup instructions (local & Docker) |
| [Architecture](docs/ARCHITECTURE.md) | Scheduler, worker, and system architecture deep-dive |
| [Redis Scheduling](docs/redis_scheduling.md) | Redis-based schedule synchronization details |

---

## Configuration

See [`.env.example`](.env.example) for all available configuration options.

### Minimal Configuration

```env
# At least one AI provider API key:
OPENAI_API_KEY=sk-...

# For development (uses SQLite):
DEVELOPMENT=True

# For production (requires PostgreSQL):
DEVELOPMENT=False
DATABASE_HOST=your-db-host
DATABASE_PASSWORD=your-db-password
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

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Related

Built as an accessible, self-hosted alternative to commercial HN readers. Inspired by the need for:
- Privacy-first news consumption
- Language barrier reduction through AI translation
- Accessible interfaces for aging eyes
- Offline-capable, self-contained deployments