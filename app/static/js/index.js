// ──────────────────────────────────────────────
// Global variables for infinite scroll
// ──────────────────────────────────────────────
let currentPage = 0;
const storiesPerPage = 20;
let isLoading = false;
let hasMoreStories = true;

// SVG icons for eye
const EYE_OPEN_SVG = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`;
const EYE_CLOSED_SVG = `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"/></svg>`;

// ──────────────────────────────────────────────
// Check if we're online or offline
// ──────────────────────────────────────────────
function updateOnlineStatus() {
    document.getElementById('offline-indicator').classList.toggle('hidden', navigator.onLine);
}

// ──────────────────────────────────────────────
// Load stories with pagination
// ──────────────────────────────────────────────
async function loadStories(page = 0, append = false) {
    if (isLoading) return;
    if (!append && page === 0) {
        document.getElementById('stories-container').innerHTML = `
            <div class="text-center py-8">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                <p class="mt-2">Hikayeler yükleniyor...</p>
            </div>
        `;
    }

    isLoading = true;
    if (append) {
        document.getElementById('loading-indicator').classList.remove('hidden');
    }

    try {
        const response = await fetch(`/api/stories/?skip=${page * storiesPerPage}&limit=${storiesPerPage}`);
        const stories = await response.json();

        if (stories.length === 0) {
            hasMoreStories = false;
            document.getElementById('end-of-content').classList.remove('hidden');
            if (!append) {
                document.getElementById('stories-container').innerHTML = `
                    <div class="text-center py-8">
                        <p>Henüz özetlenmiş haber bulunmuyor. İlk özetler yakında eklenecek.</p>
                        <p class="mt-2 text-sm text-gray-500">Veri çekmek için yukarıdaki "Veri Çek" butonunu kullanabilirsiniz.</p>
                    </div>
                `;
            }
        } else {
            const storiesHtml = stories.map(story => buildStoryCardHtml(story)).join('');

            if (append) {
                document.getElementById('stories-container').insertAdjacentHTML('beforeend', storiesHtml);
            } else {
                document.getElementById('stories-container').innerHTML = storiesHtml;
            }

            if (stories.length < storiesPerPage) {
                hasMoreStories = false;
                document.getElementById('end-of-content').classList.remove('hidden');
            } else {
                hasMoreStories = true;
                document.getElementById('end-of-content').classList.add('hidden');
            }
            
        }
    } catch (error) {
        if (!append) {
            document.getElementById('stories-container').innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <p>Hikayeler yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.</p>
                </div>
            `;
        }
    } finally {
        isLoading = false;
        document.getElementById('loading-indicator').classList.add('hidden');

        document.querySelectorAll('.negative-feedback-btn').forEach(button => {
            button.addEventListener('click', function() {
                const storyId = this.getAttribute('data-story-id');
                addNegativeFeedback(storyId);
            });
        });
        document.querySelectorAll('.reprocess-btn').forEach(button => {
            button.addEventListener('click', function() {
                const storyId = this.getAttribute('data-story-id');
                reprocessSingleStory(storyId);
            });
        });
        setupReadToggleListeners();
    }
}

// ──────────────────────────────────────────────
// Build story card HTML (shared between loadStories and onNewStoryPoll)
// ──────────────────────────────────────────────
function buildStoryCardHtml(story) {
    const isRead = story.is_read || false;
    return `
        <article class="mb-6 p-4 rounded-lg shadow story-card ${story.is_dimmed ? 'grayscale opacity-50' : ''} ${story.is_highlighted ? 'border-l-4 border-blue-500' : ''} ${isRead ? 'is-read' : ''}" 
                 data-story-id="${story.id}">
            <div class="flex justify-between items-start">
                <h3 class="text-lg font-bold mb-2">
                    <a href="https://news.ycombinator.com/item?id=${story.hacker_news_id}" 
                       target="_blank" rel="noopener noreferrer" 
                       class="hover:text-blue-600 hover:underline">
                        ${story.title_tr || story.title}
                        ${story.is_highlighted ? '<span class="ml-2 text-blue-500">★</span>' : ''}
                    </a>
                </h3>
                <div class="flex items-center gap-2 text-sm text-gray-500 flex-shrink-0 ml-2">
                    <span>${story.score} puan</span>
                    <button class="read-toggle-btn" data-story-id="${story.id}" title="${isRead ? 'Okunmadı olarak işaretle' : 'Okundu olarak işaretle'}">
                        ${isRead ? EYE_CLOSED_SVG : EYE_OPEN_SVG}
                    </button>
                </div>
            </div>
            
            <div class="card-body-wrapper">
                <p class="text-gray-600 mb-3">by ${story.author}</p>
                
                ${story.content_tr ? `
                    <div class="mb-3">
                        <h4 class="font-bold mb-1">Özet:</h4>
                        <div class="pl-4">${story.content_tr.replace(/\n/g, '<br>')}</div>
                    </div>
                ` : ''}
                
                ${story.comments_summary ? `
                    <div class="mb-3">
                        <h4 class="font-bold mb-1">Yorumlar:</h4>
                        <p class="pl-4">${story.comments_summary}</p>
                    </div>
                ` : ''}
                
                <div class="flex flex-wrap gap-2 mt-3 items-center">
                    ${story.url ? `
                        <a href="${story.url}" target="_blank" class="text-blue-500 hover:underline text-sm">
                            Orijinal içerik
                        </a>
                    ` : ''}
                    
                    <button class="reprocess-btn text-green-600 hover:text-green-800 text-sm flex items-center" 
                            data-story-id="${story.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Yenile
                    </button>
                    
                    <button class="negative-feedback-btn text-red-500 hover:text-red-700 text-sm flex items-center" 
                            data-story-id="${story.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Tekrar gösterme
                    </button>
                    <span class="text-xs text-gray-400 ml-auto hover:underline cursor-default" title="ID: ${story.id}">${new Date(story.hn_created_at || story.created_at).toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                </div>
            </div>
        </article>
    `;
}

// ──────────────────────────────────────────────
// Read toggle: eye button click handler
// ──────────────────────────────────────────────
function handleReadToggle(e) {
    const storyId = this.getAttribute('data-story-id');
    toggleReadStatus(storyId);
}

function setupReadToggleListeners() {
    document.querySelectorAll('.read-toggle-btn').forEach(btn => {
        btn.removeEventListener('click', handleReadToggle);
        btn.addEventListener('click', handleReadToggle);
    });
}

async function toggleReadStatus(storyId) {
    try {
        const res = await fetch(`/api/stories/${storyId}/read`, { method: 'PATCH' });
        if (!res.ok) return;
        const data = await res.json();
        const article = document.querySelector(`article[data-story-id="${storyId}"]`);
        if (!article) return;

        const btn = article.querySelector('.read-toggle-btn');
        if (data.is_read) {
            article.classList.add('is-read');
            if (btn) {
                btn.innerHTML = EYE_CLOSED_SVG;
                btn.title = 'Okunmadı olarak işaretle';
            }
        } else {
            article.classList.remove('is-read');
            if (btn) {
                btn.innerHTML = EYE_OPEN_SVG;
                btn.title = 'Okundu olarak işaretle';
            }
        }
    } catch (e) {
        // Toggle read error
    }
}

// ──────────────────────────────────────────────
// Add negative feedback (toast notification)
// ──────────────────────────────────────────────
async function addNegativeFeedback(storyId) {
    try {
        const response = await fetch(`/api/stories/feedback/negative/${storyId}`, {
            method: 'POST'
        });

        if (response.ok) {
            const storyElement = document.querySelector(`[data-story-id="${storyId}"]`);
            if (storyElement) {
                storyElement.classList.add('hidden');
            }
            showToast('success', 'Bu içerik bundan sonra gösterilmeyecek.');
        }
    } catch (error) {
        showToast('error', 'Bir hata oluştu. Lütfen tekrar deneyin.');
    }
}

// ──────────────────────────────────────────────
// Trigger worker from home page (toast + loader)
// ──────────────────────────────────────────────
async function triggerWorkerHome() {
    const button = document.getElementById('trigger-worker-home');
    const btnText = document.getElementById('trigger-home-text');
    const spinner = document.getElementById('trigger-home-spinner');
    const statusText = document.getElementById('worker-status-home');

    button.disabled = true;
    btnText.textContent = 'Başlatılıyor...';
    spinner.classList.remove('hidden');
    statusText.classList.remove('hidden');

    if (window.showWorkerProgress) {
        window.showWorkerProgress();
        window.updateWorkerProgress(0);
    }

    try {
        const response = await fetch('/api/settings/trigger-worker', { method: 'POST' });

        if (response.ok) {
            const result = await response.json();
            showToast('success', 'Veri çekimi başlatıldı! ' + (result.message || ''));
            simulateWorkerProgress();
        } else {
            const err = await response.json();
            showToast('error', err.detail || 'Worker başlatılamadı');
            if (window.hideWorkerProgress) window.hideWorkerProgress();
        }
    } catch (error) {
        showToast('error', 'Veri çekimi başlatılırken bir hata oluştu.');
        if (window.hideWorkerProgress) window.hideWorkerProgress();
    } finally {
        button.disabled = false;
        btnText.textContent = 'Veri Çek';
        spinner.classList.add('hidden');
        statusText.classList.add('hidden');
    }
}

// ──────────────────────────────────────────────
// Reprocess untranslated stories from home page (SSE with live progress)
// ──────────────────────────────────────────────
async function reprocessUntranslatedHome() {
    const button = document.getElementById('reprocess-home');
    const btnText = document.getElementById('reprocess-home-text');
    const spinner = document.getElementById('reprocess-home-spinner');
    const statusText = document.getElementById('worker-status-home');

    button.disabled = true;
    btnText.textContent = 'İşleniyor...';
    spinner.classList.remove('hidden');
    statusText.classList.remove('hidden');

    // Reset and show progress bar
    if (window.showWorkerProgress) window.showWorkerProgress();
    if (window.updateWorkerProgress) window.updateWorkerProgress(0);
    if (window.showWorkerLabel) window.showWorkerLabel('0 / 0 - %0');

    function resetButton() {
        button.disabled = false;
        btnText.textContent = 'Çevrilmemişleri İşle';
        spinner.classList.add('hidden');
        statusText.classList.add('hidden');
        const cancelBtn = document.getElementById('cancel-reprocess-home');
        if (cancelBtn) cancelBtn.classList.add('hidden');
    }

    // Use raw EventSource (no reconnect) — if connection drops,
    // checkReprocessState() polling will pick up the state.
    const sse = new EventSource('/api/stories/reprocess-untranslated/stream');

    sse.addEventListener('progress', function(e) {
        try {
            const data = JSON.parse(e.data);
            if (window.updateWorkerProgress) {
                window.updateWorkerProgress(data.percentage);
            }
            if (window.showWorkerLabel) {
                const label = `${data.current} / ${data.total} - %${data.percentage}`;
                window.showWorkerLabel(label);
            }
            if (data.story_id) {
                statusText.textContent = `İşleniyor: #${data.story_id} (${data.current}/${data.total})`;
                statusText.classList.remove('hidden');
            }
        } catch (err) {
            // SSE progress parse error
        }
    });

    sse.addEventListener('story_update', function(e) {
        try {
            const story = JSON.parse(e.data);
            if (typeof window.updateStoryCard === 'function') {
                window.updateStoryCard(story);
            }
        } catch (err) {
            // SSE story_update parse error
        }
    });

    sse.addEventListener('complete', function(e) {
        try {
            const data = JSON.parse(e.data);
            sse.close();
            resetButton();

            if (window.updateWorkerProgress) window.updateWorkerProgress(100);
            if (window.showWorkerLabel) window.showWorkerLabel(`${data.processed} / ${data.total} - %100`);

            setTimeout(() => {
                if (window.hideWorkerProgress) window.hideWorkerProgress();
                if (window.hideWorkerLabel) window.hideWorkerLabel();
            }, 2000);

            const msg = data.processed > 0
                ? `${data.processed} hikaye işlendi. ${data.errors > 0 ? `${data.errors} hata.` : ''}`
                : 'İşlenecek hikaye bulunamadı.';
            showToast(data.errors > 0 ? 'warning' : 'success', msg);

            // Reload first page if stories were processed
            if (data.processed > 0) {
                setTimeout(() => {
                    currentPage = 0;
                    hasMoreStories = true;
                    document.getElementById('end-of-content').classList.add('hidden');
                    loadStories();
                }, 1000);
            }
        } catch (err) {
            // SSE complete parse error
        }
    });

    sse.addEventListener('error', function() {
        sse.close();
        resetButton();

        if (window.hideWorkerProgress) window.hideWorkerProgress();
        if (window.hideWorkerLabel) window.hideWorkerLabel();

        // Show error only if there was no 'complete' event
        showToast('warning', 'Çeviri bağlantısı koptu. Sayfayı yenileyip durumu kontrol edin.');
    });
}

