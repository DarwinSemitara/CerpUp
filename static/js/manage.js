/* ══════════════════════════════════════════════════════════════
   CERP Admin - Manage Page JavaScript
   ══════════════════════════════════════════════════════════════ */

let membersData = [];
let membersFiltered = [];
let membersPage = 1;
const MEMBERS_PAGE_SIZE = 8;
let selectedAvailability = [];
let _caTargetId = null;
let _deleteTargetId = null;

// ── Load Members ──────────────────────────────────────────────

async function loadMembers() {
    try {
        const res = await fetch('/api/members');
        if (!res.ok) throw new Error();
        membersData = await res.json();
    } catch {
        membersData = [];
    }
    membersFiltered = [...membersData];
    membersPage = 1;
    renderMembers();
}

function applyMemberFilter() {
    const type = document.getElementById('m-filter-type')?.value || '';
    const facultyOnly = document.getElementById('m-filter-faculty')?.checked || false;
    const q = (document.getElementById('m-search')?.value || '').toLowerCase();
    membersFiltered = membersData.filter(m =>
        (!type || m.type === type) &&
        (!facultyOnly || m.is_faculty === true) &&
        (!q || `${m.first} ${m.last} ${m.email} ${m.position} ${m.role}`.toLowerCase().includes(q))
    );
    membersPage = 1;
    renderMembers();
}

