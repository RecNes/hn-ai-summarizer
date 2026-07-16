// ──────────────────────────────────────────────
// Service Worker for PWA
// ──────────────────────────────────────────────
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then((registration) => {
                console.log('Service Worker registered with scope:', registration.scope);
                // Yeni SW varsa hemen aktifleştir
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            newWorker.postMessage({ action: 'skipWaiting' });
                        }
                    });
                });
            })
            .catch((error) => {
                console.log('Service Worker registration failed:', error);
            });
        // SW değişince sayfayı yenile
        let refreshing = false;
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            if (!refreshing) {
                refreshing = true;
                window.location.reload();
            }
        });
    });
}

// ──────────────────────────────────────────────
// Theme: dark / light (localStorage 'theme')
// ──────────────────────────────────────────────

/** Geçerli temayı döndürür: 'dark' veya 'light' */
function getEffectiveTheme() {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') return 'dark';
    if (stored === 'light') return 'light';
    // Varsayılan: sistem tercihini kullan
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Temayı uygula: html.dark class'ı + body'ye data-theme attribute */
function applyTheme(theme) {
    const effective = theme || getEffectiveTheme();
    document.documentElement.classList.toggle('dark', effective === 'dark');
    document.documentElement.setAttribute('data-theme', effective);
    // Settings modalındaki dropdown'ı güncelle (varsa)
    const themeSelect = document.getElementById('theme-mode');
    if (themeSelect) {
        themeSelect.value = localStorage.getItem('theme') || 'system';
    }
}

/** Tema değiştir: direkt toggle — system kullanıcı dropdown'dan seçer */
function cycleTheme() {
    const stored = localStorage.getItem('theme');
    // Eğer stored 'system' veya yoksa → dark'a geç
    if (!stored || stored === 'system') {
        localStorage.setItem('theme', 'dark');
    } else if (stored === 'dark') {
        localStorage.setItem('theme', 'light');
    } else {
        localStorage.setItem('theme', 'dark');
    }
    applyTheme();
    updateThemeIcon();
}

/** Tema icon'unu güncelle: dark = ay, light = güneş */
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

/** Sistem teması değişikliğini dinle — sadece 'system' modunda iken */
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

// Apply settings to the page (tema class'larını ve body'nin default class'larını koru)
function applySettings(fontFamily, fontSize, contrast) {
    // Body class'larını düzenle — diğer class'ları (tailwind vb.) korumak için
    const classes = document.body.className.split(' ').filter(c => {
        return !c.startsWith('font-') && !c.startsWith('text-') && !c.startsWith('contrast-');
    });
    classes.push(`font-${fontFamily}`);  // font-atkinson veya font-merriweather
    classes.push(`text-${fontSize}`);

    // Dark modda contrast seçeneğini otomatik olarak dark yap (flash'ı önler)
    const isDark = getEffectiveTheme() === 'dark';
    const effectiveContrast = isDark && contrast !== 'dark' ? 'dark' : contrast;
    classes.push(`contrast-${effectiveContrast}`);

    document.body.className = classes.join(' ').trim();
}

// Save settings to localStorage
function saveSettings() {
    const fontFamily = document.getElementById('font-family').value;
    const fontSize = document.getElementById('font-size').value;
    const contrast = document.getElementById('contrast').value;

    localStorage.setItem('fontFamily', fontFamily);
    localStorage.setItem('fontSize', fontSize);
    localStorage.setItem('contrast', contrast);

    // Tema dropdown'ını da kaydet ve anlık uygula
    const themeSelect = document.getElementById('theme-mode');
    if (themeSelect) {
        const themeVal = themeSelect.value;
        localStorage.setItem('theme', themeVal);
        applyTheme();
        updateThemeIcon();
    }

    applySettings(fontFamily, fontSize, contrast);
    closeSettingsModal();
}

// Reset to default settings
function resetSettings() {
    localStorage.removeItem('fontFamily');
    localStorage.removeItem('fontSize');
    localStorage.removeItem('contrast');

    document.getElementById('font-family').value = 'atkinson';
    document.getElementById('font-size').value = 'medium';
    document.getElementById('contrast').value = 'light';

    // Temayı da sıfırla (system)
    localStorage.removeItem('theme');
    const themeSelect = document.getElementById('theme-mode');
    if (themeSelect) themeSelect.value = 'system';
    applyTheme();
    updateThemeIcon();

    applySettings('atkinson', 'medium', 'light');
    closeSettingsModal();
}

// Open settings modal
function openSettingsModal() {
    document.getElementById('font-family').value = localStorage.getItem('fontFamily') || 'atkinson';
    document.getElementById('font-size').value = localStorage.getItem('fontSize') || 'medium';
    document.getElementById('contrast').value = localStorage.getItem('contrast') || 'light';

    // Tema dropdown'ını güncelle
    const themeSelect = document.getElementById('theme-mode');
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

// ──────────────────────────────────────────────
// Polling — check every 30s if new stories arrived
// Track by max story ID for reliable detection.
// ──────────────────────────────────────────────
let lastKnownStoryId = 0;

/** Callback — sayfa-specific JS (index.js) bunu set etmeli */
window.updateLastKnownStoryId = function(id) {
    if (id > lastKnownStoryId) lastKnownStoryId = id;
};

function initPolling() {
    setInterval(async () => {
        try {
            // Sadece en yeni 1 story'yi çek — ID karşılaştırması için yeterli
            const res = await fetch('/api/stories/?skip=0&limit=1');
            const stories = await res.json();
            if (stories.length === 0) return;

            const latest = stories[0];
            if (latest.id > lastKnownStoryId && lastKnownStoryId > 0) {
                // Yeni story var — hepsini çekip başa ekle
                const newRes = await fetch('/api/stories/?skip=0&limit=5');
                const newStories = await newRes.json();
                const freshOnes = newStories.filter(s => s.id > lastKnownStoryId);
                // Büyük fark varsa sayfayı yenile (çok sayıda kaçırmış olabiliriz)
                if (freshOnes.length > 3) {
                    console.log('[Poll] Significant change, refreshing...');
                    location.reload();
                    return;
                }
                // Sırala (en eski yeni önce eklensin)
                freshOnes.sort((a, b) => a.id - b.id);
                if (typeof window.onNewStoryPoll === 'function') {
                    freshOnes.forEach(s => window.onNewStoryPoll(s));
                }
                // lastKnownStoryId'i güncelle
                const maxId = newStories.reduce((max, s) => s.id > max ? s.id : max, 0);
                if (maxId > lastKnownStoryId) lastKnownStoryId = maxId;
            } else if (latest.id > lastKnownStoryId) {
                // İlk çalıştırma — sadece ID'yi set et
                lastKnownStoryId = latest.id;
            }
        } catch (e) {
            // Ignore polling errors
        }
    }, 30000);
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
            initI18n(uiLang);
        }
    } catch (e) {
        console.warn('Could not load UI language preference:', e);
        if (typeof initI18n === 'function') {
            initI18n('en');
        }
    }
}

// ──────────────────────────────────────────────
// DOMContentLoaded (global)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // i18n başlat (önce preferences'dan UI dilini çek)
    initUILanguage();

    // Tema başlat
    applyTheme();
    updateThemeIcon();
    listenSystemTheme();

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', cycleTheme);
    }

    loadSettings();

    // Settings modal events
    const settingsButton = document.getElementById('settings-button');
    if (settingsButton) {
        settingsButton.addEventListener('click', openSettingsModal);
    }

    const saveSettingsButton = document.getElementById('save-settings');
    if (saveSettingsButton) {
        saveSettingsButton.addEventListener('click', saveSettings);
    }

    const resetSettingsButton = document.getElementById('reset-settings');
    if (resetSettingsButton) {
        resetSettingsButton.addEventListener('click', resetSettings);
    }

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
});