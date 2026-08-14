/* ══════════════════════════════════════════════════════════════
   CERP Admin - Teaching Staff JavaScript
   ══════════════════════════════════════════════════════════════ */

// All Subjects by Year and Semester - Only declare if not already defined
if (typeof ALL_SUBJECTS === 'undefined') {
    var ALL_SUBJECTS = {
        '1-1': [ // 1st Year, 1st Semester
            { code: 'HIST/KAS 1', name: 'Philippine History', units: 3 },
            { code: 'ETHICS 1', name: 'Ethics and Moral Reasoning', units: 3 },
            { code: 'HFDS 101', name: 'Family and Environment', units: 3 },
            { code: 'HUME 100', name: 'Introduction to Human Ecology', units: 3 },
            { code: 'CERP 101', name: 'Fundamentals of Human Settlements', units: 3 },
            { code: 'SDS 101', name: 'Introduction to Social Development', units: 3 },
            { code: 'HK 11', name: 'Concept in Wellness and Basic Injury Management', units: 2 }
        ],
        '1-2': [ // 1st Year, 2nd Semester
            { code: 'ARTS 1', name: 'Critical Perspectives in the Arts', units: 3 },
            { code: 'HUME 112', name: 'Sustainability Science', units: 3 },
            { code: 'HUME 107', name: 'Principles of Human Development', units: 3 },
            { code: 'HUME 105', name: 'Humans and their Environment', units: 3 },
            { code: 'SOC 140', name: 'Introduction to Demography', units: 3 },
            { code: 'BIO 150', name: 'Principles of Ecology', units: 4 },
            { code: 'HK 12/13', name: 'Human Kinetics Activities', units: 2 },
            { code: 'NSTP 1', name: 'National Service Training Program 1', units: 3 }
        ],
        '2-1': [ // 2nd Year, 1st Semester
            { code: 'PI 10', name: 'Life and Works of Rizal', units: 3 },
            { code: 'HUME 110', name: 'Ecology and Value Systems', units: 3 },
            { code: 'HUME 111', name: 'Human Ecological Perspective in Development', units: 3 },
            { code: 'HUME 113', name: 'Community Study in Human Welfare', units: 3 },
            { code: 'HK 12 or 13', name: 'Human Kinetics Activities', units: 2 },
            { code: 'NSTP 2', name: 'National Service Training Program 2', units: 3 }
        ],
        '2-2': [ // 2nd Year, 2nd Semester
            { code: 'STS 1', name: 'Science, Technology, and Society', units: 3 },
            { code: 'STAT 166', name: 'Statistics for Social Sciences', units: 3 },
            { code: 'HUME 114', name: 'Material and Energy Flows', units: 3 },
            { code: 'CERP 161', name: 'Planning Theory and Practice I', units: 3 },
            { code: 'HUME 115', name: 'Social Policies', units: 3 },
            { code: 'HK 12 or 13', name: 'Human Kinetics Activities', units: 2 }
        ],
        '3-1': [ // 3rd Year, 1st Semester
            { code: 'COMM 10', name: 'Critical Perspectives in Communication', units: 3 },
            { code: 'HUME 195', name: 'Research Methods in Human Ecology', units: 3 },
            { code: 'HUME 122', name: 'Human Needs and the Built Environment', units: 3 },
            { code: 'HUME 123', name: 'Climate Change Adaptation and Disaster Risk Reduction in Human Ecosystems', units: 3 },
            { code: 'CERP 140', name: 'Fundamentals of Environmental Economics', units: 3 },
            { code: 'CERP 122', name: 'Conservation of Natural Resources', units: 3 },
            { code: 'SDS 172', name: 'Techniques in Community Organizing', units: 3 }
        ],
        '3-2': [ // 3rd Year, 2nd Semester
            { code: 'HUME 125', name: 'Human Ecological Systems Mapping', units: 5 },
            { code: 'HUME 124', name: 'Environmental Health', units: 3 },
            { code: 'SDS 173', name: 'Consumer Education', units: 3 },
            { code: 'HFDS 110', name: 'Migration', units: 3 },
            { code: 'CERP 162', name: 'Planning Theory and Practice II', units: 3 },
            { code: 'CERP 163', name: 'Land Use Planning for Human Settlements', units: 5 },
            { code: 'CERP 165', name: 'Human Settlements Planning I', units: 5 }
        ],
        '4-1': [ // 4th Year, 1st Semester
            { code: 'HNF 141', name: 'Food and Nutrition Systems', units: 3 },
            { code: 'CERP 166', name: 'Human Settlements Planning II', units: 7 },
            { code: 'CERP 170', name: 'Environmental Project Planning & Administration', units: 3 },
            { code: 'CERP 164', name: 'Spatial Analysis & Planning for Human Settlements', units: 5 },
            { code: 'CERP 200', name: 'Undergraduate Thesis', units: 3 }
        ],
        '4-2': [ // 4th Year, 2nd Semester
            { code: 'HUME 200a', name: 'Supervised Field Experience', units: 6 },
            { code: 'HUME 199', name: 'Seminar in Human Ecology', units: 1 },
            { code: 'CERP 200', name: 'Undergraduate Thesis', units: 3 }
        ]
    };
}

