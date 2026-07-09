<#
.SYNOPSIS
    HN-AI-Summerizer başlatma scripti (Docker'sız native çalıştırma)

.DESCRIPTION
    .env dosyasını okuyup backend servislerini native olarak başlatır.
    DEVELOPMENT=true ise SQLite kullanır (PostgreSQL gerekmez).
    
    Worker ve scheduler için Redis gereklidir. Redis yoksa:
    - docker yüklüyse: docker run redis ile otomatik başlatılır
    - yoksa: uyarı verilir

.PARAMETER Mode
    Hangi servisin başlatılacağı: server, worker, scheduler, all, full
    - server: sadece web (Redis gerekmez)
    - full: server + worker + scheduler + Redis (varsayılan)
    - all: server + worker + scheduler (Redis harici, cli all'ı çağırır)

.PARAMETER EnvFile
    .env dosyasının yolu. Varsayılan: proje kökündeki .env

.PARAMETER NoMigration
    Bu flag verilirse migration çalıştırılmaz.

.EXAMPLE
    # Tümünü başlat (önerilen)
    .\start.ps1

    # Sadece web sunucusu
    .\start.ps1 -Mode server

    # Worker + scheduler + server (Redis'in çalıştığını varsayar)
    .\start.ps1 -Mode all
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("server", "worker", "scheduler", "all", "full")]
    [string]$Mode = "full",

    [string]$EnvFile = ".env",

    [switch]$NoMigration
)

# ──────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ──────────────────────────────────────────────
function Write-Info {
    Write-Host "[INFO] $($args -join ' ')" -ForegroundColor Cyan
}
function Write-Success {
    Write-Host "[OK] $($args -join ' ')" -ForegroundColor Green
}
function Write-Warn {
    Write-Host "[WARN] $($args -join ' ')" -ForegroundColor Yellow
}
function Write-Error {
    Write-Host "[ERROR] $($args -join ' ')" -ForegroundColor Red
}

# ──────────────────────────────────────────────
# Proje kökü
# ──────────────────────────────────────────────
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Info "Proje: HN-AI-Summerizer"
Write-Info "Kök dizin: $ProjectRoot"

# ──────────────────────────────────────────────
# Python kontrolü
# ──────────────────────────────────────────────
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Error "Python environment bulunamadı: $PythonPath"
    Write-Info "Kurulum için: .venv\Scripts\uv pip install -e ."
    exit 1
}
Write-Success "Python: $PythonPath"

# ──────────────────────────────────────────────
# .env dosyasını oku ve environment'a yükle
# ──────────────────────────────────────────────
$EnvFilePath = Join-Path $ProjectRoot $EnvFile

if (-not (Test-Path $EnvFilePath)) {
    Write-Error ".env dosyası bulunamadı: $EnvFilePath"
    Write-Info "Örnek dosyayı kopyala: cp .env.example .env"
    exit 1
}

Write-Info ".env dosyası okunuyor: $EnvFilePath"

Get-Content $EnvFilePath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $split = $line.IndexOf("=")
        $key = $line.Substring(0, $split).Trim()
        $value = $line.Substring($split + 1).Trim().Trim('"', "'")
        if ($value) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$DevMode = [Environment]::GetEnvironmentVariable("DEVELOPMENT", "Process")
$RedisUrl = [Environment]::GetEnvironmentVariable("REDIS_URL", "Process")

if ($DevMode -and $DevMode -eq "true") {
    Write-Success "MOD: Geliştirme (DEVELOPMENT=true) → SQLite kullanılacak"
} else {
    Write-Info "MOD: Üretim (DEVELOPMENT=false) → PostgreSQL gerekli"
}

# ──────────────────────────────────────────────
# Redis kontrolü / otomatik başlatma
# ──────────────────────────────────────────────
$RedisHost = "localhost"
$RedisPort = 6379

# REDIS_URL'den host:port çözümle
if ($RedisUrl -match "redis://([^:]+):(\d+)/") {
    $RedisHost = $matches[1]
    $RedisPort = [int]$matches[2]
}

function Test-RedisConnection {
    param($TargetHost, $TargetPort)
    try {
        $socket = New-Object System.Net.Sockets.TcpClient
        $socket.ConnectAsync($TargetHost, $TargetPort).Wait(2000) | Out-Null
        if ($socket.Connected) { $socket.Close(); return $true }
        return $false
    } catch { return $false }
}

$redisRunning = Test-RedisConnection -TargetHost $RedisHost -TargetPort $RedisPort

