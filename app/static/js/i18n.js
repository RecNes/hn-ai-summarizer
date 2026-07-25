// ──────────────────────────────────────────────
// i18n initialization and UI language management
// ──────────────────────────────────────────────

let i18nInitialized = false;

/**
 * Initialize i18next with the given language.
 * Falls back to 'en' if the requested language is not available.
 *
 * NOW ASYNC: waits for the locale file to load before initializing i18next,
 * so that applyI18nToDOM() runs with actual translations, not placeholder keys.
 *
 * @param {string} lang - Language code (e.g. 'tr', 'en', 'de')
 * @param {function} callback - Called after initialization
 */
/**
 * Fetch a locale file and return { lang, data }.
 */
async function _fetchLocale(lang, path) {
    const url = path.replace('{{lng}}', lang);
    try {
        const res = await fetch(url);
        const data = await res.json();
        return { lang, data };
    } catch (err) {
        console.warn(`Could not load locale for ${lang}:`, err);
        return null;
    }
}

/**
 * Fetch the target locale + fallback (English) in parallel.
 * Returns a resources object suitable for i18next.init({ resources }).
 */
async function _buildResources(lang, path) {
    const results = await Promise.all([
        _fetchLocale(lang, path),
        lang !== 'en' ? _fetchLocale('en', path) : null,
    ]);

    const resources = {};
    for (const r of results) {
        if (r && r.data) {
            resources[r.lang] = { translation: r.data };
        }
    }
    return resources;
}

async function initI18n(lang, callback) {
    if (typeof i18next === 'undefined') {
        console.warn('i18next not loaded, skipping i18n init');
        if (callback) callback();
        return;
    }

    lang = lang || 'en';
    const loadPath = `/static/locales/{{lng}}/common.json`;

    // Fetch all needed locale files BEFORE init, pass as resources.
    // i18next.init() with resources immediately has the data,
    // no race condition with addResourceBundle.
    const resources = await _buildResources(lang, loadPath);

    await new Promise((resolve) => {
        i18next.init({
            lng: lang,
            fallbackLng: 'en',
            debug: false,
            returnObjects: false,
            resources: resources,
        }, function(err) {
            if (err) {
                console.error('i18next init error:', err);
                resolve();
                return;
            }
            i18nInitialized = true;
            applyI18nToDOM();
            resolve();
        });
    });

    if (callback) callback();
}

// Özel event adı — initUILanguage dışında hiçbir yer dispatch etmemeli.
// changeUILanguage zaten applyI18nToDOM ile DOM'u günceller, ekstra event'e gerek yoktur.
const LANGUAGE_INIT_EVENT = 'languageChanged';

/**
 * Change UI language without page reload.
 * @param {string} lang - Language code
 */
async function changeUILanguage(lang) {
    if (!i18nInitialized || typeof i18next === 'undefined') {
        console.warn('i18n not initialized');
        return;
    }

    // Fallback to English if lang is empty
    lang = lang || 'en';

    const loadPath = `/static/locales/{{lng}}/common.json`;
    const url = loadPath.replace('{{lng}}', lang);

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (i18next.addResourceBundle) {
            i18next.addResourceBundle(lang, 'translation', data, true, true);
        }
    } catch (err) {
        console.warn(`Could not load locale for ${lang}, trying cached:`, err);
    }

    return new Promise((resolve) => {
        i18next.changeLanguage(lang, function(err) {
            if (err) {
                console.error('Error changing language:', err);
                resolve();
                return;
            }
            applyI18nToDOM();
            // languageChanged event'i dispatch ETME — bu event sadece initUILanguage
            // tarafından sayfa ilk yüklendiğinde dispatch edilir. Aksi halde
            // settings.js'deki listener loadPreferences() çağırarak dropdown'u
            // veritabanındaki eski değere döndürür → kullanıcının seçimi ezilir.
            resolve();
        });
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
            el.innerHTML = translated;
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