// ──────────────────────────────────────────────
// Service Worker for PWA
// ──────────────────────────────────────────────
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then((registration) => {
                console.log('Service Worker registered with scope:', registration.scope);
            })
            .catch((error) => {
                console.log('Service Worker registration failed:', error);
            });
    });
}

// ──────────────────────────────────────────────
// Theme: dark / light / system (localStorage 'theme')
// ──────────────────────────────────────────────

/** Geçerli temayı döndürür: 'dark' veya 'light' */
function getEffectiveTheme() {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') return 'dark';
    if (stored === 'light') return 'light';
    // 'system' veya hiç kayıt yoksa — sistem tercihini kullan
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Temayı uygula: html.dark class'ı + body contrast + dropdown senkronizasyonu */
function applyTheme(theme) {
    const effective = theme || getEffectiveTheme();
    document.documentElement.classList.toggle('dark', effective === 'dark');
    // Body'deki contrast-* class'ını güncelle (tema değişince body rengi de değişsin)
    document.body.className = document.body.className.replace(/contrast-\w+/g, 'contrast-' + effective);
    // Dropdown'u senkronize et (varsa)
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.value = localStorage.getItem('theme') || 'system';
    }
}

/** Tema geçişi: light ↔ dark (sadece 2 durum) */
function cycleTheme() {
    const stored = localStorage.getItem('theme');
    let next;
    if (stored === 'dark') next = 'light';
    else next = 'dark'; // light veya system → dark
    localStorage.setItem('theme', next);
    applyTheme();
    updateThemeIcon();
}

/** Tema icon'unu güncelle */
function updateThemeIcon() {
    const stored = localStorage.getItem('theme') || 'system';
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const effective = getEffectiveTheme();
    if (effective === 'dark') {
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>`;
        btn.title = 'Açık moda geç';
    } else {
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>`;
        btn.title = 'Koyu moda geç';
    }
}

/** Sistem teması değişikliğini dinle */
function listenSystemTheme() {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const stored = localStorage.getItem('theme');
        if (!stored || stored === 'system') {
            applyTheme();
            updateThemeIcon();
        }
    });
}

// ──────────────────────────────────────────────
// Accessibility settings (localStorage)
// ──────────────────────────────────────────────

// Load saved settings from localStorage
function loadSettings() {
    const fontFamily = localStorage.getItem('fontFamily') || 'atkinson';
    const fontSize = localStorage.getItem('fontSize') || 'medium';
    const contrast = localStorage.getItem('contrast') || 'light';

    applySettings(fontFamily, fontSize, contrast);
}

// Apply settings to the page
function applySettings(fontFamily, fontSize, contrast) {
    document.body.className = `font-${fontFamily} text-${fontSize} contrast-${contrast}`;
}

// Tema dropdown'ı değiştiğinde anında uygula
function handleThemeSelectChange() {
    const themeSelect = document.getElementById('theme-select');
    if (!themeSelect) return;
    localStorage.setItem('theme', themeSelect.value);
    applyTheme();
    updateThemeIcon();
}

// Display setting change: kaydet + anında uygula
function handleDisplaySettingChange(settingId, storageKey) {
    return function() {
        const value = document.getElementById(settingId).value;
        localStorage.setItem(storageKey, value);
        const fontFamily = localStorage.getItem('fontFamily') || 'atkinson';
        const fontSize = localStorage.getItem('fontSize') || 'medium';
        const contrast = localStorage.getItem('contrast') || 'light';
        applySettings(fontFamily, fontSize, contrast);
    };
}

/** Modal içindeki display select'lerine change listener'ları bağla, Esc ve X ile kapat */
function initDisplaySettings() {
    const fontFamilyEl = document.getElementById('font-family');
    const fontSizeEl = document.getElementById('font-size');
    const contrastEl = document.getElementById('contrast');
    if (fontFamilyEl) fontFamilyEl.addEventListener('change', handleDisplaySettingChange('font-family', 'fontFamily'));
    if (fontSizeEl) fontSizeEl.addEventListener('change', handleDisplaySettingChange('font-size', 'fontSize'));
    if (contrastEl) contrastEl.addEventListener('change', handleDisplaySettingChange('contrast', 'contrast'));

    const closeBtn = document.getElementById('close-settings-modal');
    if (closeBtn) closeBtn.addEventListener('click', closeSettingsModal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSettingsModal();
        }
    });
}

