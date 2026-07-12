 // ──────────────────────────────────────────────
// State
// ──────────────────────────────────────────────
let availableProviders = [];
let currentModels = [];

// ──────────────────────────────────────────────
// Custom searchable dropdown helpers
// ──────────────────────────────────────────────
function setSelectedModel(value) {
    const native = document.getElementById('ai_model');
    const displayText = document.getElementById('model-display-text');
    native.innerHTML = value ? `<option value="${value}" selected>${value}</option>` : '';
    displayText.textContent = value || '-- Model Seçin --';
    displayText.className = value ? 'text-gray-900' : 'text-gray-400';
}

function buildModelList(filter) {
    const container = document.getElementById('model-options');
    const q = (filter || '').toLowerCase();
    container.innerHTML = '';
    let count = 0;
    currentModels.forEach(m => {
        if (m.toLowerCase().includes(q)) {
            const div = document.createElement('div');
            div.className = 'p-2 cursor-pointer hover:bg-blue-100 text-sm';
            div.textContent = m;
            div.addEventListener('click', function(e) {
                e.stopPropagation();
                setSelectedModel(m);
                closeModelPanel();
            });
            container.appendChild(div);
            count++;
        }
    });
    if (count === 0) {
        container.innerHTML = '<div class="p-2 text-gray-400 text-sm">Eşleşen model yok</div>';
    }
}

function openModelPanel() {
    const panel = document.getElementById('model-panel');
    const search = document.getElementById('model-search');
    panel.classList.remove('hidden');
    search.value = '';
    search.focus();
    buildModelList('');
}

function closeModelPanel() {
    document.getElementById('model-panel').classList.add('hidden');
}

function toggleModelPanel() {
    const panel = document.getElementById('model-panel');
    if (panel.classList.contains('hidden')) {
        openModelPanel();
    } else {
        closeModelPanel();
    }
}

// ──────────────────────────────────────────────
// Load settings from server
// ──────────────────────────────────────────────
async function loadSettings() {
    try {
        const res = await fetch('/api/settings/');
        const data = await res.json();

        availableProviders = data.available_providers || [];
        populateProviderDropdown(data.ai_provider);

        const minScoreField = document.getElementById('min_score');
        if (minScoreField) minScoreField.value = data.min_score || 100;
        const retentionField = document.getElementById('retention_days');
        if (retentionField) retentionField.value = data.retention_days || 30;

        const hourField = document.getElementById('scheduled_hour');
        const minuteField = document.getElementById('scheduled_minute');
        if (hourField) hourField.value = data.scheduled_hour || 9;
        if (minuteField) minuteField.value = data.scheduled_minute || 0;

        const dayCheckboxes = document.querySelectorAll('input[name="scheduled_days"]');
        if (dayCheckboxes.length > 0 && data.scheduled_days) {
            const days = data.scheduled_days.split(",").map(d => d.trim());
            dayCheckboxes.forEach(cb => { cb.checked = days.includes(cb.value); });
        }

        // Telegram settings
        const chatIdField = document.getElementById('telegram_chat_id');
        if (chatIdField) chatIdField.value = data.telegram_chat_id || '';

        const enabledCheckbox = document.getElementById('telegram_enabled');
        if (enabledCheckbox) enabledCheckbox.checked = data.telegram_enabled || false;

        if (data.ai_provider) {
            await loadModelsForProvider(data.ai_provider, data.ai_provider_config);
            if (data.ai_model) {
                setSelectedModel(data.ai_model);
            }
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
}

// ──────────────────────────────────────────────
// Provider dropdown
// ──────────────────────────────────────────────
function populateProviderDropdown(selected) {
    const sel = document.getElementById('ai_provider');
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Sağlayıcı Seçin --</option>';

    availableProviders.forEach(p => {
        if (!p.has_key && !p.config_required) return;
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name + (p.has_key ? '' : ' (yerel)');
        if (p.id === selected) opt.selected = true;
        sel.appendChild(opt);
    });

    updateProviderStatus();
}

function updateProviderStatus() {
    const sel = document.getElementById('ai_provider');
    const status = document.getElementById('provider-key-status');
    if (!sel || !status) return;
    const selectedId = sel.value;

    if (!selectedId) {
        status.textContent = '';
        const configSection = document.getElementById('provider-config-section');
        if (configSection) configSection.classList.add('hidden');
        return;
    }

    const provider = availableProviders.find(p => p.id === selectedId);
    if (provider) {
        status.textContent = provider.has_key
            ? '✓ API anahtarı .env dosyasında tanımlı'
            : 'ℹ Yerel sağlayıcı (API anahtarı gerekmez)';
        status.className = 'text-sm mt-1 ' + (provider.has_key ? 'text-green-600' : 'text-blue-600');

        const configSection = document.getElementById('provider-config-section');
        if (configSection) {
            if (provider.config_required) {
                configSection.classList.remove('hidden');
            } else {
                configSection.classList.add('hidden');
            }
        }
    }
}

// ──────────────────────────────────────────────
// Model loading
// ──────────────────────────────────────────────
async function loadModelsForProvider(providerId, configStr) {
    const display = document.getElementById('model-display');
    const searchInput = document.getElementById('model-search');
    const refreshBtn = document.getElementById('refresh-models');
    const status = document.getElementById('model-status');
    if (!display || !status) return;

    display.disabled = true;
    if (searchInput) searchInput.disabled = true;
    if (refreshBtn) refreshBtn.disabled = true;
    document.getElementById('model-display-text').textContent = 'Modeller yükleniyor...';
    status.textContent = 'Modeller API\'den çekiliyor...';
    closeModelPanel();

    try {
        const params = new URLSearchParams({ provider: providerId });
        if (configStr) params.append('config', configStr);

        const res = await fetch(`/api/settings/available-models?${params}`);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to fetch models');
        }

        const data = await res.json();
        currentModels = data.models || [];

        buildModelList('');

        display.disabled = false;
        if (searchInput) searchInput.disabled = false;
        if (refreshBtn) refreshBtn.disabled = false;
        document.getElementById('model-display-text').textContent = '-- Model Seçin --';
        document.getElementById('model-display-text').className = 'text-gray-400';
        status.textContent = `${currentModels.length} model bulundu`;
        status.className = 'text-sm text-gray-500 mt-1';
    } catch (e) {
        console.error('Error loading models:', e);
        const container = document.getElementById('model-options');
        if (container) {
            container.innerHTML = '<div class="p-2 text-red-500 text-sm">Modeller yüklenemedi: ' + (e.message || '') + '</div>';
        }
        status.textContent = 'Hata: ' + (e.message || 'Bilinmeyen hata');
        status.className = 'text-sm text-red-500 mt-1';
    }
}

// ──────────────────────────────────────────────
// Populate language dropdowns
// ──────────────────────────────────────────────
let availableLanguages = [];

function populateLanguageDropdowns(selectId, selectedCode) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = '';
    
    availableLanguages.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang.code;
        opt.textContent = lang.native_name + ' (' + lang.english_name + ')';
        if (lang.code === selectedCode) opt.selected = true;
        sel.appendChild(opt);
    });
}