if (-not $redisRunning -and ($Mode -in @("all", "full", "worker", "scheduler"))) {
    Write-Warn "Redis bağlantısı yok ($RedisHost`:$RedisPort)"
    Write-Info "Docker ile Redis başlatılıyor..."
    
    try {
        $dockerCheck = docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $existing = docker ps --filter "name=hn-redis" --format "{{.ID}}" 2>&1
            if (-not $existing) {
                docker run -d --name hn-redis -p 6379:6379 redis:6-alpine 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Redis container başlatıldı (hn-redis, port 6379)"
                    Start-Sleep 2
                    $redisRunning = $true
                } else {
                    Write-Warn "Redis container başlatılamadı. Worker çalışmaz."
                }
            } else {
                Write-Success "Redis container zaten çalışıyor (hn-redis)"
                $redisRunning = $true
            }
        } else {
            Write-Warn "Docker yok. Worker için Redis gerekli."
            Write-Info "Docker'ı başlat veya Redis'i manuel çalıştır."
        }
    } catch {
        Write-Warn "Docker kontrol edilemedi. Worker çalışmaz."
    }
}

if ($redisRunning) {
    Write-Success "Redis: $RedisHost`:$RedisPort (bağlantı var)"
} else {
    if ($Mode -in @("all", "full", "worker", "scheduler")) {
        Write-Warn "REDIS OLMADAN WORKER ÇALIŞMAZ. Sadece server modunu kullan."
        Write-Info "Veri çekmek için: docker run -d --name hn-redis -p 6379:6379 redis:6-alpine"
    }
}

# ──────────────────────────────────────────────
# Migration
# ──────────────────────────────────────────────
if (-not $NoMigration) {
    Write-Info "Alembic migration kontrol ediliyor..."
    $migrationResult = & "$PythonPath" -m alembic upgrade head 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Migration tamam"
    } else {
        Write-Error "Migration hatası:"
        Write-Host $migrationResult -ForegroundColor Red
        exit 1
    }
}

# ──────────────────────────────────────────────
# Servis başlatma fonksiyonları
# ──────────────────────────────────────────────
$processes = @()

function Start-Server {
    Write-Info "Web sunucusu başlatılıyor (http://localhost:8000)..."
    $proc = Start-Process -NoNewWindow -PassThru -FilePath $PythonPath -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    $processes += $proc
    Start-Sleep 3
    if ($proc.HasExited) {
        Write-Error "Web sunucusu hemen çıktı!"
    } else {
        Write-Success "Web sunucusu PID=$($proc.Id) - http://localhost:8000"
    }
    return $proc
}

function Start-Worker {
    Write-Info "Arq worker başlatılıyor..."
    $proc = Start-Process -NoNewWindow -PassThru -FilePath $PythonPath -ArgumentList "-m arq app.tasks.worker.WorkerSettings"
    $processes += $proc
    Start-Sleep 2
    if ($proc.HasExited) {
        Write-Error "Worker hemen çıktı!"
    } else {
        Write-Success "Worker PID=$($proc.Id)"
    }
    return $proc
}

function Start-Scheduler {
    Write-Info "Scheduler başlatılıyor..."
    $proc = Start-Process -NoNewWindow -PassThru -FilePath $PythonPath -ArgumentList "-m app.cli scheduler"
    $processes += $proc
    Start-Sleep 2
    if ($proc.HasExited) {
        Write-Error "Scheduler hemen çıktı!"
    } else {
        Write-Success "Scheduler PID=$($proc.Id)"
    }
    return $proc
}

function Wait-All {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host "Tüm servisler çalışıyor. Ctrl+C ile durdur." -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

    try {
        while ($true) {
            Start-Sleep 1
            # Check if any process died
            $dead = $processes | Where-Object { $_.HasExited }
            if ($dead) {
                foreach ($p in $dead) {
                    Write-Warn "Process PID=$($p.Id) çıktı (exit code: $($p.ExitCode))"
                }
                break
            }
        }
    } finally {
        Write-Info "Tüm servisler durduruluyor..."
        foreach ($p in $processes) {
            if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
        Write-Info "Durduruldu."
    }
}

# ──────────────────────────────────────────────
# Mod seçimine göre başlat
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

switch ($Mode) {
    "server" {
        Start-Server | Out-Null
        Wait-All
    }
    "worker" {
        Start-Worker | Out-Null
        Wait-All
    }
    "scheduler" {
        Start-Scheduler | Out-Null
        Wait-All
    }
    "all" {
        Write-Info "Tüm servisler başlatılıyor (server + worker + scheduler)..."
        Start-Server | Out-Null
        Start-Sleep 1
        Start-Worker | Out-Null
        Start-Sleep 1
        Start-Scheduler | Out-Null
        Wait-All
    }
    "full" {
        Write-Info "FULL MOD: Redis + server + worker + scheduler başlatılıyor..."
        if (-not $redisRunning) {
            Write-Error "Redis çalışmıyor. 'full' mod Redis gerektirir."
            Write-Info "Önce: .\start.ps1 -Mode server (web sunucusu için)"
            exit 1
        }
        Start-Server | Out-Null
        Start-Sleep 1
        Start-Worker | Out-Null
        Start-Sleep 1
        Start-Scheduler | Out-Null
        Wait-All
    }
}
</write_file>