// Only declare if not already defined
if (typeof staffData === 'undefined') var staffData = [];
if (typeof selectedSubjects === 'undefined') var selectedSubjects = [];
if (typeof editingStaffId === 'undefined') var editingStaffId = null;
if (typeof deleteStaffId === 'undefined') var deleteStaffId = null;
if (typeof currentStaffYear === 'undefined') var currentStaffYear = '';
if (typeof currentStaffSemester === 'undefined') var currentStaffSemester = '1';
if (typeof isSubmitting === 'undefined') var isSubmitting = false;
if (typeof viewingStaffId === 'undefined') var viewingStaffId = null;

// ── Load Staff ────────────────────────────────────────────────

async function loadStaff() {
    console.log('Loading staff...');
    try {
        const res = await fetch('/api/staff');
        console.log('Staff API response:', res.status);
        if (!res.ok) throw new Error('Failed to fetch staff');
        staffData = await res.json();
        console.log('Staff data loaded:', staffData.length, 'items');
    } catch (error) {
        console.error('Error loading staff:', error);
        staffData = [];
    }
    renderStaff();
    console.log('Staff rendered');
}

function renderStaff() {
    console.log('Rendering staff, count:', staffData.length);
    const grid = document.getElementById('staff-grid');
    if (!grid) {
        console.error('staff-grid element not found!');
        return;
    }

    if (!staffData.length) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #9ca3af;">
                <svg width="64" height="64" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="margin: 0 auto 16px; opacity: 0.3;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <p style="font-size: 0.9rem; font-weight: 500;">No faculty added yet</p>
                <p style="font-size: 0.8rem; margin-top: 4px;">Click "Add Faculty" to get started</p>
            </div>
        `;
        console.log('Rendered empty state');
        return;
    }

    // Render staff cards directly without year grouping
    let html = '';
    staffData.forEach(staff => {
        const photoHtml = staff.photo_url
            ? `<img src="${staff.photo_url}" class="staff-photo" alt="${staff.fullName}">`
            : `<div class="staff-photo-placeholder">${staff.fullName.charAt(0).toUpperCase()}</div>`;

        html += `
            <div class="staff-card" oncontextmenu="openStaffDetails('${staff.id}', event)">
                <div class="staff-photo-container">
                    ${photoHtml}
                </div>
                <div class="staff-name">${staff.fullName}</div>
            </div>
        `;
    });

    grid.innerHTML = html;
}

// ── Add Staff Modal ───────────────────────────────────────────

window.openAddStaffModal = function () {
    selectedSubjects = [];
    currentStaffYear = '';

    // Uncheck all year level checkboxes
    document.querySelectorAll('input[name="yearLevel"]').forEach(cb => cb.checked = false);

    document.getElementById('add-staff-modal').classList.add('open');
    document.getElementById('subject-chips').innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select at least one year level</div>';
};

window.closeAddStaffModal = function () {
    document.getElementById('add-staff-modal').classList.remove('open');
    resetAddStaffForm();
};

function resetAddStaffForm() {
    document.getElementById('add-staff-form').reset();
    document.getElementById('staff-photo-preview').classList.remove('show');
    document.getElementById('add-staff-error').textContent = '';
    selectedSubjects = [];
    currentStaffYear = '';
    document.getElementById('subject-chips').innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select at least one year level</div>';
}

// Handle multiple year level checkboxes
window.onStaffYearCheckChange = function (mode) {
    const containerId = mode === 'add' ? 'subject-chips' : 'edit-subject-chips';
    const checkboxes = document.querySelectorAll(`input[name="yearLevel"]:checked`);

    // Get all selected years
    const selectedYears = Array.from(checkboxes).map(cb => cb.value);

    // Reset selected subjects when year selection changes
    selectedSubjects = [];

    if (selectedYears.length === 0) {
        document.getElementById(containerId).innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select at least one year level</div>';
        return;
    }

    renderSubjectChipsMultiYear(containerId, selectedYears);
};

function renderSubjectChipsMultiYear(containerId, years) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';

    // For each selected year, show subjects grouped by semester
    years.sort().forEach(year => {
        const sem1Key = year + '-1';
        const sem2Key = year + '-2';
        const sem1Subjects = ALL_SUBJECTS[sem1Key] || [];
        const sem2Subjects = ALL_SUBJECTS[sem2Key] || [];

        // Year header - standalone div outside grid
        html += `
            <div style="font-weight:700;color:#6b0f1a;font-size:0.85rem;margin-top:${years[0] === year ? '0' : '24px'};margin-bottom:4px;border-bottom:2px solid #6b0f1a;padding-bottom:4px;">
                ${year}${['st', 'nd', 'rd', 'th'][year - 1]} Year
            </div>
        `;

        // 1st Semester - directly under year header
        if (sem1Subjects.length > 0) {
            html += '<div style="font-size:0.75rem;font-weight:600;color:#6b7280;margin-top:12px;margin-bottom:10px;">1st Semester</div>';
            html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px;">';
            sem1Subjects.forEach(subj => {
                const isSelected = selectedSubjects.some(s => s.code === subj.code);
                html += `<div class="subject-chip ${isSelected ? 'selected' : ''}" onclick="toggleSubject('${subj.code}', '${subj.name}', ${subj.units})">
                    <span class="subject-chip-code">${subj.code}</span>
                    <span class="subject-chip-name">${subj.name}</span>
                    <span class="subject-chip-units">${subj.units} ${subj.units === 1 ? 'unit' : 'units'}</span>
                </div>`;
            });
            html += '</div>';
        }

        // 2nd Semester
        if (sem2Subjects.length > 0) {
            html += '<div style="font-size:0.75rem;font-weight:600;color:#6b7280;margin-top:4px;margin-bottom:10px;">2nd Semester</div>';
            html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px;">';
            sem2Subjects.forEach(subj => {
                const isSelected = selectedSubjects.some(s => s.code === subj.code);
                html += `<div class="subject-chip ${isSelected ? 'selected' : ''}" onclick="toggleSubject('${subj.code}', '${subj.name}', ${subj.units})">
                    <span class="subject-chip-code">${subj.code}</span>
                    <span class="subject-chip-name">${subj.name}</span>
                    <span class="subject-chip-units">${subj.units} ${subj.units === 1 ? 'unit' : 'units'}</span>
                </div>`;
            });
            html += '</div>';
        }
    });

    container.innerHTML = html;
}

// Legacy function - kept for compatibility but not used with new multi-select
window.onStaffYearChange = function (mode) {
    const yearSelect = document.getElementById(mode === 'add' ? 'staff-year-select' : 'edit-staff-year-select');
    const containerId = mode === 'add' ? 'subject-chips' : 'edit-subject-chips';

    if (!yearSelect) return;

    currentStaffYear = yearSelect.value;
    selectedSubjects = []; // Reset selected subjects when year changes

    if (!currentStaffYear) {
        document.getElementById(containerId).innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select a year level first</div>';
        return;
    }

    renderSubjectChips(containerId);
};

function previewStaffPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('staff-photo-preview');
            preview.src = e.target.result;
            preview.classList.add('show');
        };
        reader.readAsDataURL(file);
    }
}

function renderSubjectChips(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!currentStaffYear) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select a year level first</div>';
        return;
    }

    // Get subjects for both semesters of the selected year
    const sem1Key = currentStaffYear + '-1';
    const sem2Key = currentStaffYear + '-2';
    const sem1Subjects = ALL_SUBJECTS[sem1Key] || [];
    const sem2Subjects = ALL_SUBJECTS[sem2Key] || [];

    let html = '';

    if (sem1Subjects.length > 0) {
        html += '<div style="width:100%;font-size:0.75rem;font-weight:700;color:#6b0f1a;margin:8px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">1st Semester</div>';
        html += sem1Subjects.map(subject => {
            const isSelected = selectedSubjects.some(s => s.code === subject.code);
            return `
                <div class="subject-chip ${isSelected ? 'selected' : ''}" 
                     onclick="toggleSubject('${subject.code}', '${containerId}')">
                    <div class="subject-chip-code">${subject.code}</div>
                    <div class="subject-chip-name">${subject.name}</div>
                    <div class="subject-chip-units">${subject.units} ${subject.units === 1 ? 'unit' : 'units'}</div>
                </div>
            `;
        }).join('');
    }

    if (sem2Subjects.length > 0) {
        html += '<div style="width:100%;font-size:0.75rem;font-weight:700;color:#6b0f1a;margin:16px 0 8px;text-transform:uppercase;letter-spacing:0.05em;">2nd Semester</div>';
        html += sem2Subjects.map(subject => {
            const isSelected = selectedSubjects.some(s => s.code === subject.code);
            return `
                <div class="subject-chip ${isSelected ? 'selected' : ''}" 
                     onclick="toggleSubject('${subject.code}', '${containerId}')">
                    <div class="subject-chip-code">${subject.code}</div>
                    <div class="subject-chip-name">${subject.name}</div>
                    <div class="subject-chip-units">${subject.units} ${subject.units === 1 ? 'unit' : 'units'}</div>
                </div>
            `;
        }).join('');
    }

    if (html === '') {
        html = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">No subjects available for this year</div>';
    }

    container.innerHTML = html;
}

window.toggleSubject = function (code, name, units) {
    // Create subject object
    const subject = { code, name, units };

    const index = selectedSubjects.findIndex(s => s.code === code);
    if (index > -1) {
        selectedSubjects.splice(index, 1);
    } else {
        selectedSubjects.push(subject);
    }

    // Re-render the chips for the current mode
    const checkboxes = document.querySelectorAll('input[name="yearLevel"]:checked');
    const selectedYears = Array.from(checkboxes).map(cb => cb.value);

    // Determine which container to update based on which modal is open
    const addModalOpen = document.getElementById('add-staff-modal').classList.contains('open');
    const editModalOpen = document.getElementById('edit-staff-modal').classList.contains('open');

    if (addModalOpen && selectedYears.length > 0) {
        renderSubjectChipsMultiYear('subject-chips', selectedYears);
    } else if (editModalOpen && selectedYears.length > 0) {
        renderSubjectChipsMultiYear('edit-subject-chips', selectedYears);
    }
};

async function submitAddStaff(event) {
    event.preventDefault();

    if (isSubmitting) return; // Prevent duplicate submissions

    const errEl = document.getElementById('add-staff-error');
    errEl.textContent = '';

    // REMOVED: Subject validation - no longer required
    // All faculty can teach any subject
    // if (selectedSubjects.length === 0) {
    //     errEl.textContent = 'Please select at least one subject.';
    //     return;
    // }

    const form = event.target;

    // Get availability checkboxes
    const availabilityCheckboxes = form.querySelectorAll('input[name="availability"]:checked');
    const availability = Array.from(availabilityCheckboxes).map(cb => cb.value);

    if (availability.length === 0) {
        errEl.textContent = 'Please select at least one day availability.';
        return;
    }

    // Get year level checkboxes
    const yearCheckboxes = form.querySelectorAll('input[name="yearLevel"]:checked');
    const years = Array.from(yearCheckboxes).map(cb => cb.value);

    if (years.length === 0) {
        errEl.textContent = 'Please select at least one year level.';
        return;
    }

    // Show confirmation modal
    showConfirmStaffModal(form, availability, years);
}

function showConfirmStaffModal(form, availability, years) {
    const fullName = form.querySelector('#staff-fullname').value;

    // Populate confirmation modal
    document.getElementById('confirm-fullname').textContent = fullName;

    // Availability chips
    document.getElementById('confirm-availability').innerHTML = availability.map(day =>
        `<span style="padding:4px 10px;background:transparent;color:#6b0f1a;border:1.5px solid #6b0f1a;border-radius:6px;font-size:0.75rem;font-weight:600;">${day}</span>`
    ).join('');

    // Year levels
    const yearLabels = years.map(y => ['1st', '2nd', '3rd', '4th'][parseInt(y) - 1] + ' Year');
    document.getElementById('confirm-years').innerHTML = yearLabels.map(label =>
        `<span style="padding:4px 10px;background:transparent;color:#6b0f1a;border:1.5px solid #6b0f1a;border-radius:6px;font-size:0.75rem;font-weight:600;">${label}</span>`
    ).join('');

    // Subjects (now optional)
    const subjectContainer = document.getElementById('confirm-subjects');
    if (selectedSubjects.length > 0) {
        subjectContainer.innerHTML = selectedSubjects.map(s =>
            `<span style="padding:4px 10px;background:transparent;color:#6b0f1a;border:1.5px solid #6b0f1a;border-radius:6px;font-size:0.75rem;font-weight:600;">${s.code}</span>`
        ).join('');
    } else {
        subjectContainer.innerHTML = '<span style="color:#9ca3af;font-size:0.8rem;">No subjects selected (can teach any subject)</span>';
    }

    // Open confirmation modal
    document.getElementById('confirm-staff-modal').classList.add('open');
}

window.closeConfirmStaffModal = function () {
    document.getElementById('confirm-staff-modal').classList.remove('open');
};

window.confirmAddStaff = async function () {
    const form = document.getElementById('add-staff-form');
    const errEl = document.getElementById('add-staff-error');

    // Get availability checkboxes
    const availabilityCheckboxes = form.querySelectorAll('input[name="availability"]:checked');
    const availability = Array.from(availabilityCheckboxes).map(cb => cb.value);

    // Create FormData manually to avoid conflicts
    const fd = new FormData();

    // Add form fields
    fd.append('fullName', form.querySelector('#staff-fullname').value);
    fd.append('subjects', JSON.stringify(selectedSubjects));
    fd.append('availability', JSON.stringify(availability));

    // Add photo
    const photoInput = document.getElementById('staff-photo-input');
    const photo = photoInput.files[0];
    if (photo) fd.append('photo', photo);

    // Debug: Log what we're sending
    console.log('Sending data:', {
        fullName: form.querySelector('#staff-fullname').value,
        subjects: selectedSubjects,
        availability: availability
    });

    isSubmitting = true; // Set flag

    // Show loading state on button
    const submitBtn = document.querySelector('#confirm-staff-modal .btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.classList.add('btn-loading');
    submitBtn.textContent = 'Adding...';

    try {
        const res = await fetch('/api/staff', { method: 'POST', body: fd });

        // Check if response is JSON
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await res.text();
            throw new Error(`Server error: ${text.substring(0, 100)}`);
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add staff.');

        closeConfirmStaffModal();
        closeAddStaffModal();
        resetAddStaffForm();
        await loadStaff();

        // Show success modal
        showSuccessModal('Faculty member added successfully!');
    } catch (e) {
        errEl.textContent = e.message;
        console.error('Add staff error:', e);
        closeConfirmStaffModal(); // Close confirmation to show error
    } finally {
        isSubmitting = false; // Reset flag
        submitBtn.classList.remove('btn-loading');
        submitBtn.textContent = originalText;
    }
};

// ── Edit Staff Modal ──────────────────────────────────────────

function openEditStaffModal(staffId) {
    editingStaffId = staffId;
    const staff = staffData.find(s => s.id === staffId);
    if (!staff) return;

    // Set form values
    document.getElementById('edit-staff-fullname').value = staff.fullName;

    // Set availability checkboxes
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.forEach(day => {
        const checkbox = document.getElementById(`edit-avail-${day.toLowerCase()}`);
        if (checkbox) {
            checkbox.checked = staff.availability && staff.availability.includes(day);
        }
    });

    // Set photo preview
    const preview = document.getElementById('edit-staff-photo-preview');
    if (staff.photo_url) {
        preview.src = staff.photo_url;
        preview.classList.add('show');
    } else {
        preview.classList.remove('show');
    }

    // Determine year from subjects (use first subject's year if available)
    if (staff.subjects && staff.subjects.length > 0) {
        // Find which year/semester this subject belongs to
        let foundYear = '';
        for (const key in ALL_SUBJECTS) {
            if (ALL_SUBJECTS[key].some(s => s.code === staff.subjects[0].code)) {
                foundYear = key.split('-')[0];
                break;
            }
        }
        currentStaffYear = foundYear || '1';
    } else {
        currentStaffYear = '1';
    }

    document.getElementById('edit-staff-year-select').value = currentStaffYear;

    // Set selected subjects
    selectedSubjects = [...staff.subjects];
    renderSubjectChips('edit-subject-chips');

    document.getElementById('edit-staff-modal').classList.add('open');
}

function closeEditStaffModal() {
    document.getElementById('edit-staff-modal').classList.remove('open');
    editingStaffId = null;
    selectedSubjects = [];
}

function previewEditStaffPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('edit-staff-photo-preview');
            preview.src = e.target.result;
            preview.classList.add('show');
        };
        reader.readAsDataURL(file);
    }
}

async function submitEditStaff(event) {
    event.preventDefault();
    const errEl = document.getElementById('edit-staff-error');
    errEl.textContent = '';

    if (selectedSubjects.length === 0) {
        errEl.textContent = 'Please select at least one subject.';
        return;
    }

    const form = event.target;

    // Get availability checkboxes
    const availabilityCheckboxes = form.querySelectorAll('input[name="availability"]:checked');
    const availability = Array.from(availabilityCheckboxes).map(cb => cb.value);

    if (availability.length === 0) {
        errEl.textContent = 'Please select at least one day availability.';
        return;
    }

    // Create FormData manually
    const fd = new FormData();

    // Add form fields
    fd.append('fullName', form.querySelector('#edit-staff-fullname').value);
    fd.append('subjects', JSON.stringify(selectedSubjects));
    fd.append('availability', JSON.stringify(availability));

    // Add photo if changed
    const photoInput = document.getElementById('edit-staff-photo-input');
    const photo = photoInput.files[0];
    if (photo) fd.append('photo', photo);

    try {
        const res = await fetch(`/api/staff/${editingStaffId}`, { method: 'PUT', body: fd });

        // Check if response is JSON
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await res.text();
            throw new Error(`Server error: ${text.substring(0, 100)}`);
        }

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to update staff.');
        closeEditStaffModal();
        await loadStaff();
    } catch (e) {
        errEl.textContent = e.message;
        console.error('Edit staff error:', e);
    }
}

// ── Delete Staff Modal ────────────────────────────────────────

function openDeleteStaffModal(staffId) {
    deleteStaffId = staffId;
    document.getElementById('delete-staff-modal').classList.add('open');
}

function closeDeleteStaffModal() {
    document.getElementById('delete-staff-modal').classList.remove('open');
    deleteStaffId = null;
}

async function confirmDeleteStaff() {
    if (isSubmitting) return; // Prevent duplicate submissions
    isSubmitting = true;

    try {
        const res = await fetch(`/api/staff/${deleteStaffId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        closeDeleteStaffModal();
        await loadStaff();
        showSuccessModal('Staff member deleted successfully!');
    } catch {
        alert('Failed to delete staff. Please try again.');
    } finally {
        isSubmitting = false;
    }
}

// ── Staff Details - Navigate to Detail Page (Right-click) ─────

window.openStaffDetails = function (staffId, event) {
    event.preventDefault(); // Prevent default context menu

    const staff = staffData.find(s => s.id === staffId);
    if (!staff) return;

    // Navigate to faculty detail page using memberId
    if (staff.memberId) {
        window.location.href = `/dashboard/faculty/${staff.memberId}`;
    } else {
        console.error('Staff member has no memberId:', staff);
        alert('Unable to view details: memberId not found');
    }
};

// ── Success Modal ─────────────────────────────────────────────

function showSuccessModal(message) {
    document.getElementById('success-message').textContent = message;
    document.getElementById('success-modal').classList.add('open');
}

window.closeSuccessModal = function () {
    document.getElementById('success-modal').classList.remove('open');
};

// ── Initialize ────────────────────────────────────────────────

loadStaff();