// Open settings modal
function openSettingsModal() {
    document.getElementById('font-family').value = localStorage.getItem('fontFamily') || 'atkinson';
    document.getElementById('font-size').value = localStorage.getItem('fontSize') || 'medium';
    document.getElementById('contrast').value = localStorage.getItem('contrast') || 'light';

    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.value = localStorage.getItem('theme') || 'system';
    }

    document.getElementById('settings-modal').classList.remove('hidden');
}

// Close settings modal
function closeSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

// ──────────────────────────────────────────────
// Toast notification system (global)
// ──────────────────────────────────────────────
const icons = {
    success: '✓',
    error:   '✗',
    warning: '⚠',
    info:    'ℹ'
};

/**
 * Show a toast notification.
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {string} message
 * @param {number} duration - ms, default 4000
 */
window.showToast = function(type, message, duration) {
    duration = duration || 4000;
    const container = document.getElementById('toast-container');
    if (!container) return;

    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.innerHTML = '<span class="toast-icon">' + (icons[type] || 'ℹ') + '</span> ' + message;
    container.appendChild(el);

    setTimeout(() => {
        el.style.animation = 'toast-out 0.3s ease-in forwards';
        setTimeout(() => el.remove(), 300);
    }, duration);
};

// ──────────────────────────────────────────────
// Worker progress functions (global)
// ──────────────────────────────────────────────
window.showWorkerProgress = function() {
    const progressBar = document.getElementById('worker-progress-bar');
    if (progressBar) {
        console.log('Showing progress bar');
        progressBar.classList.add('visible');
        progressBar.style.width = '0%';
        progressBar.offsetHeight;
    }
};

window.updateWorkerProgress = function(percent) {
    const progressBar = document.getElementById('worker-progress-bar');
    if (progressBar) {
        console.log('Updating progress to:', percent + '%');
        progressBar.style.width = percent + '%';
        progressBar.offsetHeight;
    }
};

window.hideWorkerProgress = function() {
    const progressBar = document.getElementById('worker-progress-bar');
    if (progressBar) {
        console.log('Hiding progress bar');
        progressBar.style.width = '100%';
        progressBar.offsetHeight;
        setTimeout(() => {
            progressBar.classList.remove('visible');
            progressBar.style.width = '0%';
        }, 500);
    }
};

window.showWorkerLabel = function(text) {
    const label = document.getElementById('worker-progress-label');
    const textEl = document.getElementById('worker-progress-text');
    if (label && textEl) {
        label.classList.remove('hidden');
        textEl.textContent = text;
    }
};

window.hideWorkerLabel = function() {
    const label = document.getElementById('worker-progress-label');
    if (label) {
        label.classList.add('hidden');
    }
};

// ──────────────────────────────────────────────
// Reusable SSE connection manager
// ──────────────────────────────────────────────
let activeSSEConnections = [];

/**
 * Create an SSE connection with automatic reconnection and cleanup.
 *
 * @param {string} url - SSE endpoint URL
 * @param {Object} handlers - Event handlers: { eventName: fn(data) }
 * @param {Object} [options]
 * @param {number} [options.reconnectDelay=5000] - ms before reconnecting on error
 * @returns {EventSource} the EventSource instance
 */
