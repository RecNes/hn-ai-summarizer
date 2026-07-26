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
    displayText.textContent = value || __('settings.ai.modelPlaceholder');
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
        container.innerHTML = '<div class="p-2 text-gray-400 text-sm">' + __('settings.ai.modelNotFound') + '</div>';
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
async function loadAISettings() {
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

        // Timezone warning
        const tzWarning = document.getElementById('timezone-warning');
        if (tzWarning) {
            if (data.timezone_configured) {
                tzWarning.classList.add('hidden');
            } else {
                tzWarning.classList.remove('hidden');
            }
        }

        // Telegram settings
        const chatIdField = document.getElementById('telegram_chat_id');
        if (chatIdField) chatIdField.value = data.telegram_chat_id || '';

        const enabledCheckbox = document.getElementById('telegram_enabled');
        if (enabledCheckbox) enabledCheckbox.checked = data.telegram_enabled || false;

        const savedModel = data.ai_model || null;
        const savedProvider = data.ai_provider || null;

        if (savedProvider) {
            showModelLoading(savedModel);
            loadModelsForProviderAsync(savedProvider, data.ai_provider_config, savedModel);
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
}

function showModelLoading(savedModel) {
    const display = document.getElementById('model-display');
    const searchInput = document.getElementById('model-search');
    const refreshBtn = document.getElementById('refresh-models');
    const status = document.getElementById('model-status');
    const displayText = document.getElementById('model-display-text');

    if (display) display.disabled = true;
    if (searchInput) searchInput.disabled = true;
    if (refreshBtn) refreshBtn.disabled = true;
    if (status) {
        status.textContent = __('settings.ai.modelLoading');
        status.className = 'text-sm text-gray-500 mt-1';
    }
    if (displayText) {
        displayText.textContent = savedModel || __('settings.ai.modelLoading');
        displayText.className = savedModel ? 'text-gray-900' : 'text-gray-400';
    }
    closeModelPanel();
}

async function loadModelsForProviderAsync(providerId, configStr, savedModel) {
    try {
        const params = new URLSearchParams({ provider: providerId });
        if (configStr) params.append('config', configStr);

        const res = await fetch(`/api/settings/available-models?${params}`);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || __('settings.ai.modelError'));
        }

        const data = await res.json();
        currentModels = data.models || [];

        buildModelList('');

        if (savedModel && currentModels.includes(savedModel)) {
            setSelectedModel(savedModel);
        } else if (currentModels.length > 0) {
            const displayText = document.getElementById('model-display-text');
            if (displayText) {
                displayText.textContent = __('settings.ai.modelPlaceholder');
                displayText.className = 'text-gray-900';
            }
        }

        const display = document.getElementById('model-display');
        const searchInput = document.getElementById('model-search');
        const refreshBtn = document.getElementById('refresh-models');
        const status = document.getElementById('model-status');

        if (display) display.disabled = false;
        if (searchInput) searchInput.disabled = false;
        if (refreshBtn) refreshBtn.disabled = false;
        if (status) {
            status.textContent = __('settings.ai.modelCount', { count: currentModels.length });
            status.className = 'text-sm text-gray-500 mt-1';
        }
    } catch (e) {
        console.error('Error loading models:', e);
        const container = document.getElementById('model-options');
        if (container) {
            container.innerHTML = '<div class="p-2 text-red-500 text-sm">' + __('settings.ai.modelError') + ': ' + (e.message || '') + '</div>';
        }
        const status = document.getElementById('model-status');
        if (status) {
            status.textContent = __('common.error') + ': ' + (e.message || __('worker.reprocessUnknownError'));
            status.className = 'text-sm text-red-500 mt-1';
        }
    }
}

// ──────────────────────────────────────────────
// Provider dropdown
// ──────────────────────────────────────────────
function populateProviderDropdown(selected) {
    const sel = document.getElementById('ai_provider');
    if (!sel) return;
    sel.innerHTML = '<option value="">' + __('settings.ai.providerPlaceholder') + '</option>';

    availableProviders.forEach(p => {
        if (!p.has_key && !p.config_required) return;
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name + (p.has_key ? '' : ' (' + __('settings.ai.keyLocal').replace('ℹ ', '') + ')');
        if (p.id === selected) opt.selected = true;
        sel.appendChild(opt);
    });

    updateProviderStatus();
}

