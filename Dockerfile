FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


# Copy project files and install package
COPY pyproject.toml .
COPY app/ app/
RUN pip install --no-cache-dir .

# Copy remaining files
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app

# Expose port
EXPOSE 8000

# Create entrypoint script with proper permissions

RUN echo '#!/bin/bash' > /usr/local/bin/hn-ai-summerizer && \
    echo 'exec python -m app.cli "$@"' >> /usr/local/bin/hn-ai-summerizer && \
    chmod +x /usr/local/bin/hn-ai-summerizer


# Default to running server
#CMD ["python", "-m", "app.cli", "server"]

# Run the application
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]