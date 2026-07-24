// ──────────────────────────────────────────────
// Service Worker for PWA
// ──────────────────────────────────────────────
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then((registration) => {
                // Service Worker registered
            })
            .catch((error) => {
                // Service Worker registration failed
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
        progressBar.classList.add('visible');
        progressBar.style.width = '0%';
        progressBar.offsetHeight;
    }
};

window.updateWorkerProgress = function(percent) {
    const progressBar = document.getElementById('worker-progress-bar');
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.offsetHeight;
    }
};

window.hideWorkerProgress = function() {
    const progressBar = document.getElementById('worker-progress-bar');
    if (progressBar) {
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
                    // SSE parse error
                }
            });
        }

        es.addEventListener('error', function() {
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
        if (typeof initI18n === 'function') {
            await initI18n('en');
        }
    }
    // Tüm sayfaların i18n hazır olduğunda DOM'u güncellemesi için
    // merkezi event fırlat. applyI18nToDOM zaten initI18n içinde çağrıldı.
    document.dispatchEvent(new CustomEvent('languageChanged', {
        detail: { language: i18next ? i18next.language : 'en' }
    }));
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

    // AI health polling - check every 15s if AI model is reachable
    checkAIHealth();
    window._aiHealthInterval = setInterval(checkAIHealth, 15000);
});

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