// ──────────────────────────────────────────────
// Load preferences from server
// ──────────────────────────────────────────────
async function loadPreferences() {
    try {
        const res = await fetch('/api/preferences/');
        const data = await res.json();
        
        availableLanguages = data.available_languages || [];
        
        populateLanguageDropdowns('ui_language', data.ui_language || 'en');
        populateLanguageDropdowns('translation_language', data.translation_language || 'en');
        
        document.getElementById('highlight_keywords').value = data.highlight_keywords || '';
        document.getElementById('blocklist_keywords').value = data.blocklist_keywords || '';
    } catch (e) {
        console.error('Error loading preferences:', e);
    }
}

// ──────────────────────────────────────────────
// Save settings (toast + loader)
// ──────────────────────────────────────────────
async function saveSettings(event) {
    event.preventDefault();

    const btn = document.getElementById('save-btn');
    const btnText = document.getElementById('save-btn-text');
    const btnSpinner = document.getElementById('save-btn-spinner');
    if (!btn) return;

    btn.disabled = true;
    btnText.textContent = 'Saving...';
    btnSpinner.classList.remove('hidden');

    const nativeSelect = document.getElementById('ai_model');
    const settingsData = {
        ai_provider: document.getElementById('ai_provider').value || null,
        ai_model: nativeSelect ? nativeSelect.value || null : null,
        ai_provider_config: document.getElementById('ai_provider_config').value || null,
        min_score: parseInt(document.getElementById('min_score').value) || 100,
        retention_days: parseInt(document.getElementById('retention_days').value) || 30,
        scheduled_hour: parseInt(document.getElementById('scheduled_hour').value) || 9,
        scheduled_minute: parseInt(document.getElementById('scheduled_minute').value) || 0,
        scheduled_days: Array.from(document.querySelectorAll('input[name="scheduled_days"]:checked'))
            .map(cb => cb.value)
            .join(','),
        telegram_chat_id: document.getElementById('telegram_chat_id').value || null,
        telegram_enabled: document.getElementById('telegram_enabled').checked
    };

    const prefsData = {
        highlight_keywords: document.getElementById('highlight_keywords').value,
        blocklist_keywords: document.getElementById('blocklist_keywords').value,
        ui_language: document.getElementById('ui_language').value,
        translation_language: document.getElementById('translation_language').value
    };

    try {
        const settingsRes = await fetch('/api/settings/', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settingsData)
        });

        if (!settingsRes.ok) {
            const errData = await settingsRes.json();
            if (errData.warning) showToast('warning', errData.warning);
            else if (errData.detail) { showToast('error', errData.detail); return; }
        }

        await fetch('/api/preferences/', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prefsData)
        });

        // Update UI language immediately without page reload
        const newUiLang = document.getElementById('ui_language').value;
        if (typeof changeUILanguage === 'function') {
            changeUILanguage(newUiLang);
        }

        showToast('success', 'Settings saved successfully!');
    } catch (e) {
        console.error('Error saving settings:', e);
        showToast('error', 'An error occurred while saving settings.');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Save Settings';
        btnSpinner.classList.add('hidden');
    }
}

