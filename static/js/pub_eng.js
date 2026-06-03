/* ══════════════════════════════════════════════════════════════
   CERP Admin - Public Engagements JavaScript
   ══════════════════════════════════════════════════════════════ */

let engagementsData = [];
let engagementsFiltered = [];
let engagementsPage = 1;
const ENGAGEMENTS_PAGE_SIZE = 10;
let _deleteTargetId = null;

// ── Load Engagements ──────────────────────────────────────────

async function loadEngagements() {
    try {
        const res = await fetch('/api/engagements');
        if (!res.ok) throw new Error();
        engagementsData = await res.json();
    } catch {
        engagementsData = [];
    }
    engagementsFiltered = [...engagementsData];
    engagementsPage = 1;
    renderEngagements();
}

function applyPEFilter() {
    const sort = document.getElementById('pe-sort')?.value || '';
    const q = (document.getElementById('pe-search')?.value || '').toLowerCase();

    engagementsFiltered = engagementsData.filter(e => {
        const searchText = `${e.type} ${e.designation} ${e.event_name} ${e.partner} ${e.person_involved} ${e.period}`.toLowerCase();
        return !q || searchText.includes(q);
    });

    // Apply sorting
    if (sort === 'faculty') {
        engagementsFiltered.sort((a, b) => (a.person_involved || '').localeCompare(b.person_involved || ''));
    } else if (sort === 'site') {
        engagementsFiltered.sort((a, b) => (a.partner || '').localeCompare(b.partner || ''));
    }

    engagementsPage = 1;
    renderEngagements();
}

function renderEngagements() {
    const tbody = document.getElementById('pe-tbody');
    const pg = document.getElementById('pe-pg');

    if (!tbody) return;

    const total = engagementsFiltered.length;
    const pages = Math.max(1, Math.ceil(total / ENGAGEMENTS_PAGE_SIZE));
    if (engagementsPage > pages) engagementsPage = 1;
    const slice = engagementsFiltered.slice((engagementsPage - 1) * ENGAGEMENTS_PAGE_SIZE, engagementsPage * ENGAGEMENTS_PAGE_SIZE);

    if (!slice.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding:32px;color:#9ca3af;">No engagements found.</td></tr>`;
    } else {
        tbody.innerHTML = slice.map(e => `
            <tr>
                <td>${e.type || 'N/A'}</td>
                <td>${e.designation || 'N/A'}</td>
                <td>${e.event_name || 'N/A'}</td>
                <td>${e.partner || 'N/A'}</td>
                <td>${e.person_involved || 'N/A'}</td>
                <td>${e.period || 'N/A'}</td>
                <td>
                    <button class="action-btn action-btn-delete" onclick="openDeleteEngagementModal('${e.id || ''}')">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    if (pg) {
        let html = `<button class="pg-btn" onclick="engagementsPgGo(${engagementsPage - 1})" ${engagementsPage === 1 ? 'disabled' : ''}>&lsaquo;</button>`;
        for (let i = 1; i <= pages; i++) html += `<button class="pg-btn ${i === engagementsPage ? 'active' : ''}" onclick="engagementsPgGo(${i})">${i}</button>`;
        html += `<button class="pg-btn" onclick="engagementsPgGo(${engagementsPage + 1})" ${engagementsPage === pages ? 'disabled' : ''}>&rsaquo;</button>`;
        pg.innerHTML = html;
    }
}

window.engagementsPgGo = function (p) { engagementsPage = p; renderEngagements(); };

// ── Add Engagement Modal ──────────────────────────────────────

function openAddEngagementModal() {
    document.getElementById('add-engagement-modal').classList.add('open');
}

function closeAddEngagementModal() {
    document.getElementById('add-engagement-modal').classList.remove('open');
    document.getElementById('add-engagement-form').reset();
    document.getElementById('add-engagement-error').textContent = '';
}

async function submitAddEngagement(event) {
    event.preventDefault();
    const errEl = document.getElementById('add-engagement-error');
    errEl.textContent = '';

    const form = event.target;
    const data = {
        type: form.type.value.trim(),
        designation: form.designation.value.trim(),
        event_name: form.event_name.value.trim(),
        partner: form.partner.value.trim(),
        person_involved: form.person_involved.value.trim(),
        period: form.period.value.trim(),
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    const originalHeight = submitBtn.offsetHeight + 'px';
    submitBtn.style.height = originalHeight;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

    try {
        const res = await fetch('/api/engagements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Failed to add engagement.');
        closeAddEngagementModal();
        await loadEngagements();
    } catch (e) {
        errEl.textContent = e.message;
        submitBtn.disabled = false;
        submitBtn.style.height = '';
        submitBtn.textContent = originalText;
    }
}

// ── Delete Engagement Modal ───────────────────────────────────

function openDeleteEngagementModal(engagementId) {
    _deleteTargetId = engagementId;
    document.getElementById('delete-engagement-modal').classList.add('open');
}

function closeDeleteEngagementModal() {
    document.getElementById('delete-engagement-modal').classList.remove('open');
    _deleteTargetId = null;
}

window.confirmDeleteEngagement = async function () {
    const btn = document.querySelector('#delete-engagement-modal .btn-danger');
    const originalText = btn.textContent;
    const originalHeight = btn.offsetHeight + 'px';
    btn.style.height = originalHeight;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;border-color:white white white transparent;"></div>';

    try {
        const res = await fetch(`/api/engagements/${_deleteTargetId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        closeDeleteEngagementModal();
        await loadEngagements();
    } catch {
        alert('Failed to delete engagement. Please try again.');
        btn.disabled = false;
        btn.style.height = '';
        btn.textContent = originalText;
    }
};

// ── Initialize ────────────────────────────────────────────────

loadEngagements();
