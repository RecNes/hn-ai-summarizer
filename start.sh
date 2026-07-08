#!/usr/bin/env bash
#
# HN-AI-Summerizer başlatma scripti (Bash sürümü - Linux/macOS/Git Bash/WSL)
# Docker'sız native çalıştırma için.
#
# Kullanım:
#   chmod +x start.sh
#   ./start.sh                    # web sunucusu
#   ./start.sh worker             # worker
#   ./start.sh scheduler          # scheduler
#   ./start.sh all                # tüm servisler
#   ./start.sh server --no-mig    # migration atla
#   ENV_FILE=.env.production ./start.sh server  # özel .env
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ──────────────────────────────────────────────
# Varsayılanlar
# ──────────────────────────────────────────────
MODE="${1:-server}"
ENV_FILE="${ENV_FILE:-.env}"
NO_MIGRATION=false
[[ "$*" == *--no-mig* ]] && NO_MIGRATION=true

# ──────────────────────────────────────────────
# Renkler
# ──────────────────────────────────────────────
INFO='\033[0;36m'
OK='\033[0;32m'
WARN='\033[1;33m'
ERR='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${INFO}[INFO]${NC} $*"; }
ok()    { echo -e "${OK}[OK]${NC} $*"; }
warn()  { echo -e "${WARN}[WARN]${NC} $*"; }
err()   { echo -e "${ERR}[ERROR]${NC} $*"; }

# ──────────────────────────────────────────────
# Python
# ──────────────────────────────────────────────
PYTHON=""
for candidate in "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/.venv/Scripts/python" "$PROJECT_ROOT/.venv/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python environment bulunamadı: $PROJECT_ROOT/.venv/"
    info "Kurulum için: python3 -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi

ok "Python: $PYTHON"

# ──────────────────────────────────────────────
# .env dosyasını oku
# ──────────────────────────────────────────────
ENV_FILE_PATH="$PROJECT_ROOT/$ENV_FILE"

if [ ! -f "$ENV_FILE_PATH" ]; then
    err ".env dosyası bulunamadı: $ENV_FILE_PATH"
    info "Örnek dosyayı kopyala: cp .env.example .env"
    exit 1
fi

info ".env dosyası okunuyor: $ENV_FILE_PATH"

set -a  # otomatik export
source "$ENV_FILE_PATH"
set +a

# DEVELOPMENT modu kontrolü
if [ "${DEVELOPMENT:-false}" = "true" ]; then
    ok "MOD: Geliştirme (DEVELOPMENT=true) → SQLite kullanılacak"
else
    info "MOD: Üretim (DEVELOPMENT=false) → PostgreSQL gerekli"
fi

# ──────────────────────────────────────────────
# Redis kontrolü
# ──────────────────────────────────────────────
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

if command -v timeout &>/dev/null; then
    if timeout 2 bash -c "echo > /dev/tcp/$REDIS_HOST/$REDIS_PORT" 2>/dev/null; then
        ok "Redis: $REDIS_HOST:$REDIS_PORT (bağlantı var)"
    else
        warn "Redis: $REDIS_HOST:$REDIS_PORT (bağlantı yok - scheduler/worker çalışmaz)"
        if [ "$MODE" != "server" ]; then
            warn "Worker ve scheduler için Redis gereklidir!"
        fi
    fi
else
    warn "Redis kontrolü atlandı (timeout komutu yok)"
fi

# ──────────────────────────────────────────────
# Migration
# ──────────────────────────────────────────────
if [ "$NO_MIGRATION" = false ]; then
    info "Alembic migration kontrol ediliyor..."
    if "$PYTHON" -m alembic upgrade head; then
        ok "Migration tamam"
    else
        err "Migration hatası!"
        exit 1
    fi
fi

# ──────────────────────────────────────────────
# Servisi başlat
# ──────────────────────────────────────────────
start_server() {
    info "Web sunucusu başlatılıyor (http://localhost:8000)..."
    exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

start_worker() {
    info "Arq worker başlatılıyor..."
    exec "$PYTHON" -m arq app.tasks.worker.WorkerSettings
}

start_scheduler() {
    info "Scheduler başlatılıyor..."
    exec "$PYTHON" -m app.cli scheduler
}

start_all() {
    info "Tüm servisler başlatılıyor (server + worker + scheduler)..."
    exec "$PYTHON" -m app.cli all
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

case "$MODE" in
    server)    start_server ;;
    worker)    start_worker ;;
    scheduler) start_scheduler ;;
    all)       start_all ;;
    *)
        err "Bilinmeyen mod: $MODE"
        echo "Kullanım: $0 [server|worker|scheduler|all]"
        exit 1
        ;;
esac