// ──────────────────────────────────────────────
// Reprocess a single story via API (toast + loader, no page reload)
// ──────────────────────────────────────────────
async function reprocessSingleStory(storyId) {
    const btn = document.querySelector(`.reprocess-btn[data-story-id="${storyId}"]`);
    const originalText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="inline-block w-3 h-3 border-2 border-green-600 border-t-transparent rounded-full animate-spin mr-1"></span> Yenileniyor...';
    }
    try {
        const res = await fetch(`/api/stories/${storyId}/reprocess`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            showToast('error', err.detail || 'Yenileme başarısız');
            if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
            return;
        }
        showToast('info', 'HN verisi alındı, AI çevirisi başlatıldı. Güncelleniyor...');

        const maxAttempts = 20;
        let attempt = 0;
        let done = false;

        async function pollOnce() {
            if (done) return;
            attempt++;
            try {
                const r = await fetch(`/api/stories/${storyId}`);
                if (r.ok) {
                    const updated = await r.json();
                    if (!done && updated.title_tr && updated.content_tr && updated.comments_summary
                        && updated.title_tr !== ''
                        && updated.content_tr !== ''
                        && updated.comments_summary !== ''
                        && !updated.title_tr.startsWith('[TR]')
                        && updated.content_tr !== 'İçerik özeti mevcut değil.'
                        && updated.comments_summary !== 'Yorum özeti mevcut değil.') {
                        done = true;
                        updateStoryCard(updated);
                        showToast('success', 'Hikaye güncellendi!');
                        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
                        return;
                    }
                }
            } catch (e) {
                // Poll error
            }
            if (attempt >= maxAttempts && !done) {
                done = true;
                showToast('warning', 'AI çevirisi tamamlanamadı, sayfayı yenileyin.');
                if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
                return;
            }
            setTimeout(pollOnce, 6000);
        }

        setTimeout(pollOnce, 6000);

    } catch (e) {
        showToast('error', 'Yenileme sırasında hata oluştu.');
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}