window.createSSEConnection = function(url, handlers, options) {
    options = options || {};
    const reconnectDelay = options.reconnectDelay || 5000;
    let es = null;
    let reconnectTimer = null;

    function connect() {
        // Close existing if any
        if (es) es.close();

        es = new EventSource(url);
        activeSSEConnections.push(es);

        // Register event handlers
        for (const [eventName, handler] of Object.entries(handlers)) {
            es.addEventListener(eventName, function(e) {
                try {
                    const data = JSON.parse(e.data);
                    handler(data);
                } catch (err) {
                    console.error(`[SSE/${eventName}] Parse error:`, err);
                }
            });
        }

        es.addEventListener('error', function() {
            console.warn(`[SSE] Connection lost for ${url}, reconnecting in ${reconnectDelay}ms...`);
            es.close();
            // Remove from active list
            const idx = activeSSEConnections.indexOf(es);
            if (idx !== -1) activeSSEConnections.splice(idx, 1);
            // Auto-reconnect
            if (reconnectTimer) clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(connect, reconnectDelay);
        });

        return es;
    }

    const instance = connect();
    // Store close method that stops reconnection
    instance.closeAndStop = function() {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (es) {
            es.close();
            const idx = activeSSEConnections.indexOf(es);
            if (idx !== -1) activeSSEConnections.splice(idx, 1);
        }
    };

    return instance;
};

/** Cleanup all active SSE connections (call on page unload) */
function cleanupSSEConnections() {
    activeSSEConnections.forEach(es => {
        if (es.closeAndStop) es.closeAndStop();
        else es.close();
    });
    activeSSEConnections = [];
}

// ──────────────────────────────────────────────
// Live polling via SSE — replaces old HTTP polling
// ──────────────────────────────────────────────
/** Callback — sayfa-specific JS (index.js) bunu set etmeli */
window.onNewStorySSE = null;

function initSSE() {
    const sse = window.createSSEConnection('/api/stories/poll-stream', {
        'story_update': function(story) {
            if (typeof window.onNewStorySSE === 'function') {
                window.onNewStorySSE(story);
            }
        },
        'keepalive': function() {
            // Connection is alive, nothing to do
        },
    }, { reconnectDelay: 5000 });

    // Store for cleanup
    window._pollSSE = sse;
}

// ──────────────────────────────────────────────
// i18n initialization
// ──────────────────────────────────────────────
async function initUILanguage() {
    try {
        const res = await fetch('/api/preferences/');
        const data = await res.json();
        const uiLang = data.ui_language || 'en';
        if (typeof initI18n === 'function') {
            await initI18n(uiLang);
        }
    } catch (e) {
        console.warn('Could not load UI language preference:', e);
        if (typeof initI18n === 'function') {
            await initI18n('en');
        }
    }
}

// ──────────────────────────────────────────────
// DOMContentLoaded (global)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async function() {
    // i18n başlat (önce preferences'dan UI dilini çek) — await ile bekle
    await initUILanguage();

    // Tema başlat
    applyTheme();
    updateThemeIcon();
    listenSystemTheme();

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', cycleTheme);
    }

    // Tema dropdown değişiklik anında uygula
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.addEventListener('change', handleThemeSelectChange);
    }

    loadSettings();

    // Settings modal events
    const settingsButton = document.getElementById('settings-button');
    if (settingsButton) {
        settingsButton.addEventListener('click', openSettingsModal);
    }

    // Anında kaydeden display ayarlarını başlat
    initDisplaySettings();

    // Close modal when clicking outside
    const settingsModal = document.getElementById('settings-modal');
    if (settingsModal) {
        settingsModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeSettingsModal();
            }
        });
    }

    // Refresh button
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            location.reload();
        });
    }

    // Log Panel event listeners
    const logPanelBtn = document.getElementById('log-panel-btn');
    if (logPanelBtn) {
        logPanelBtn.addEventListener('click', toggleLogPanel);
    }

    const logPanelCloseBtn = document.getElementById('log-panel-close-btn');
    if (logPanelCloseBtn) {
        logPanelCloseBtn.addEventListener('click', toggleLogPanel);
    }

    const logPanelOverlay = document.getElementById('log-panel-overlay');
    if (logPanelOverlay) {
        logPanelOverlay.addEventListener('click', toggleLogPanel);
    }

    // Cancel reprocess button
    const cancelReprocessBtn = document.getElementById('cancel-reprocess-home');
    if (cancelReprocessBtn) {
        cancelReprocessBtn.addEventListener('click', function() {
            if (typeof window.cancelReprocess === 'function') {
                window.cancelReprocess();
            }
        });
    }

    // Check if there's an ongoing reprocess job (survives page refresh)
    checkReprocessState();

    // Poll reprocess state every 15s so UI doesn't freeze if SSE drops
    window._reprocessStateInterval = setInterval(checkReprocessState, 15000);

    // AI health polling - check every 15s if AI model is reachable
    checkAIHealth();
    window._aiHealthInterval = setInterval(checkAIHealth, 15000);
});

