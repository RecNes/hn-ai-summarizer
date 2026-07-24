// ──────────────────────────────────────────────
// Worker Logs Page - Live log viewer with SSE + infinite scroll
// ──────────────────────────────────────────────

const LOGS_CONTAINER = document.getElementById('worker-logs');
const LOGS_LOADING = document.getElementById('logs-loading');
const LOGS_END = document.getElementById('logs-end');
let sseConnection = null;
let skipCount = 0;
let isLoading = false;
let hasMoreLogs = true;
let autoScroll = true;

// ──────────────────────────────────────────────
// i18n helper (fallback to Turkish)
// ──────────────────────────────────────────────
function tt(key, fallback) {
    if (typeof i18next !== 'undefined' && i18next.isInitialized) {
        return i18next.t(key, { defaultValue: fallback });
    }
    return fallback;
}

// ──────────────────────────────────────────────
// Format a log entry into a human-readable HTML line
// ──────────────────────────────────────────────
function renderLogEntry(log) {
    const now = new Date();
    const logTime = log.created_at ? new Date(log.created_at) : now;
    const timeStr = logTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const isError = log.status === 'error';
    const isSuccess = log.status === 'success';
    const isProcessing = log.status === 'processing';

    let icon = '●';
    let colorClass = 'text-gray-600 dark:text-gray-400';
    let text = '';

    if (log.event_category === 'worker') {
        if (log.worker_event_type === 'worker_triggered') {
            // Worker triggered event
            const triggerSource = log.trigger_source || 'auto';
            const autoText = triggerSource === 'manual' 
                ? tt('logs.manualTrigger', 'manuel')
                : tt('logs.autoTrigger', 'otomatik');
            const actionText = log.story_title === 'fetch_new'
                ? tt('logs.fetchNew', 'yenileri çekmek için')
                : tt('logs.reprocessMissing', 'eksikleri çevirmek için');
            icon = '🚀';
            colorClass = 'text-blue-600 dark:text-blue-400';
            text = `${tt('logs.workerTriggered', 'Worker tetiklendi')} (${autoText}) — ${actionText}`;
        } else if (log.worker_event_type === 'story_new' || log.worker_event_type === 'story_reprocess') {
            // Story processing event
            const isNew = log.worker_event_type === 'story_new';
            const storyLabel = isNew 
                ? tt('logs.newArticle', 'Yeni makale')
                : tt('logs.reprocessing', 'Tekrar çevriliyor');
            const title = log.story_title || '?';
            const hnId = log.story_id || '?';
            
            if (isProcessing) {
                const phaseLabel = tt(`logs.phase${log.worker_phase?.charAt(0).toUpperCase() + log.worker_phase?.slice(1) || 'Title'}`, log.worker_phase || 'başlık');
                icon = '🔄';
                colorClass = 'text-yellow-600 dark:text-yellow-400';
                text = `${storyLabel}: (${title} ID:${hnId}) → ${tt('logs.processing', 'işleniyor')}: ${phaseLabel}`;
            } else if (isSuccess) {
                icon = '✅';
                colorClass = 'text-green-600 dark:text-green-400';
                text = `${storyLabel}: (${title} ID:${hnId}) → ${tt('logs.success', 'başarılı')}.`;
            } else if (isError) {
                icon = '❌';
                colorClass = 'text-red-600 dark:text-red-400';
                const errCode = log.error_code || tt('logs.errorWorker', 'Worker hatası');
                const errMsg = log.error_summary || log.error_message || '';
                text = `${storyLabel}: (${title} ID:${hnId}) → ${tt('logs.error', 'hata')}: (${errCode}: ${errMsg})`;
            }
        } else {
            // Fallback for unknown worker events
            icon = '📋';
            text = log.event_type || log.worker_event_type || 'unknown';
        }
    } else {
        // AI call logs - show as-is
        icon = '🤖';
        text = log.event_type || 'ai_call';
        if (log.story_title) text += ` (${log.story_title})`;
        if (isError) text += ` ❌ ${log.error_message || ''}`;
    }

    return `<div class="log-entry ${colorClass} text-xs leading-relaxed">
        <span class="text-gray-400 mr-1">${timeStr}</span>
        <span>${icon}</span>
        <span>${text}</span>
    </div>`;
}