// ──────────────────────────────────────────────
// Update a single story card in-place with new data
// ──────────────────────────────────────────────
function updateStoryCard(story) {
    const article = document.querySelector(`article[data-story-id="${story.id}"]`);
    if (!article) return;

    const titleLink = article.querySelector('h3 a');
    if (titleLink) {
        titleLink.innerHTML = (story.title_tr || story.title) + (story.is_highlighted ? ' <span class="ml-2 text-blue-500">★</span>' : '');
    }

    // Update header row: score · eye
    const headerRight = article.querySelector('.flex.justify-between.items-start .flex.items-center');
    if (headerRight) {
        const scoreSpan = headerRight.querySelector('span');
        const eyeBtn = headerRight.querySelector('.read-toggle-btn');
        if (scoreSpan) scoreSpan.textContent = story.score + ' puan';
        if (eyeBtn) {
            const isRead = story.is_read || false;
            eyeBtn.innerHTML = isRead ? EYE_CLOSED_SVG : EYE_OPEN_SVG;
            eyeBtn.title = isRead ? 'Okunmadı olarak işaretle' : 'Okundu olarak işaretle';
        }
    }

    // Update footer date tooltip (ID in title)
    const footerDateSpan = article.querySelector('.flex-wrap .ml-auto');
    if (footerDateSpan) {
        footerDateSpan.title = 'ID: ' + story.id;
    }

    const authorP = article.querySelector('p.text-gray-600');
    if (authorP) {
        authorP.textContent = 'by ' + story.author;
    }

    const existingContent = article.querySelector('h4.font-bold.mb-1');
    if (story.content_tr) {
        if (existingContent && existingContent.textContent === 'Özet:') {
            const contentDiv = existingContent.nextElementSibling;
            if (contentDiv) contentDiv.innerHTML = story.content_tr.replace(/\n/g, '<br>');
        } else {
            const oldContentHeader = article.querySelector('h4');
            if (oldContentHeader && oldContentHeader.textContent === 'Özet:') {
                oldContentHeader.parentElement.remove();
            }
            const authorP = article.querySelector('p.text-gray-600');
            if (authorP) {
                const newContent = document.createElement('div');
                newContent.className = 'mb-3';
                newContent.innerHTML = '<h4 class="font-bold mb-1">Özet:</h4><div class="pl-4">' + story.content_tr.replace(/\n/g, '<br>') + '</div>';
                authorP.insertAdjacentElement('afterend', newContent);
            }
        }
    }

    const existingComments = article.querySelectorAll('h4.font-bold.mb-1');
    let commentsHeader = null;
    existingComments.forEach(h => { if (h.textContent === 'Yorumlar:') commentsHeader = h; });

    if (story.comments_summary && story.comments_summary !== 'Yorum özeti mevcut değil.') {
        if (commentsHeader) {
            const commentsDiv = commentsHeader.nextElementSibling;
            if (commentsDiv) commentsDiv.textContent = story.comments_summary;
        } else {
            const newComments = document.createElement('div');
            newComments.className = 'mb-3';
            newComments.innerHTML = '<h4 class="font-bold mb-1">Yorumlar:</h4><p class="pl-4">' + story.comments_summary + '</p>';
            const contentSection = article.querySelector('.card-body-wrapper > .mb-3:last-of-type');
            if (contentSection) {
                contentSection.insertAdjacentElement('afterend', newComments);
            } else {
                article.querySelector('.card-body-wrapper .flex-wrap').insertAdjacentElement('beforebegin', newComments);
            }
        }
    }

    // is_read state update
    if (story.is_read !== undefined) {
        if (story.is_read) {
            article.classList.add('is-read');
        } else {
            article.classList.remove('is-read');
        }
    }
}