// ──────────────────────────────────────────────
// Worker trigger functions (toast + loader)
// ──────────────────────────────────────────────
async function triggerWorker() {
    const button = document.getElementById('trigger-worker');
    const btnText = document.getElementById('trigger-worker-text');
    const spinner = document.getElementById('trigger-worker-spinner');
    const statusText = document.getElementById('worker-status');
    if (!button) return;

    button.disabled = true;
    btnText.textContent = 'İşlem Başlatılıyor...';
    spinner.classList.remove('hidden');
    statusText.classList.remove('hidden');

    try {
        const response = await fetch('/api/settings/trigger-worker', { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            showToast('success', 'Veri çekimi başlatıldı! ' + (result.message || ''));
        } else {
            const err = await response.json();
            showToast('error', err.detail || 'Worker başlatılamadı');
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'Veri çekimi başlatılırken bir hata oluştu.');
    } finally {
        button.disabled = false;
        btnText.textContent = 'Veri Çekimini Başlat';
        spinner.classList.add('hidden');
        statusText.classList.add('hidden');
    }
}

async function reprocessUntranslated() {
    const button = document.getElementById('reprocess-untranslated');
    const btnText = document.getElementById('reprocess-text');
    const spinner = document.getElementById('reprocess-spinner');
    const statusText = document.getElementById('worker-status');
    if (!button) return;

    button.disabled = true;
    btnText.textContent = 'İşleniyor...';
    spinner.classList.remove('hidden');
    statusText.classList.remove('hidden');

    try {
        const response = await fetch('/api/settings/reprocess-untranslated', { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            showToast('success', 'Yeniden işleme başlatıldı! ' + (result.message || ''));
        } else {
            const err = await response.json();
            showToast('error', err.detail || 'Yeniden işleme başlatılamadı');
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'Yeniden işleme başlatılırken bir hata oluştu.');
    } finally {
        button.disabled = false;
        btnText.textContent = 'Çevrilmemişleri Yeniden İşle';
        spinner.classList.add('hidden');
        statusText.classList.add('hidden');
    }
}

// ──────────────────────────────────────────────
// DOMContentLoaded (settings page)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    loadPreferences(); // Load language dropdowns

    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) settingsForm.addEventListener('submit', saveSettings);

    const triggerBtn = document.getElementById('trigger-worker');
    if (triggerBtn) triggerBtn.addEventListener('click', triggerWorker);

    const reprocessBtn = document.getElementById('reprocess-untranslated');
    if (reprocessBtn) reprocessBtn.addEventListener('click', reprocessUntranslated);

    // Custom dropdown events
    const displayBtn = document.getElementById('model-display');
    const searchInput = document.getElementById('model-search');
    const panel = document.getElementById('model-panel');

    if (displayBtn) {
        displayBtn.addEventListener('click', toggleModelPanel);
    }

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            buildModelList(this.value);
        });
    }

    document.addEventListener('click', function(e) {
        const dropdown = document.getElementById('model-dropdown');
        if (dropdown && !dropdown.contains(e.target)) {
            closeModelPanel();
        }
    });

    if (searchInput) {
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModelPanel();
        });
    }

    const providerSelect = document.getElementById('ai_provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', async function() {
            updateProviderStatus();
            const providerId = this.value;
            if (providerId) {
                const configField = document.getElementById('ai_provider_config');
                await loadModelsForProvider(providerId, configField ? configField.value || null : null);
            } else {
                const display = document.getElementById('model-display');
                if (display) display.disabled = true;
                const displayText = document.getElementById('model-display-text');
                if (displayText) {
                    displayText.textContent = '-- Önce sağlayıcı seçin --';
                    displayText.className = 'text-gray-400';
                }
                const search = document.getElementById('model-search');
                if (search) search.disabled = true;
                const refresh = document.getElementById('refresh-models');
                if (refresh) refresh.disabled = true;
                currentModels = [];
                closeModelPanel();
            }
        });
    }

    const refreshModelsBtn = document.getElementById('refresh-models');
    if (refreshModelsBtn) {
        refreshModelsBtn.addEventListener('click', async function() {
            const providerId = document.getElementById('ai_provider').value;
            if (providerId) {
                const configField = document.getElementById('ai_provider_config');
                await loadModelsForProvider(providerId, configField ? configField.value || null : null);
            }
        });
    }
});