/**
 * Check if a reprocess-untranslated job is currently running on the server.
 * If so, restore the UI state (button, progress bar, label).
 */
async function checkReprocessState() {
    try {
        const res = await fetch('/api/stories/reprocess-untranslated/status');
        if (!res.ok) return;
        const state = await res.json();

        // If cancelled flag is set but stream didn't reset yet — clear it now
        if (state.cancelled) {
            console.log('[Reprocess] Cancellation detected, resetting UI');
            _resetReprocessUI();
            return;
        }

        if (!state.running) return;

        // Restore button state
        const btn = document.getElementById('reprocess-home');
        const btnText = document.getElementById('reprocess-home-text');
        const spinner = document.getElementById('reprocess-home-spinner');
        const cancelBtn = document.getElementById('cancel-reprocess-home');
        if (btn) btn.disabled = true;
        if (btnText) btnText.textContent = 'İşleniyor...';
        if (spinner) spinner.classList.remove('hidden');
        if (cancelBtn) cancelBtn.classList.remove('hidden');

        // Restore progress bar
        if (window.showWorkerProgress) window.showWorkerProgress();
        if (window.updateWorkerProgress) window.updateWorkerProgress(state.percentage || 0);
        if (window.showWorkerLabel) {
            const current = state.current || 0;
            const total = state.total || 0;
            const pct = state.percentage || 0;
            window.showWorkerLabel(`${current} / ${total} - %${pct}`);
        }
    } catch (e) {
        // Ignore — server may not have the endpoint yet
        console.warn('[checkReprocessState] Failed:', e);
    }
}

/**
 * Reset all reprocess UI elements to idle state.
 */
function _resetReprocessUI() {
    const btn = document.getElementById('reprocess-home');
    const btnText = document.getElementById('reprocess-home-text');
    const spinner = document.getElementById('reprocess-home-spinner');
    const cancelBtn = document.getElementById('cancel-reprocess-home');
    const statusText = document.getElementById('worker-status-home');

    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = 'Çevrilmemişleri İşle';
    if (spinner) spinner.classList.add('hidden');
    if (cancelBtn) cancelBtn.classList.add('hidden');
    if (statusText) statusText.classList.add('hidden');

    if (window.hideWorkerProgress) window.hideWorkerProgress();
    if (window.hideWorkerLabel) window.hideWorkerLabel();
}

/**
 * Cancel the currently running reprocess job.
 * Sets cancelled=true in Redis. The SSE stream will detect it and exit.
 */
window.cancelReprocess = async function() {
    try {
        const res = await fetch('/api/stories/reprocess-untranslated/cancel', { method: 'POST' });
        if (!res.ok) {
            showToast('error', 'İptal isteği gönderilemedi.');
            return;
        }
        showToast('info', 'İşlem iptal ediliyor...');

        // Immediately reset frontend UI
        _resetReprocessUI();
    } catch (e) {
        console.error('[cancelReprocess] Error:', e);
        showToast('error', 'İptal sırasında hata oluştu.');
    }
};

// ──────────────────────────────────────────────
// Log Panel
// ──────────────────────────────────────────────

/** Log panel slide-up toggle (açılınca 10sn'de bir otomatik yenile) */
window.toggleLogPanel = function() {
    const panel = document.getElementById('log-panel');
    const overlay = document.getElementById('log-panel-overlay');
    const isOpen = panel && panel.style.display !== 'none' && !panel.classList.contains('translate-y-full');

    if (isOpen) {
        panel.classList.add('translate-y-full');
        panel.style.display = 'none';
        overlay.classList.add('hidden');
        // Auto-refresh interval'ı temizle
        if (window._logPanelInterval) {
            clearInterval(window._logPanelInterval);
            window._logPanelInterval = null;
        }
    } else {
        panel.style.display = 'block';
        overlay.classList.remove('hidden');
        // Force reflow for transition
        void panel.offsetHeight;
        panel.classList.remove('translate-y-full');
        loadActivityLogs();
        // Her 10sn'de bir otomatik yenile
        if (window._logPanelInterval) clearInterval(window._logPanelInterval);
        window._logPanelInterval = setInterval(loadActivityLogs, 10000);
    }
};