// ──────────────────────────────────────────────
// Simulate worker progress
// ──────────────────────────────────────────────
function simulateWorkerProgress() {
    let progress = 0;
    const interval = setInterval(() => {
        progress += 5;
        if (progress > 100) {
            progress = 100;
            clearInterval(interval);
            setTimeout(() => {
                if (window.hideWorkerProgress) window.hideWorkerProgress();
            }, 500);
        }
        if (window.updateWorkerProgress) window.updateWorkerProgress(progress);
    }, 300);
}

// ──────────────────────────────────────────────
// Infinite scroll
// ──────────────────────────────────────────────
function handleScroll() {
    const scrollPosition = window.innerHeight + window.scrollY;
    const pageHeight = document.body.offsetHeight;
    const threshold = 100;

    if (scrollPosition >= (pageHeight - threshold) && hasMoreStories && !isLoading) {
        currentPage++;
        loadStories(currentPage, true);
    }
}

// ──────────────────────────────────────────────
// Real-time story updates via polling
// ──────────────────────────────────────────────
window.onNewStoryPoll = function(story) {
    const container = document.getElementById('stories-container');
    if (!container) return;

    if (document.querySelector(`article[data-story-id="${story.id}"]`)) return;

    const html = buildStoryCardHtml(story);

    container.insertAdjacentHTML('afterbegin', html);

    const newArticle = container.querySelector(`article[data-story-id="${story.id}"]`);
    if (newArticle) {
        newArticle.querySelector('.reprocess-btn')?.addEventListener('click', function() {
            reprocessSingleStory(story.id);
        });
        newArticle.querySelector('.negative-feedback-btn')?.addEventListener('click', function() {
            addNegativeFeedback(story.id);
        });
    }

    setupReadToggleListeners();

    if (typeof window.updateLastKnownStoryId === 'function') {
        window.updateLastKnownStoryId(story.id);
    }
    showToast('info', 'Yeni hikaye eklendi: ' + (story.title_tr || story.title).substring(0, 40) + '...');
};

window.onNewStorySSE = window.onNewStoryPoll;

// ──────────────────────────────────────────────
// DOMContentLoaded (index page)
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // Start SSE for live new story notifications
    if (typeof initSSE === 'function') {
        setTimeout(() => {
            initSSE();
        }, 5000);
    }

    updateOnlineStatus();

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    loadStories();

    window.addEventListener('scroll', handleScroll);

    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            currentPage = 0;
            hasMoreStories = true;
            document.getElementById('end-of-content').classList.add('hidden');
            loadStories();
        });
    }

    const triggerButton = document.getElementById('trigger-worker-home');
    if (triggerButton) {
        triggerButton.addEventListener('click', triggerWorkerHome);
    }

    const reprocessButton = document.getElementById('reprocess-home');
    if (reprocessButton) {
        reprocessButton.addEventListener('click', reprocessUntranslatedHome);
    }
});