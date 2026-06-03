/* ══════════════════════════════════════════════════════════════
   CERP Admin - TAP-HSP JavaScript
   ══════════════════════════════════════════════════════════════ */

let tapData = [];
let tapFiltered = [];
let tapPage = 1;
const TAP_PAGE_SIZE = 10;
let _deleteTAPTargetId = null;

// ── Load TAP Projects ─────────────────────────────────────────

async function loadTAPProjects() {
    try {
        const res = await fetch('/api/tap-projects');
        if (!res.ok) throw new Error();
        tapData = await res.json();
    } catch {
        tapData = [];
    }
    tapFiltered = [...tapData];
    tapPage = 1;
    renderTAPProjects();
}

function applyTAPFilter() {
    const sort = document.getElementById('tap-sort')?.value || '';
    const filter = document.getElementById('tap-filter')?.value || '';
    const q = (document.getElementById('tap-search')?.value || '').toLowerCase();

    tapFiltered = tapData.filter(t => {
        const searchText = `${t.title} ${t.province} ${t.municipality} ${t.period} ${t.partner_agency} ${t.person_involved} ${t.role}`.toLowerCase();
        return !q || searchText.includes(q);
    });

    // Apply sorting by site (municipality)
    if (sort === 'site') {
        tapFiltered.sort((a, b) => (a.municipality || '').localeCompare(b.municipality || ''));
    }

    // Apply alphabetical filtering
    if (filter === 'a-z') {
        tapFiltered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (filter === 'z-a') {
        tapFiltered.sort((a, b) => (b.title || '').localeCompare(a.title || ''));
    }

    tapPage = 1;
    renderTAPProjects();
}

function renderTAPProjects() {
    const tbody = document.getElementById('tap-tbody');
    const pg = document.getElementById('tap-pg');

    if (!tbody) return;

    const total = tapFiltered.length;
    const pages = Math.max(1, Math.ceil(total / TAP_PAGE_SIZE));
    if (tapPage > pages) tapPage = 1;
    const slice = tapFiltered.slice((tapPage - 1) * TAP_PAGE_SIZE, tapPage * TAP_PAGE_SIZE);

    if (!slice.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding:32px;color:#9ca3af;">No projects found.</td></tr>`;
    } else {
        tbody.innerHTML = slice.map(t => {
            const docLink = t.document_url
                ? `<a href="${t.document_url}" target="_blank" class="doc-link">View Document</a>`
                : 'N/A';
            return `
                <tr>
                    <td>${t.title || 'N/A'}</td>
                    <td>${t.province || 'N/A'}</td>
                    <td>${t.municipality || 'N/A'}</td>
                    <td>${t.period || 'N/A'}</td>
                    <td>${t.partner_agency || 'N/A'}</td>
                    <td>${t.person_involved || 'N/A'}</td>
                    <td>${t.role || 'N/A'}</td>
                    <td>${docLink}</td>
                    <td>
                        <button class="action-btn action-btn-delete" onclick="openDeleteTAPModal('${t.id || ''}')">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    if (pg) {
        let html = `<button class="pg-btn" onclick="tapPgGo(${tapPage - 1})" ${tapPage === 1 ? 'disabled' : ''}>&lsaquo;</button>`;
        for (let i = 1; i <= pages; i++) html += `<button class="pg-btn ${i === tapPage ? 'active' : ''}" onclick="tapPgGo(${i})">${i}</button>`;
        html += `<button class="pg-btn" onclick="tapPgGo(${tapPage + 1})" ${tapPage === pages ? 'disabled' : ''}>&rsaquo;</button>`;
        pg.innerHTML = html;
    }
}

window.tapPgGo = function (p) { tapPage = p; renderTAPProjects(); };

// ── Add TAP Project Modal ─────────────────────────────────────

function openAddTAPModal() {
    document.getElementById('add-tap-modal').classList.add('open');
}

function closeAddTAPModal() {
    document.getElementById('add-tap-modal').classList.remove('open');
    document.getElementById('add-tap-form').reset();
    document.getElementById('add-tap-error').textContent = '';
}

async function submitAddTAP(event) {
    event.preventDefault();
    const errEl = document.getElementById('add-tap-error');
    errEl.textContent = '';

    const form = event.target;
    const data = {
        title: form.title.value.trim(),
        province: form.province.value.trim(),
        municipality: form.municipality.value.trim(),
        period: form.period.value.trim(),
        partner_agency: form.partner_agency.value.trim(),
        person_involved: form.person_involved.value.trim(),
        role: form.role.value.trim(),
        document_url: form.document_url.value.trim() || null,
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    const originalHeight = submitBtn.offsetHeight + 'px';
    submitBtn.style.height = originalHeight;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

    try {
        const res = await fetch('/api/tap-projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Failed to add project.');
        closeAddTAPModal();
        await loadTAPProjects();
    } catch (e) {
        errEl.textContent = e.message;
        submitBtn.disabled = false;
        submitBtn.style.height = '';
        submitBtn.textContent = originalText;
    }
}

// ── Delete TAP Project Modal ──────────────────────────────────

function openDeleteTAPModal(projectId) {
    _deleteTAPTargetId = projectId;
    document.getElementById('delete-tap-modal').classList.add('open');
}

function closeDeleteTAPModal() {
    document.getElementById('delete-tap-modal').classList.remove('open');
    _deleteTAPTargetId = null;
}

window.confirmDeleteTAP = async function () {
    const btn = document.querySelector('#delete-tap-modal .btn-danger');
    const originalText = btn.textContent;
    const originalHeight = btn.offsetHeight + 'px';
    btn.style.height = originalHeight;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;border-color:white white white transparent;"></div>';

    try {
        const res = await fetch(`/api/tap-projects/${_deleteTAPTargetId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        closeDeleteTAPModal();
        await loadTAPProjects();
    } catch {
        alert('Failed to delete project. Please try again.');
        btn.disabled = false;
        btn.style.height = '';
        btn.textContent = originalText;
    }
};

// ── Initialize ────────────────────────────────────────────────

loadTAPProjects();
