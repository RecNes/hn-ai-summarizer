# HN-AI-Summerizer

AI-powered Hacker News reader that fetches top stories daily, summarizes them into Turkish, and presents them in a high-readability interface optimized for mobile and older eyes (40+).

## Features

- Daily fetching of top Hacker News stories
- AI-powered Turkish translation and summarization
- Accessible interface optimized for users 40+
- Smart filtering based on user preferences
- Self-hosted with Docker deployment

## Tech Stack

- **Backend:** Python 3.11+, FastAPI (Async), SQLAlchemy (Async), Pydantic
- **Database:** PostgreSQL (Production), SQLite (Dev/Test)
- **Task Queue:** Redis + Arq for background scraping and AI summarization
- **AI Integration:** Modular interface (support for OpenAI/Anthropic)
- **Frontend:** Server-side rendered HTML (Jinja2) + TailwindCSS + Vanilla JS
- **Infrastructure:** Docker & Docker Compose

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your settings
3. Run `docker-compose up` to start the application
4. Access the application at `http://localhost:8000`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.