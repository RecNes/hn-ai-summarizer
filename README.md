<p align="center">
  <img src="app/static/images/logo.png" alt="HN AI Summarizer" width="120">
</p>

<h1 align="center">HN-AI-Summarizer</h1>

<p align="center">
  <em>Your morning coffee, AI-summarized Hacker News stories in your language — delivered daily.</em>
</p>

<br>

<p align="center">
  <strong>🧾 Like reading your daily newspaper — but smarter, translated, and tailored just for you.</strong>
</p>

<br>
<br>

> Imagine: Every morning before work, the best tech stories you missed overnight are already waiting for you — summarized by AI, translated into your native language, and filtered to only show what interests you. No scrolling, no noise, no language barriers. That's **HN-AI-Summarizer**.

<br>

## ✨ Features

### 🧠 Your Personal AI Reader
HN-AI-Summarizer automatically fetches the top Hacker News stories every day, summarizes them, and translates them into your preferred language. Every story above 100 upvotes gets processed automatically — just sit back and read.

### 🌍 No Language Barrier
Don't speak English? No problem. HN-AI-Summarizer uses 7 different AI providers (OpenAI, Anthropic Claude, DeepSeek, Google Gemini, and more) to translate story titles and content into your language automatically. Article content is condensed into 3-bullet-point summaries.

Every story includes direct links to the **original Hacker News discussion** and the **source article** — so you can always jump to the full context when a summary catches your eye.

### 🎯 Only What Interests You
Set your interest keywords — the system highlights stories that match. Into "blockchain", "machine learning", or "Rust"? Only see those. Mark stories as "not interested" and they won't appear again.

### 📱 Designed for Aging Eyes
Can't read tiny fonts anymore? HN-AI-Summarizer was built with older users in mind: large fonts, high contrast, clean interface. Whether on phone or tablet, it's the most readable HN reader out there.

### 🔄 Three Processes, One Purpose
While you sleep, the system works:
1. **Scheduler** runs at your configured time (e.g., 09:00)
2. **Worker** fetches stories, processes them with AI, saves to database
3. **Web server** serves the polished result in a clean interface

### 📬 Telegram Notifications
Get instant notifications on Telegram when new stories are ready. Your daily tech briefing delivered to your pocket.

---

## 🚀 Quick Start (1 Minute)

```bash
# Clone the repository
git clone https://github.com/RecNes/hn-ai-summarizer.git
cd hn-ai-summarizer

# Configure environment (just one API key needed)
cp .env.example .env
# Edit .env and add OPENAI_API_KEY (or any other AI provider key)

# Start everything with one command (PostgreSQL + Redis included)
docker compose --profile internal up
```

Open **[http://localhost:8000](http://localhost:8000)** — that's it.

For detailed setup options: [docs/INSTALLATION.md](docs/INSTALLATION.md)

> **Windows users:** No Docker? Run `.\start.ps1` directly. Uses SQLite, auto-starts Redis.

---

## 🖼️ Screenshots

| Home Page — Summarized Stories | Settings — AI Provider & Scheduling |
|-----------|----------|
| ![Home](docs/images/screenshot.png) | ![Settings](docs/images/settings.png) |

---

## 🤖 Supported AI Providers

| Provider | Type | Notable Model |
|-----------|-----|-----------------|
| **OpenAI** | ☁️ Cloud | GPT-4o, GPT-4o-mini |
| **Anthropic** | ☁️ Cloud | Claude Sonnet, Claude Haiku |
| **DeepSeek** | ☁️ Cloud | DeepSeek V3 |
| **OpenRouter** | ☁️ Cloud | Multi-model access |
| **Google Gemini** | ☁️ Cloud | Gemini Pro |
| **Ollama** | 🖥️ Local | Llama 3, Mistral |
| **LM Studio** | 🖥️ Local | Any GGUF model |

> API keys are stored exclusively in `.env` — never in the database, never exposed to the frontend.

---

## 🌐 Supported Languages

HN-AI-Summarizer can translate stories into **20+ languages**. The interface language and the translation language are configured independently — you can browse in English while reading stories in Turkish, or use a Turkish UI while reading stories in Japanese.

> **UI Language** controls the interface text (buttons, labels).  
> **Translation Language** controls what language stories are translated into.

| Language | Native Name | Code |
|----------|-------------|------|
| 🇬🇧 English | English | `en` |
| 🇹🇷 Turkish | Türkçe | `tr` |
| 🇩🇪 German | Deutsch | `de` |
| 🇫🇷 French | Français | `fr` |
| 🇪🇸 Spanish | Español | `es` |
| 🇮🇹 Italian | Italiano | `it` |
| 🇵🇹 Portuguese | Português | `pt` |
| 🇷🇺 Russian | Русский | `ru` |
| 🇺🇦 Ukrainian | Українська | `uk` |
| 🇵🇱 Polish | Polski | `pl` |
| 🇳🇱 Dutch | Nederlands | `nl` |
| 🇨🇿 Czech | Čeština | `cs` |
| 🇸🇦 Arabic | العربية | `ar` |
| 🇮🇷 Persian | فارسی | `fa` |
| 🇮🇳 Hindi | हिन्दी | `hi` |
| 🇧🇩 Bengali | বাংলা | `bn` |
| 🇨🇳 Chinese (Simplified) | 中文 | `zh-CN` |
| 🇹🇼 Chinese (Traditional) | 中文 | `zh-TW` |
| 🇯🇵 Japanese | 日本語 | `ja` |
| 🇰🇷 Korean | 한국어 | `ko` |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Step-by-step setup (Docker, local, Windows) |
| [Architecture](docs/ARCHITECTURE.md) | System design, scheduler, worker internals |
| [.env Reference](.env.example) | All configuration options |

---

## 🔧 Minimal Configuration

```env
# All you need: one AI API key
OPENAI_API_KEY=sk-...

# Development mode (uses SQLite, no PostgreSQL required):
DEVELOPMENT=True
```

See [`.env.example`](.env.example) for the full list of configuration options.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 💡 Why HN-AI-Summarizer?

- **Privacy-first:** All data stays on your server, under your control
- **Language barrier breaker:** AI translation makes HN accessible to non-English speakers
- **Eye-friendly:** Optimized for users 40+ with large fonts and high contrast
- **Self-contained:** Single Docker deployment, no external service dependencies
- **Customizable:** You decide which stories to see and when