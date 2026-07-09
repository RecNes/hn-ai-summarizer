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
    document.body.className = `${fontFamily} text-${fontSize} contrast-${contrast}`;
}

// Save settings to localStorage
function saveSettings() {
    const fontFamily = document.getElementById('font-family').value;
    const fontSize = document.getElementById('font-size').value;
    const contrast = document.getElementById('contrast').value;

    localStorage.setItem('fontFamily', fontFamily);
    localStorage.setItem('fontSize', fontSize);
    localStorage.setItem('contrast', contrast);

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

    applySettings('atkinson', 'medium', 'light');
    closeSettingsModal();
}

// Open settings modal
function openSettingsModal() {
    document.getElementById('font-family').value = localStorage.getItem('fontFamily') || 'atkinson';
    document.getElementById('font-size').value = localStorage.getItem('fontSize') || 'medium';
    document.getElementById('contrast').value = localStorage.getItem('contrast') || 'light';

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
// DOMContentLoaded (global)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
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