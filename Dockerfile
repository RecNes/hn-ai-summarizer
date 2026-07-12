FROM python:3.11-slim

# Install uv (Rust-based, ~10-100x faster than pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \ 
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


# Copy entrypoint script first (before full copy for layer caching)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy project files and install package with uv (Rust-based, ~10-100x faster than pip)
COPY pyproject.toml .
COPY app/ app/
RUN uv pip install --system . && uv cache clean

# Copy remaining files
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app

# Create CLI shortcut
RUN echo '#!/bin/bash' > /usr/local/bin/hn-ai-summerizer && \
    echo 'exec python -m app.cli "$@"' >> /usr/local/bin/hn-ai-summerizer && \
    chmod +x /usr/local/bin/hn-ai-summerizer

# Expose port
EXPOSE 8000

# Run the application via entrypoint (migrations run automatically)
USER app
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
