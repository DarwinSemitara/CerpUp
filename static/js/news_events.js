/* ══════════════════════════════════════════════════════════════
   CERP Admin - News & Events Management JavaScript
   ══════════════════════════════════════════════════════════════ */

let newsData = [];
let selectedMediaType = 'text';
let _deleteNewsId = null;

// ── Load News ──────────────────────────────────────────────────

async function loadNews() {
    try {
        const res = await fetch('/api/news');
        if (!res.ok) throw new Error();
        newsData = await res.json();
        renderNews();
    } catch {
        newsData = [];
        renderNews();
    }
}

function renderNews() {
    const grid = document.getElementById('news-grid');
    if (!grid) return;

    if (!newsData.length) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: #9ca3af;">
                <svg width="64" height="64" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="margin: 0 auto 16px; opacity: 0.3;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                <p style="font-size: 1rem; font-weight: 600; margin-bottom: 8px;">No news or events yet</p>
                <p style="font-size: 0.875rem;">Click "Add News/Event" to create your first entry</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = newsData.map(news => {
        let mediaHtml = '';

        if (news.media_type === 'image' && news.media_url) {
            mediaHtml = `<img src="${news.media_url}" alt="${news.title}">`;
        } else if (news.media_type === 'video' && news.media_url) {
            // Convert YouTube URL to embed format
            let embedUrl = news.media_url;
            if (embedUrl.includes('youtube.com/watch')) {
                const videoId = new URL(embedUrl).searchParams.get('v');
                embedUrl = `https://www.youtube.com/embed/${videoId}`;
            } else if (embedUrl.includes('youtu.be/')) {
                const videoId = embedUrl.split('youtu.be/')[1].split('?')[0];
                embedUrl = `https://www.youtube.com/embed/${videoId}`;
            }
            mediaHtml = `<iframe src="${embedUrl}" allowfullscreen></iframe>`;
        } else {
            mediaHtml = `<div class="news-media-placeholder">📰</div>`;
        }

        const date = news.created_at ? new Date(news.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }) : 'N/A';

        return `
            <div class="news-card">
                <div class="news-media">
                    ${mediaHtml}
                </div>
                <div class="news-content">
                    <h3 class="news-title">${news.title}</h3>
                    ${news.description ? `<p class="news-description">${news.description}</p>` : ''}
                    <div class="news-meta">
                        <span class="news-date">${date}</span>
                        <div class="news-actions">
                            <button class="action-btn action-btn-delete" onclick="openDeleteNewsModal('${news.id}')">
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ── Add News Modal ──────────────────────────────────────────────

function openAddNewsModal() {
    document.getElementById('add-news-modal').classList.add('open');
    selectMediaType('text');
}

function closeAddNewsModal() {
    document.getElementById('add-news-modal').classList.remove('open');
    resetAddNewsForm();
}

function resetAddNewsForm() {
    document.getElementById('add-news-form').reset();
    document.getElementById('media-preview').classList.remove('show');
    document.getElementById('add-news-error').textContent = '';
    selectMediaType('text');
}

function selectMediaType(type) {
    selectedMediaType = type;
    document.getElementById('media-type-input').value = type;

    // Update button states
    document.querySelectorAll('.media-type-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event?.target?.classList.add('active');

    // Show/hide appropriate upload areas
    document.getElementById('image-upload-area').style.display = type === 'image' ? 'block' : 'none';
    document.getElementById('video-url-area').style.display = type === 'video' ? 'block' : 'none';
}

function previewMedia(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('media-preview');
            preview.src = e.target.result;
            preview.classList.add('show');
        };
        reader.readAsDataURL(file);
    }
}

async function submitAddNews(event) {
    event.preventDefault();
    const errEl = document.getElementById('add-news-error');
    errEl.textContent = '';

    const form = event.target;
    const fd = new FormData(form);

    // Get submit button and add loading state
    const submitBtn = document.getElementById('add-news-submit-btn');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="content-spinner" style="display:inline-flex;align-items:center;gap:8px;"><div class="spinner-ring" style="width:14px;height:14px;border-width:2px;"></div> Adding...</div>';

    // Add media file if image type
    if (selectedMediaType === 'image') {
        const mediaInput = document.getElementById('news-media-input');
        const media = mediaInput.files[0];
        if (media) {
            fd.append('media', media);
        }
    }

    try {
        const res = await fetch('/api/news', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add news.');
        closeAddNewsModal();
        await loadNews();
    } catch (e) {
        errEl.textContent = e.message;
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// ── Delete News Modal ──────────────────────────────────────────

function openDeleteNewsModal(newsId) {
    _deleteNewsId = newsId;
    document.getElementById('delete-news-modal').classList.add('open');
}

function closeDeleteNewsModal() {
    document.getElementById('delete-news-modal').classList.remove('open');
    _deleteNewsId = null;
}

async function confirmDeleteNews() {
    const btn = document.getElementById('delete-news-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<div class="content-spinner" style="display:inline-flex;align-items:center;gap:8px;"><div class="spinner-ring" style="width:14px;height:14px;border-width:2px;"></div> Deleting...</div>';

    try {
        const res = await fetch(`/api/news/${_deleteNewsId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        closeDeleteNewsModal();
        await loadNews();
    } catch {
        alert('Failed to delete news. Please try again.');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ── Initialize ────────────────────────────────────────────────

loadNews();
