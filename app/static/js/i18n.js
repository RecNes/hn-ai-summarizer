// ──────────────────────────────────────────────
// i18n initialization and UI language management
// ──────────────────────────────────────────────

let i18nInitialized = false;

/**
 * Initialize i18next with the given language.
 * Falls back to 'en' if the requested language is not available.
 * @param {string} lang - Language code (e.g. 'tr', 'en', 'de')
 * @param {function} callback - Called after initialization
 */
function initI18n(lang, callback) {
    if (typeof i18next === 'undefined') {
        console.warn('i18next not loaded, skipping i18n init');
        if (callback) callback();
        return;
    }

    const loadPath = `/static/locales/{{lng}}/common.json`;

    i18next.init({
        lng: lang || 'en',
        fallbackLng: 'en',
        debug: false,
        returnObjects: false,
    }, function(err) {
        if (err) {
            console.error('i18next init error:', err);
            if (callback) callback();
            return;
        }
        i18nInitialized = true;
        applyI18nToDOM();
        if (callback) callback();
    });

    // Load resources manually via fetch (simpler than backend plugins)
    _loadLocale(lang || 'en', loadPath);
}

/**
 * Load a locale file from the server.
 */
function _loadLocale(lang, path) {
    const url = path.replace('{{lng}}', lang);
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (i18next.addResourceBundle) {
                i18next.addResourceBundle(lang, 'translation', data, true, true);
                // Re-apply after loading
                if (i18nInitialized) {
                    applyI18nToDOM();
                }
            }
        })
        .catch(err => {
            console.warn(`Could not load locale for ${lang}:`, err);
        });

    // Also always load fallback (English)
    const fallbackUrl = path.replace('{{lng}}', 'en');
    if (fallbackUrl !== url) {
        fetch(fallbackUrl)
            .then(res => res.json())
            .then(data => {
                if (i18next.addResourceBundle) {
                    i18next.addResourceBundle('en', 'translation', data, true, true);
                }
            })
            .catch(() => {});
    }
}

/**
 * Change UI language without page reload.
 * @param {string} lang - Language code
 */
function changeUILanguage(lang) {
    if (!i18nInitialized || typeof i18next === 'undefined') {
        console.warn('i18n not initialized');
        return;
    }

    i18next.changeLanguage(lang, function(err) {
        if (err) {
            console.error('Error changing language:', err);
            return;
        }
        applyI18nToDOM();

        // Dispatch event for other scripts to react
        document.dispatchEvent(new CustomEvent('languageChanged', {
            detail: { language: lang }
        }));
    });
}

/**
 * Apply i18n translations to the DOM.
 * Finds all elements with data-i18n attribute and updates their content.
 */
function applyI18nToDOM() {
    if (!i18nInitialized || typeof i18next === 'undefined') return;

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translated = i18next.t(key);
        if (translated && translated !== key) {
            el.textContent = translated;
        }
    });

    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const translated = i18next.t(key);
        if (translated && translated !== key) {
            el.placeholder = translated;
        }
    });

    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        const translated = i18next.t(key);
        if (translated && translated !== key) {
            el.title = translated;
        }
    });

    // Update html lang attribute
    const currentLang = i18next.language || 'en';
    document.documentElement.lang = currentLang;
}

/**
 * Shortcut for i18next.t()
 */
function __(key, options) {
    if (typeof i18next !== 'undefined' && i18next.isInitialized) {
        return i18next.t(key, options);
    }
    return key; // fallback: return the key itself
}