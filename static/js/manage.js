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
    document.getElementById('ca-member-id').value = '';
    document.getElementById('ca-email').value = email || '';
    document.getElementById('create-account-error').textContent = '';
    document.getElementById('create-account-modal').classList.add('open');
}

function closeCreateAccountModal() {
    document.getElementById('create-account-modal').classList.remove('open');
    _caTargetId = null;
}

function openManageAccountModal(memberId, email) {
    // Open the promotions modal instead
    openPromotionsModal(memberId);
}

function openPromotionsModal(memberId) {
    // Store the member ID for future use
    window._promotionsTargetId = memberId;
    document.getElementById('promotions-modal').classList.add('open');
}

function closePromotionsModal() {
    document.getElementById('promotions-modal').classList.remove('open');
    window._promotionsTargetId = null;
}

async function confirmCreateAccount() {
    const errEl = document.getElementById('create-account-error');
    errEl.textContent = '';

    const memberId = document.getElementById('ca-member-id').value.trim();
    const email = document.getElementById('ca-email').value.trim();

    if (!memberId || !email) {
        errEl.textContent = 'Member ID and email are required.';
        return;
    }

    // Validate ID format (XXXX-XX)
    const idPattern = /^\d{4}-\d{2}$/;
    if (!idPattern.test(memberId)) {
        errEl.textContent = 'Invalid ID format. Use format: XXXX-XX (e.g., 0123-01)';
        return;
    }

    // Use member ID as password
    const password = memberId;

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
            body: JSON.stringify({
                email,
                password,
                member_id: memberId  // Send the ID separately
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to create account.');
        closeCreateAccountModal();
        await loadMembers();
        showSuccessModal(`Account created! Login with ID: ${memberId}`);
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

// ── Courses Management ────────────────────────────────────────

let coursesData = [];
let facultyData = [];
let currentCategory = 'CERP';
let selectedFacultyId = null;

async function loadCourses() {
    try {
        const res = await fetch('/api/courses');
        if (!res.ok) throw new Error();
        coursesData = await res.json();
        renderCourses();
    } catch (error) {
        console.error('Failed to load courses:', error);
        coursesData = [];
        renderCourses();
    }
}

async function loadFacultyForCourses() {
    try {
        const res = await fetch('/api/members');
        if (!res.ok) throw new Error();
        const allMembers = await res.json();
        // Filter only faculty members
        facultyData = allMembers.filter(m => m.is_faculty === true);
        renderFacultyCards();
    } catch (error) {
        console.error('Failed to load faculty:', error);
        facultyData = [];
        renderFacultyCards();
    }
}

window.switchCourseCategory = function (category, button) {
    currentCategory = category;

    // Update active button
    document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');

    renderCourses();
};

function renderCourses() {
    const container = document.getElementById('courses-list');
    if (!container) return;

    // Filter courses by current category
    const filtered = coursesData.filter(course => {
        const code = course.course_code || '';
        if (currentCategory === 'CERP') {
            return code.startsWith('CERP');
        } else if (currentCategory === 'HUME') {
            return code.startsWith('HUME');
        } else if (currentCategory === 'NSTP') {
            return code.startsWith('NSTP');
        }
        return false;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                <p>No ${currentCategory} courses found</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(course => {
        return `
            <div class="course-block" draggable="true" data-course-id="${course.id}" ondragstart="handleCourseDragStart(event)">
                <div class="course-code">${course.course_code || 'N/A'}</div>
            </div>
        `;
    }).join('');
}

function renderFacultyCards() {
    const container = document.getElementById('faculty-grid');
    if (!container) return;

    if (facultyData.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                </svg>
                <p>No faculty members found</p>
            </div>
        `;
        return;
    }

    container.innerHTML = facultyData.map(faculty => {
        const photoHtml = faculty.photo_url
            ? `<img src="${faculty.photo_url}" class="faculty-photo" alt="${faculty.first}">`
            : `<div class="faculty-avatar">${(faculty.first || 'U')[0].toUpperCase()}</div>`;

        const isExpanded = selectedFacultyId === faculty.id;

        return `
            <div class="faculty-card ${isExpanded ? 'expanded' : ''}" data-faculty-id="${faculty.id}" onclick="toggleFacultyCard('${faculty.id}')">
                <div class="faculty-header">
                    ${photoHtml}
                    <div class="faculty-info">
                        <h3 class="faculty-name">${faculty.first} ${faculty.last}</h3>
                        <p class="faculty-position">${faculty.position || 'Faculty Member'}</p>
                    </div>
                    <svg class="expand-icon" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
                <div class="faculty-courses-area" ondrop="handleCourseDrop(event, '${faculty.id}')" ondragover="handleCourseDragOver(event)">
                    ${isExpanded ? '<div class="loading-courses">Loading courses...</div>' : ''}
                </div>
            </div>
        `;
    }).join('');

    // If a faculty was expanded, reload their courses
    if (selectedFacultyId) {
        loadFacultyCourses(selectedFacultyId);
    }
}

window.toggleFacultyCard = async function (facultyId) {
    if (selectedFacultyId === facultyId) {
        // Collapse
        selectedFacultyId = null;
        renderFacultyCards();
    } else {
        // Expand
        selectedFacultyId = facultyId;
        renderFacultyCards();
    }
};

async function loadFacultyCourses(facultyId) {
    const card = document.querySelector(`.faculty-card[data-faculty-id="${facultyId}"]`);
    if (!card) return;

    const coursesArea = card.querySelector('.faculty-courses-area');

    try {
        const res = await fetch(`/api/faculty/${facultyId}/courses`);
        if (!res.ok) throw new Error();
        const facultyCourses = await res.json();

        if (facultyCourses.length === 0) {
            coursesArea.innerHTML = `
                <div class="empty-courses-message">
                    <p>No courses assigned yet. Drag courses here to assign.</p>
                </div>
            `;
        } else {
            coursesArea.innerHTML = facultyCourses.map(course => `
                <div class="faculty-course-block" data-course-id="${course.id}">
                    <div class="course-code">${course.course_code || 'N/A'}</div>
                    <button class="remove-course-btn" onclick="removeCourseFromFaculty(event, '${facultyId}', '${course.id}')">
                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load faculty courses:', error);
        coursesArea.innerHTML = `
            <div class="empty-courses-message error">
                <p>Failed to load courses. Please try again.</p>
            </div>
        `;
    }
}

// Drag and drop handlers
window.handleCourseDragStart = function (event) {
    const courseId = event.target.dataset.courseId;
    event.dataTransfer.setData('courseId', courseId);
    event.target.classList.add('dragging');
};

window.handleCourseDragOver = function (event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
};

window.handleCourseDrop = async function (event, facultyId) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');

    const courseId = event.dataTransfer.getData('courseId');
    if (!courseId) return;

    // Remove dragging class
    document.querySelectorAll('.course-block.dragging').forEach(el => el.classList.remove('dragging'));

    try {
        const res = await fetch(`/api/faculty/${facultyId}/courses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_id: courseId })
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Failed to assign course');
        }

        // Reload the faculty's courses
        await loadFacultyCourses(facultyId);
        showSuccessModal('Course assigned successfully!');
    } catch (error) {
        alert('Failed to assign course: ' + error.message);
    }
};

window.removeCourseFromFaculty = async function (event, facultyId, courseId) {
    event.stopPropagation();

    try {
        const res = await fetch(`/api/faculty/${facultyId}/courses/${courseId}`, {
            method: 'DELETE'
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Failed to remove course');
        }

        // Reload the faculty's courses
        await loadFacultyCourses(facultyId);
        showSuccessModal('Course removed successfully!');
    } catch (error) {
        alert('Failed to remove course: ' + error.message);
    }
}

// Remove drag-over class when leaving
document.addEventListener('dragleave', function (event) {
    if (event.target.classList.contains('faculty-courses-area')) {
        event.target.classList.remove('drag-over');
    }
});

document.addEventListener('dragend', function (event) {
    document.querySelectorAll('.course-block.dragging').forEach(el => el.classList.remove('dragging'));
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
});

// ── Initialize ────────────────────────────────────────────────

loadMembers();

// Initialize courses page if we're on it
if (document.getElementById('courses-list')) {
    loadCourses();
    loadFacultyForCourses();
}