// ──────────────────────────────────────────────
// Append a single log entry to the container
// ──────────────────────────────────────────────
function appendLog(log) {
    if (!LOGS_CONTAINER) return;
    const isNearBottom = LOGS_CONTAINER.scrollHeight - LOGS_CONTAINER.scrollTop - LOGS_CONTAINER.clientHeight < 100;
    LOGS_CONTAINER.insertAdjacentHTML('beforeend', renderLogEntry(log));
    if (autoScroll || isNearBottom) {
        LOGS_CONTAINER.scrollTop = LOGS_CONTAINER.scrollHeight;
    }
}

// ──────────────────────────────────────────────
// Prepend multiple log entries (older logs from DB)
// ──────────────────────────────────────────────
function prependLogs(logs) {
    if (!LOGS_CONTAINER) return;
    const prevScrollHeight = LOGS_CONTAINER.scrollHeight;
    logs.reverse().forEach(log => {
        LOGS_CONTAINER.insertAdjacentHTML('afterbegin', renderLogEntry(log));
    });
    // Maintain scroll position
    const newScrollHeight = LOGS_CONTAINER.scrollHeight;
    LOGS_CONTAINER.scrollTop = newScrollHeight - prevScrollHeight;
}

// ──────────────────────────────────────────────
// Load recent logs from Redis (initial load)
// ──────────────────────────────────────────────
async function loadRecentLogs() {
    try {
        const res = await fetch('/api/logs/recent');
        if (!res.ok) return;
        const logs = await res.json();
        if (logs.length === 0) {
            LOGS_CONTAINER.innerHTML = `<div class="text-center text-gray-400 py-8">${tt('logs.empty', 'Henüz log bulunmuyor.')}</div>`;
            return;
        }
        LOGS_CONTAINER.innerHTML = '';
        logs.reverse().forEach(log => appendLog(log));
        skipCount = logs.length;
    } catch (e) {
        LOGS_CONTAINER.innerHTML = `<div class="text-center text-red-500 py-8">${tt('logs.loadError', 'Loglar yüklenemedi.')}</div>`;
    }
}

// ──────────────────────────────────────────────
// Load older logs from DB (infinite scroll)
// ──────────────────────────────────────────────
async function loadOlderLogs() {
    if (isLoading || !hasMoreLogs) return;
    isLoading = true;
    LOGS_LOADING.classList.remove('hidden');
    try {
        const res = await fetch(`/api/logs/?skip=${skipCount}&limit=20`);
        if (!res.ok) {
            isLoading = false;
            LOGS_LOADING.classList.add('hidden');
            return;
        }
        const logs = await res.json();
        if (logs.length === 0) {
            hasMoreLogs = false;
            LOGS_END.classList.remove('hidden');
        } else {
            prependLogs(logs);
            skipCount += logs.length;
        }
    } catch (e) {
        // Silently fail
    } finally {
        isLoading = false;
        LOGS_LOADING.classList.add('hidden');
    }
}

// ──────────────────────────────────────────────
// SSE connection for real-time log streaming
// ──────────────────────────────────────────────
function connectSSE() {
    if (sseConnection) {
        sseConnection.closeAndStop();
    }
    sseConnection = window.createSSEConnection('/api/logs/stream', {
        'log_entry': function(data) {
            appendLog(data);
        },
        'connected': function() {
            // Connection established
        },
    }, { reconnectDelay: 3000 });
}

// ──────────────────────────────────────────────
// Infinite scroll handler (scroll to top loads older)
// ──────────────────────────────────────────────
function handleScroll() {
    if (!LOGS_CONTAINER) return;
    // Check if user is near bottom for auto-scroll
    const isNearBottom = LOGS_CONTAINER.scrollHeight - LOGS_CONTAINER.scrollTop - LOGS_CONTAINER.clientHeight < 100;
    autoScroll = isNearBottom;
    // Load older logs when scrolled to top
    if (LOGS_CONTAINER.scrollTop < 100) {
        loadOlderLogs();
    }
}

// ──────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async function() {
    // Load recent logs
    await loadRecentLogs();
    // Connect SSE for live updates
    connectSSE();
    // Infinite scroll
    if (LOGS_CONTAINER) {
        LOGS_CONTAINER.addEventListener('scroll', handleScroll);
    }
});