function updateProviderStatus() {
    const sel = document.getElementById('ai_provider');
    if (!sel) return;
    const selectedId = sel.value;

    const configSection = document.getElementById('provider-config-section');
    if (!configSection) return;

    if (!selectedId) {
        configSection.classList.add('hidden');
        return;
    }

    const provider = availableProviders.find(p => p.id === selectedId);
    if (provider) {
        if (provider.config_required) {
            configSection.classList.remove('hidden');
        } else {
            configSection.classList.add('hidden');
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
    document.getElementById('model-display-text').textContent = __('settings.ai.modelLoading');
    status.textContent = __('settings.ai.modelRefresh');
    closeModelPanel();

    try {
        const params = new URLSearchParams({ provider: providerId });
        if (configStr) params.append('config', configStr);

        const res = await fetch(`/api/settings/available-models?${params}`);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || __('settings.ai.modelError'));
        }

        const data = await res.json();
        currentModels = data.models || [];

        buildModelList('');

        display.disabled = false;
        if (searchInput) searchInput.disabled = false;
        if (refreshBtn) refreshBtn.disabled = false;
        document.getElementById('model-display-text').textContent = __('settings.ai.modelPlaceholder');
        document.getElementById('model-display-text').className = 'text-gray-900';
        status.textContent = __('settings.ai.modelCount', { count: currentModels.length });
        status.className = 'text-sm text-gray-500 mt-1';
    } catch (e) {
        console.error('Error loading models:', e);
        const container = document.getElementById('model-options');
        if (container) {
            container.innerHTML = '<div class="p-2 text-red-500 text-sm">' + __('settings.ai.modelError') + ': ' + (e.message || '') + '</div>';
        }
        status.textContent = __('common.error') + ': ' + (e.message || __('worker.reprocessUnknownError'));
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
    btnText.textContent = __('settings.saving');
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

        const newUiLang = document.getElementById('ui_language').value;
        if (newUiLang && typeof changeUILanguage === 'function') {
            await changeUILanguage(newUiLang);
        }

        showToast('success', __('settings.saveSuccess'));
    } catch (e) {
        console.error('Error saving settings:', e);
        showToast('error', __('settings.saveError'));
    } finally {
        btn.disabled = false;
        btnText.textContent = __('settings.save');
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
    btnText.textContent = __('worker.starting');
    spinner.classList.remove('hidden');
    statusText.classList.remove('hidden');

    try {
        const response = await fetch('/api/settings/trigger-worker', { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            showToast('success', __('worker.started') + ' ' + (result.message || ''));
        } else {
            const err = await response.json();
            showToast('error', err.detail || __('worker.error'));
        }
    } catch (e) {
        console.error(e);
        showToast('error', __('home.fetchError'));
    } finally {
        button.disabled = false;
        btnText.textContent = __('settings.data.fetchButton');
        spinner.classList.add('hidden');
        statusText.classList.add('hidden');
    }
}

async function checkAndCleanStuckReprocess() {
    const statusText = document.getElementById('worker-status');
    try {
        const res = await fetch('/api/stories/reprocess-untranslated/status');
        const state = await res.json();
        if (state.running) {
            await fetch('/api/stories/reprocess-untranslated/cancel', { method: 'POST' });
            if (statusText) {
                statusText.classList.remove('hidden');
                statusText.innerHTML = `<div class="text-yellow-600 text-sm">⚠️ ${__('worker.stuckCleaned')}</div>`;
                setTimeout(() => {
                    statusText.classList.add('hidden');
                }, 5000);
            }
        }
    } catch (e) {
        // Silent
    }
}

function reprocessUntranslated() {
    const button = document.getElementById('reprocess-untranslated');
    const btnText = document.getElementById('reprocess-text');
    const spinner = document.getElementById('reprocess-spinner');
    const statusText = document.getElementById('worker-status');
    if (!button) return;

    button.disabled = true;
    btnText.textContent = __('home.processing');
    spinner.classList.remove('hidden');

    statusText.classList.remove('hidden');
    statusText.innerHTML = `<span class="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2"></span> ${__('worker.reprocessStarted')}`;

    const abortController = new AbortController();

    function cancelReprocess() {
        abortController.abort();
        fetch('/api/stories/reprocess-untranslated/cancel', { method: 'POST' }).catch(() => {});
    }

    async function connectSSE() {
        try {
            const statusRes = await fetch('/api/stories/reprocess-untranslated/status');
            const statusData = await statusRes.json();
            if (statusData.running) {
                await fetch('/api/stories/reprocess-untranslated/cancel', { method: 'POST' });
            }

            const response = await fetch('/api/stories/reprocess-untranslated/stream', {
                signal: abortController.signal
            });

            if (!response.ok) {
                if (response.status === 409) {
                    const errData = await response.json();
                    statusText.innerHTML = `⚠️ <b>${__('worker.reprocessAlreadyRunning')}:</b> ${errData.detail || ''} <button onclick="checkAndCleanStuckReprocess().then(() => location.reload())" class="text-blue-500 underline ml-2">${__('home.reprocess')}</button>`;
                } else {
                    const errData = await response.json();
                    statusText.innerHTML = `❌ ${__('common.error')}: ${errData.detail || __('worker.reprocessUnknownError')}`;
                }
                showToast('error', __('worker.reprocessError'));
                resetButton();
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                let currentEvent = '';
                let currentData = '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        currentData = line.slice(6).trim();
                    } else if (line === '' && currentData) {
                        try {
                            const parsed = JSON.parse(currentData);
                            handleSSEEvent(currentEvent, parsed);
                        } catch (e) {
                            console.error('SSE parse error:', e);
                        }
                        currentEvent = '';
                        currentData = '';
                    }
                }
            }
        } catch (e) {
            if (e.name === 'AbortError') {
                statusText.innerHTML = '⏹️ ' + __('worker.reprocessAborted');
            } else {
                console.error('SSE connection error:', e);
                statusText.innerHTML = '⚠️ ' + __('worker.reprocessConnectionError');
            }
        } finally {
            resetButton();
        }
    }

    function handleSSEEvent(event, data) {
        switch (event) {
            case 'progress':
                const pct = data.percentage || 0;
                const current = data.current || 0;
                const total = data.total || 0;

                statusText.innerHTML = `
                    <div class="flex items-center gap-2 mb-1">
                        <span class="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></span>
                        <span class="font-medium">${__('worker.processingLabel', { current: current, total: total })}</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5 mb-1">
                        <div class="bg-blue-500 h-2.5 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
                    </div>
                    <div class="text-sm text-gray-500">${__('worker.completedPercent', { pct: pct })}</div>
                `;
                break;

            case 'story_update':
                if (data.title_tr) {
                    const titlePreview = data.title_tr.length > 50 ? data.title_tr.slice(0, 50) + '...' : data.title_tr;
                    statusText.innerHTML = statusText.innerHTML.replace(
                        /(<div class="flex.*?<\/div>)/,
                        `$1<div class="text-xs text-gray-400 mt-1">📄 ${titlePreview}</div>`
                    );
                }
                break;

            case 'complete':
                statusText.innerHTML = `
                    <div class="text-green-600 font-medium">✅ ${__('worker.reprocessComplete', { processed: data.processed })}</div>
                    <div class="text-sm text-gray-500">${__('worker.totalProgress', { total: data.total, processed: data.processed, errors: data.errors })}</div>
                `;
                showToast('success', __('worker.reprocessComplete', { processed: data.processed }));
                break;

            case 'cancelled':
                statusText.innerHTML = '⏹️ ' + __('worker.reprocessCancelled', { current: data.current, total: data.total });
                showToast('warning', __('worker.reprocessCancelled', { current: data.current, total: data.total }));
                break;

            case 'error':
                statusText.innerHTML = `❌ <b>${__('common.error')}:</b> ${data.detail || __('worker.reprocessUnknownError')}`;
                showToast('error', data.detail || __('worker.reprocessError'));
                break;

            case 'keepalive':
                break;

            default:
                console.log('Unknown SSE event:', event, data);
        }
    }

    function resetButton() {
        button.disabled = false;
        btnText.textContent = __('settings.data.reprocessButton');
        spinner.classList.add('hidden');
    }

    connectSSE();
}

// ──────────────────────────────────────────────
// DOMContentLoaded (settings page)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    loadAISettings();
});

document.addEventListener('languageChanged', function() {
    loadPreferences();

    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) settingsForm.addEventListener('submit', saveSettings);

    const triggerBtn = document.getElementById('trigger-worker');
    if (triggerBtn) triggerBtn.addEventListener('click', triggerWorker);

    const reprocessBtn = document.getElementById('reprocess-untranslated');
    if (reprocessBtn) reprocessBtn.addEventListener('click', reprocessUntranslated);

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
                    displayText.textContent = __('settings.ai.modelSelectFirst');
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

    const uiLangSelect = document.getElementById('ui_language');
    if (uiLangSelect) {
        uiLangSelect.addEventListener('change', async function() {
            const newLang = this.value;
            if (newLang && typeof changeUILanguage === 'function') {
                await changeUILanguage(newLang);
            }
        });
    }
});