function renderMembers() {
    const tbody = document.getElementById('members-tbody');
    const pg = document.getElementById('members-pg');

    if (!tbody) return;

    const total = membersFiltered.length;
    const pages = Math.max(1, Math.ceil(total / MEMBERS_PAGE_SIZE));
    if (membersPage > pages) membersPage = 1;
    const slice = membersFiltered.slice((membersPage - 1) * MEMBERS_PAGE_SIZE, membersPage * MEMBERS_PAGE_SIZE);

    if (!slice.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding:32px;color:#9ca3af;">No members found.</td></tr>`;
    } else {
        tbody.innerHTML = slice.map(m => {
            const photoHtml = m.photo_url
                ? `<img src="${m.photo_url}" class="member-photo" alt="${m.first}">`
                : `<div class="user-avatar">${(m.first || 'U')[0].toUpperCase()}</div>`;

            // Check if account exists (has uid field)
            const hasAccount = m.uid && m.uid.trim() !== '';
            const accountButton = hasAccount
                ? `<button class="action-btn action-btn-manage" onclick="openManageAccountModal('${m.id || ''}', '${m.email || ''}')">Manage</button>`
                : `<button class="action-btn action-btn-create" onclick="openCreateAccountModal('${m.id || ''}', '${m.email || ''}')">Create Account</button>`;

            // Faculty badge
            const facultyBadge = m.is_faculty
                ? `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:#10b981;color:white;border-radius:4px;font-size:0.7rem;font-weight:600;">
                    <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    Yes
                </span>`
                : `<span style="color:#9ca3af;font-size:0.8rem;">—</span>`;

            return `
                <tr>
                    <td>${photoHtml}</td>
                    <td>${m.first} ${m.last}</td>
                    <td>${m.email || 'N/A'}</td>
                    <td>${m.suffix || 'N/A'}</td>
                    <td><span style="text-transform:capitalize;">${m.type || 'faculty'}</span></td>
                    <td>${facultyBadge}</td>
                    <td>
                        <div class="member-actions">
                            ${accountButton}
                            <button class="action-btn action-btn-delete" onclick="openDeleteModal('${m.id || ''}')">Delete</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    if (pg) {
        let html = `<button class="pg-btn" onclick="membersPgGo(${membersPage - 1})" ${membersPage === 1 ? 'disabled' : ''}>&lsaquo;</button>`;
        for (let i = 1; i <= pages; i++) html += `<button class="pg-btn ${i === membersPage ? 'active' : ''}" onclick="membersPgGo(${i})">${i}</button>`;
        html += `<button class="pg-btn" onclick="membersPgGo(${membersPage + 1})" ${membersPage === pages ? 'disabled' : ''}>&rsaquo;</button>`;
        pg.innerHTML = html;
    }
}

window.membersPgGo = function (p) { membersPage = p; renderMembers(); };

// ── Add Member Modal ──────────────────────────────────────────

function openAddMemberModal() {
    document.getElementById('add-member-modal').classList.add('open');
}

function closeAddMemberModal() {
    document.getElementById('add-member-modal').classList.remove('open');
    resetAddMemberForm();
}

function resetAddMemberForm() {
    document.getElementById('add-member-form').reset();
    document.getElementById('photo-preview').classList.remove('show');
    document.getElementById('add-member-error').textContent = '';
    selectedAvailability = [];
    document.querySelectorAll('.avail-chip').forEach(chip => chip.classList.remove('selected'));
}

function previewPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('photo-preview');
            preview.src = e.target.result;
            preview.classList.add('show');
        };
        reader.readAsDataURL(file);
    }
}

function toggleAvailability(chip, day) {
    chip.classList.toggle('selected');
    if (chip.classList.contains('selected')) {
        if (!selectedAvailability.includes(day)) {
            selectedAvailability.push(day);
        }
    } else {
        selectedAvailability = selectedAvailability.filter(d => d !== day);
    }
}

let selectedRoles = [];

function toggleRoleDropdown() {
    const dd = document.getElementById('role-dropdown');
    if (dd) dd.classList.toggle('open');
}

function updateRoleSelection() {
    const checkboxes = document.querySelectorAll('#role-dropdown-menu input[type="checkbox"]');
    selectedRoles = [];
    checkboxes.forEach(cb => {
        if (cb.checked) selectedRoles.push(cb.value);
    });
    // Update display text
    const textEl = document.getElementById('role-dropdown-text');
    if (textEl) {
        textEl.textContent = selectedRoles.length > 0 ? selectedRoles.join(', ') : 'Select roles...';
    }
    // Update hidden input
    const hidden = document.getElementById('role-hidden-input');
    if (hidden) hidden.value = selectedRoles.join(',');
}

// Close dropdown when clicking outside
document.addEventListener('click', function (e) {
    const dd = document.getElementById('role-dropdown');
    if (dd && !dd.contains(e.target)) {
        dd.classList.remove('open');
    }
});

async function submitAddMember(event) {
    event.preventDefault();
    const errEl = document.getElementById('add-member-error');
    errEl.textContent = '';

    const form = event.target;
    const fd = new FormData(form);

    // Get submit button and add loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    const originalHeight = submitBtn.offsetHeight + 'px';
    submitBtn.style.height = originalHeight;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

    // Add availability
    selectedAvailability.forEach(day => fd.append('availability', day));

    // Auto-determine member type from selected roles
    const roles = selectedRoles || [];
    let memberType = 'admin_staff';
    if (roles.some(r => r === 'Chairperson')) {
        memberType = 'chairperson';
    } else if (roles.some(r => ['Associate Professor', 'Assistant Professor', 'Instructor', 'Teaching Associate'].includes(r))) {
        memberType = 'faculty';
    } else if (roles.some(r => ['University Research Associate 1', 'Junior Project Assistant'].includes(r))) {
        memberType = 'staff';
    }
    fd.set('type', memberType);

    // Add is_faculty checkbox (convert to string 'true'/'false')
    const isFaculty = document.getElementById('is-faculty-checkbox')?.checked || false;
    fd.append('is_faculty', isFaculty ? 'true' : 'false');

    // Add photo
    const photoInput = document.getElementById('member-photo-input');
    const photo = photoInput.files[0];
    if (photo) fd.append('photo', photo);

    try {
        const res = await fetch('/api/members', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add member.');
        closeAddMemberModal();
        resetAddMemberForm();
        await loadMembers();
        showSuccessModal('Member added successfully!');
    } catch (e) {
        errEl.textContent = e.message;
        submitBtn.disabled = false;
        submitBtn.style.height = '';
        submitBtn.textContent = originalText;
    }
}

// ── Create Account Modal ──────────────────────────────────────

function openCreateAccountModal(memberId, email) {
    _caTargetId = memberId;
    document.getElementById('ca-email').value = email || '';
    document.getElementById('ca-password').value = '';
    document.getElementById('create-account-error').textContent = '';
    document.getElementById('create-account-modal').classList.add('open');
}

function closeCreateAccountModal() {
    document.getElementById('create-account-modal').classList.remove('open');
    _caTargetId = null;
}

function openManageAccountModal(memberId, email) {
    // For now, just show an alert. You can expand this later with reset password, etc.
    alert(`Account management for ${email}\n\nAccount already exists. Future features:\n- Reset password\n- Change email\n- Disable account`);
}

async function confirmCreateAccount() {
    const errEl = document.getElementById('create-account-error');
    errEl.textContent = '';

    const email = document.getElementById('ca-email').value.trim();
    const password = document.getElementById('ca-password').value.trim();

    if (!email || !password) {
        errEl.textContent = 'Email and password are required.';
        return;
    }

    if (password.length < 6) {
        errEl.textContent = 'Password must be at least 6 characters.';
        return;
    }

    const btn = document.querySelector('#create-account-modal .btn-primary');
    const originalText = btn.textContent;
    const originalHeight = btn.offsetHeight + 'px';
    btn.style.height = originalHeight;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

    try {
        const res = await fetch(`/api/members/${_caTargetId}/create-account`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to create account.');
        closeCreateAccountModal();
        await loadMembers();
        showSuccessModal('Account created successfully!');
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
        btn.style.height = '';
        btn.textContent = originalText;
    }
}

// ── Delete Member Modal ───────────────────────────────────────

function openDeleteModal(memberId) {
    _deleteTargetId = memberId;

    // Check if member has an account and show appropriate warning
    const member = membersData.find(m => m.id === memberId);
    const warningEl = document.getElementById('delete-member-warning');
    if (warningEl) {
        if (member && member.uid) {
            warningEl.style.display = 'block';
            warningEl.textContent = '⚠️ This member has a user account. Deleting will also remove their login access.';
        } else if (member && member.is_faculty) {
            warningEl.style.display = 'block';
            warningEl.textContent = '⚠️ This member is listed as faculty. They will be removed from the Faculty & Staff page.';
        } else {
            warningEl.style.display = 'none';
        }
    }

    document.getElementById('delete-member-modal').classList.add('open');
}

function closeDeleteModal() {
    document.getElementById('delete-member-modal').classList.remove('open');
    _deleteTargetId = null;
}

window.confirmDeleteMember = async function () {
    const btn = document.querySelector('#delete-member-modal .btn-danger');
    const originalText = btn.textContent;
    const originalHeight = btn.offsetHeight + 'px';
    btn.style.height = originalHeight;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;border-color:white white white transparent;"></div>';

    try {
        const res = await fetch(`/api/members/${_deleteTargetId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed');

        // Show warning if member had an account
        const msg = data.had_account
            ? 'Member and their user account have been deleted.'
            : 'Member deleted successfully!';

        closeDeleteModal();
        await loadMembers();
        showSuccessModal(msg);
    } catch (e) {
        alert('Failed to delete member: ' + (e.message || 'Please try again.'));
    } finally {
        // ALWAYS reset button state so it works next time
        btn.disabled = false;
        btn.style.height = '';
        btn.textContent = originalText;
    }
};

// ── Success Modal ─────────────────────────────────────────────

function showSuccessModal(message) {
    const modal = document.getElementById('success-modal');
    const messageEl = document.getElementById('success-message');
    messageEl.textContent = message;
    modal.classList.add('open');

    // Auto-close after 2 seconds
    setTimeout(() => {
        modal.classList.remove('open');
    }, 2000);
}

// ── Initialize ────────────────────────────────────────────────

loadMembers();