/** Render a single log entry as HTML */
function renderLogEntry(log) {
    const isError = log.status === 'error';
    const durationStr = log.duration_ms != null ? `${(log.duration_ms / 1000).toFixed(1)}s` : '-';
    const date = new Date(log.created_at).toLocaleString('tr-TR', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
    const titlePreview = log.story_title
        ? (log.story_title.length > 60 ? log.story_title.slice(0, 60) + '...' : log.story_title)
        : '';

    return `
        <div class="p-3 rounded-lg border ${isError ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700' : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'}">
            <div class="flex justify-between items-start">
                <div class="min-w-0 flex-1">
                    <span class="text-xs font-mono text-gray-400">#${log.story_id || '-'}</span>
                    <span class="ml-2 text-sm font-semibold ${isError ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}">${log.event_type}</span>
                </div>
                <span class="text-xs text-gray-400 flex-shrink-0 ml-2">${date}</span>
            </div>
            ${titlePreview ? `<div class="mt-1 text-xs text-gray-600 dark:text-gray-300 truncate" title="${titlePreview.replace(/"/g, '"')}">📄 ${titlePreview}</div>` : ''}
            <div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                ${log.provider} / ${log.model} · ${durationStr}
                ${isError ? `<span class="ml-2 text-red-500" title="${(log.error_message || '').replace(/"/g, '"')}">⚠ hata</span>` : ' ✓'}
            </div>
            ${isError && log.error_message ? `<div class="mt-1 text-xs text-red-500 break-words" title="${log.error_message.replace(/"/g, '"')}">${log.error_message}</div>` : ''}
        </div>
    `;
}

/** Fetch and render AI activity logs */
async function loadActivityLogs() {
    const content = document.getElementById('log-panel-content');
    if (!content) return;
    content.innerHTML = '<div class="text-center text-gray-500 py-8">Yükleniyor...</div>';

    try {
        const res = await fetch('/api/activity/?limit=50');
        if (!res.ok) {
            content.innerHTML = '<div class="text-center text-red-500 py-8">Loglar yüklenemedi.</div>';
            return;
        }
        const logs = await res.json();

        if (!logs || logs.length === 0) {
            content.innerHTML = '<div class="text-center text-gray-500 py-8">Henüz AI aktivite logu bulunmuyor.</div>';
            return;
        }

        let html = '<div class="space-y-3">';
        for (const log of logs) {
            html += renderLogEntry(log);
        }
        html += '</div>';
        content.innerHTML = html;
    } catch (e) {
        console.error('AI Activity log error:', e);
        content.innerHTML = '<div class="text-center text-red-500 py-8">Loglar yüklenirken hata oluştu.</div>';
    }
}

// ──────────────────────────────────────────────
// AI Health Monitoring - checks if AI model is reachable
// ──────────────────────────────────────────────

/** Check AI health status and show/hide warning banner */
async function checkAIHealth() {
    try {
        const res = await fetch('/api/health/ai-status');
        if (!res.ok) return;
        const data = await res.json();
        updateAIHealthBanner(data);
    } catch (e) {
        // Silently ignore - server may be restarting
    }
}

/** Show or hide the AI unreachable warning banner */
function updateAIHealthBanner(status) {
    const banner = document.getElementById('ai-health-banner');
    if (!banner) return;

    if (status && status.healthy === false) {
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

// ──────────────────────────────────────────────
// Esc ile log paneli kapat
// ──────────────────────────────────────────────
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const panel = document.getElementById('log-panel');
        if (panel && panel.style.display !== 'none' && !panel.classList.contains('translate-y-full')) {
            window.toggleLogPanel();
        }
    }
});
