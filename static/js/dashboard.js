/* ══════════════════════════════════════════════════════════════
   CERP Admin - Dashboard Page JavaScript
   ══════════════════════════════════════════════════════════════ */

let pubChart = null;
let tapChartInst = null;

const pubData = {
    'this': [5, 7, 4, 8, 6, 9, 7, 10, 5, 8, 6, 9],
    2025: [5, 7, 4, 8, 6, 9, 7, 10, 5, 8, 6, 9],
    2024: [4, 6, 3, 7, 5, 8, 6, 9, 4, 7, 5, 8],
    2023: [3, 5, 2, 4, 6, 3, 7, 4, 5, 3, 6, 4],
};

const pubPrevYear = { 'this': 2024, 2025: 2024, 2024: 2023, 2023: 2022 };
const pubData2022 = [2, 4, 1, 3, 5, 2, 6, 3, 4, 2, 5, 3];

// TAP data: [ongoing, finished, pending] per year
const tapDataByYear = {
    2025: [18, 12, 6],
    2024: [15, 10, 8],
    2023: [12, 8, 5],
    2022: [10, 6, 4],
};
let tapYear = 2025;
let pubYear = 'this';

function getPrevData(y) {
    const prev = pubPrevYear[y];
    return pubData[prev] || pubData2022;
}

function getYearLabel(y) {
    return y === 'this' ? 'This Year' : String(y);
}

function getPrevLabel(y) {
    const prev = pubPrevYear[y];
    return prev ? String(prev) : '—';
}

function initCharts() {
    if (pubChart) {
        pubChart.destroy();
        pubChart = null;
    }
    if (tapChartInst) {
        tapChartInst.destroy();
        tapChartInst = null;
    }

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    // ── Line chart ──
    const pubCtx = document.getElementById('publicationsChart');
    if (pubCtx) {
        pubChart = new Chart(pubCtx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: getYearLabel(pubYear),
                        data: pubData[pubYear],
                        borderColor: '#fb923c',
                        backgroundColor: 'transparent',
                        borderWidth: 2.5,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#fb923c',
                        pointBorderWidth: 2.5,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointHoverBorderWidth: 3,
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#fb923c',
                        fill: false,
                        tension: 0.4,
                        spanGaps: false,
                    },
                    {
                        label: getPrevLabel(pubYear),
                        data: getPrevData(pubYear),
                        borderColor: '#d1d5db',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [8, 4],
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#d1d5db',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointHoverBorderWidth: 2.5,
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#d1d5db',
                        fill: false,
                        tension: 0.4,
                        spanGaps: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.85)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 13, weight: '600' },
                        bodyFont: { size: 12 },
                        displayColors: true,
                        boxWidth: 8,
                        boxHeight: 8,
                        boxPadding: 6,
                        callbacks: {
                            title: items => months[items[0].dataIndex],
                            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} publications`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        position: 'left',
                        grid: {
                            color: '#f3f4f6',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            font: { size: 11, weight: '500' },
                            stepSize: 2,
                            padding: 10,
                            color: '#6b7280'
                        },
                        border: {
                            display: false
                        }
                    },
                    x: {
                        position: 'bottom',
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: { size: 11, weight: '500' },
                            padding: 8,
                            color: '#6b7280'
                        },
                        border: {
                            display: false
                        }
                    }
                },
                elements: {
                    line: {
                        borderJoinStyle: 'round',
                        borderCapStyle: 'round'
                    }
                }
            }
        });
    }

    // ── Pie chart ──
    const tapCtx = document.getElementById('tapChart');
    if (tapCtx) {
        const [ongoing, finished, pending] = tapDataByYear[tapYear];

        // Update legend counts
        document.getElementById('tap-ongoing-count').textContent = ongoing;
        document.getElementById('tap-finished-count').textContent = finished;
        document.getElementById('tap-pending-count').textContent = pending;

        tapChartInst = new Chart(tapCtx, {
            type: 'pie',
            data: {
                labels: ['Ongoing', 'Finished', 'Pending'],
                datasets: [{
                    data: [ongoing, finished, pending],
                    backgroundColor: ['#fb923c', '#fbbf24', '#fde047'],
                    borderColor: ['#fff', '#fff', '#fff'],
                    borderWidth: 2,
                    hoverOffset: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.85)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 13, weight: '600' },
                        bodyFont: { size: 12 },
                        callbacks: {
                            label: ctx => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = ((ctx.raw / total) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                            }
                        }
                    }
                },
                onHover: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const index = activeElements[0].index;
                        const meta = tapChartInst.getDatasetMeta(0);

                        // Dim all segments except the hovered one
                        meta.data.forEach((segment, i) => {
                            if (i === index) {
                                segment.options.backgroundColor = ['#fb923c', '#fbbf24', '#fde047'][i];
                            } else {
                                segment.options.backgroundColor = ['rgba(251, 146, 60, 0.3)', 'rgba(251, 191, 36, 0.3)', 'rgba(253, 224, 71, 0.3)'][i];
                            }
                        });
                        tapChartInst.update('none');
                    } else {
                        // Reset all segments to original colors
                        const meta = tapChartInst.getDatasetMeta(0);
                        meta.data.forEach((segment, i) => {
                            segment.options.backgroundColor = ['#fb923c', '#fbbf24', '#fde047'][i];
                        });
                        tapChartInst.update('none');
                    }
                }
            }
        });
    }

    // Build pub year dropdown
    buildYearDropdown('pub', ['this', 2025, 2024, 2023], pubYear, y => {
        pubYear = y;
        const curLabel = getYearLabel(y);
        const prevLabel = getPrevLabel(y);
        document.getElementById('pub-year-label').textContent = curLabel;
        document.getElementById('pub-prev-year-label').textContent = prevLabel;
        document.getElementById('pub-year-btn-label').textContent = curLabel;
        document.getElementById('pub-legend-current').textContent = curLabel;
        document.getElementById('pub-legend-prev').textContent = prevLabel;

        if (pubChart) {
            pubChart.data.datasets[0].label = curLabel;
            pubChart.data.datasets[0].data = pubData[y];
            pubChart.data.datasets[1].label = prevLabel;
            pubChart.data.datasets[1].data = getPrevData(y);
            pubChart.update();
        }
    });

    // Build TAP year dropdown
    buildYearDropdown('tap', [2025, 2024, 2023, 2022], tapYear, y => {
        tapYear = y;
        document.getElementById('tap-year-label').textContent = String(y);

        const [ongoing, finished, pending] = tapDataByYear[y];
        document.getElementById('tap-ongoing-count').textContent = ongoing;
        document.getElementById('tap-finished-count').textContent = finished;
        document.getElementById('tap-pending-count').textContent = pending;

        if (tapChartInst) {
            tapChartInst.data.datasets[0].data = [ongoing, finished, pending];
            tapChartInst.update();
        }
    });
}

function buildYearDropdown(prefix, years, current, onChange) {
    const dropdown = document.getElementById(`${prefix}-year-dropdown`);
    if (!dropdown) return;

    dropdown.innerHTML = years.map(y => {
        const label = y === 'this' ? 'This Year' : String(y);
        return `<div class="year-option" onclick="selectYear('${prefix}', '${y}')">${label}</div>`;
    }).join('');

    window[`selectYear_${prefix}`] = function (y) {
        onChange(y);
        dropdown.classList.remove('open');
    };

    window.selectYear = function (prefix, y) {
        window[`selectYear_${prefix}`](y);
    };
}

function toggleYearDropdown(prefix) {
    const dropdown = document.getElementById(`${prefix}-year-dropdown`);
    if (dropdown) {
        dropdown.classList.toggle('open');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.year-selector')) {
        document.querySelectorAll('.year-dropdown').forEach(d => d.classList.remove('open'));
    }
});

// Initialize charts on load
initCharts();

// ── Staff Management ──────────────────────────────────────────

let facultyMembers = [];
let currentStaffPhoto = null;
let selectedMemberId = null;

async function loadFacultyMembers() {
    try {
        console.log('Fetching faculty members...');
        const res = await fetch('/api/members?faculty=true');
        if (!res.ok) {
            const errorText = await res.text();
            console.error('Failed to fetch faculty members:', res.status, errorText);
            throw new Error(errorText);
        }
        facultyMembers = await res.json();
        console.log('Faculty members loaded:', facultyMembers.length, facultyMembers);
    } catch (error) {
        console.error('Error loading faculty members:', error);
        facultyMembers = [];
    }
}

function openAddStaffModal() {
    document.getElementById('add-staff-modal').classList.add('open');
    loadFacultyMembers().then(() => {
        populateFacultyDropdown();
    });
}

function closeAddStaffModal() {
    document.getElementById('add-staff-modal').classList.remove('open');
    resetAddStaffForm();
}

function resetAddStaffForm() {
    document.getElementById('add-staff-form').reset();
    document.getElementById('staff-photo-preview').classList.remove('show');
    document.getElementById('staff-fullname-group').style.display = 'none';
    document.getElementById('staff-availability-group').style.display = 'none';
    document.getElementById('subject-chips').innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select a year level first</div>';
    currentStaffPhoto = null;
    selectedMemberId = null;
}

function populateFacultyDropdown() {
    const select = document.getElementById('staff-member-select');
    if (!select) {
        console.error('staff-member-select element not found!');
        return;
    }

    console.log('Populating dropdown with', facultyMembers.length, 'members');

    // Clear existing options except the first
    select.innerHTML = '<option value="">-- Select a faculty member --</option>';

    // Populate with faculty members
    facultyMembers.forEach(member => {
        const name = `${member.first} ${member.last}`;
        console.log('Adding member to dropdown:', name, member);
        const option = document.createElement('option');
        option.value = member.id;
        option.textContent = name;
        option.dataset.member = JSON.stringify(member);
        select.appendChild(option);
    });

    console.log('Dropdown populated with', select.options.length - 1, 'options');
}

function onFacultyMemberChange() {
    const select = document.getElementById('staff-member-select');
    const selectedOption = select.options[select.selectedIndex];

    if (!selectedOption.value) {
        // Reset form
        document.getElementById('staff-fullname-group').style.display = 'none';
        document.getElementById('staff-availability-group').style.display = 'none';
        document.getElementById('staff-photo-preview').classList.remove('show');
        currentStaffPhoto = null;
        selectedMemberId = null;
        return;
    }

    // Get member data
    const member = JSON.parse(selectedOption.dataset.member);
    selectedMemberId = member.id;

    // Auto-fill full name
    const fullName = `${member.first} ${member.last}`;
    document.getElementById('staff-fullname').value = fullName;
    document.getElementById('staff-fullname-group').style.display = 'block';

    // Auto-fill photo
    if (member.photo_url) {
        document.getElementById('staff-photo-preview').src = member.photo_url;
        document.getElementById('staff-photo-preview').classList.add('show');
        currentStaffPhoto = member.photo_url;
    } else {
        document.getElementById('staff-photo-preview').classList.remove('show');
        currentStaffPhoto = null;
    }

    // Auto-fill availability
    document.getElementById('staff-availability-group').style.display = 'block';
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.forEach(day => {
        const checkbox = document.getElementById(`staff-avail-${day.toLowerCase()}`);
        if (checkbox) {
            checkbox.checked = member.availability && member.availability.includes(day);
        }
    });
}

function previewStaffPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('staff-photo-preview').src = e.target.result;
            document.getElementById('staff-photo-preview').classList.add('show');
            currentStaffPhoto = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

async function submitAddStaff(event) {
    event.preventDefault();
    const errEl = document.getElementById('add-staff-error');
    errEl.textContent = '';

    if (!selectedMemberId) {
        errEl.textContent = 'Please select a faculty member.';
        return;
    }

    const form = event.target;

    // Get year levels
    const yearLevels = Array.from(form.querySelectorAll('input[name="yearLevel"]:checked'))
        .map(cb => cb.value);

    if (!yearLevels.length) {
        errEl.textContent = 'Please select at least one year level.';
        return;
    }

    // Get subjects (OPTIONAL - no longer required)
    const subjects = Array.from(document.querySelectorAll('#subject-chips .subject-chip.selected'))
        .map(chip => ({
            code: chip.dataset.code,
            name: chip.dataset.name,
            year: chip.dataset.year
        }));

    // REMOVED: Subject validation - no longer required
    // All faculty can teach any subject

    // Get availability from the member (already checked and disabled)
    const availability = Array.from(form.querySelectorAll('input[name="availability"]:checked'))
        .map(cb => cb.value);

    // Get the selected member
    const member = facultyMembers.find(m => m.id === selectedMemberId);
    if (!member) {
        errEl.textContent = 'Selected member not found.';
        return;
    }

    const fullName = `${member.first} ${member.last}`;

    // Prepare form data
    const fd = new FormData();
    fd.append('memberId', selectedMemberId);
    fd.append('fullName', fullName);
    fd.append('subjects', JSON.stringify(subjects)); // Empty array is now allowed
    fd.append('availability', JSON.stringify(availability));

    // Photo is already from member, no need to upload new one unless explicitly changed
    // For now, we'll use the member's photo_url directly in the backend

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    const originalHeight = submitBtn.offsetHeight + 'px';
    submitBtn.style.height = originalHeight;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="spinner-ring" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

    try {
        const res = await fetch('/api/staff', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add faculty.');

        closeAddStaffModal();
        await loadStaff(); // Reload staff grid
        showSuccessModal('Faculty added successfully!');
    } catch (e) {
        errEl.textContent = e.message;
        submitBtn.disabled = false;
        submitBtn.style.height = '';
        submitBtn.textContent = originalText;
    }
}

// ── Staff Loading & Display ──────────────────────────────────

async function loadStaff() {
    const grid = document.getElementById('staff-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="content-spinner"><div class="spinner-ring"></div> Loading staff…</div>';

    try {
        const res = await fetch('/api/staff');
        if (!res.ok) throw new Error();
        const staff = await res.json();
        renderStaffGrid(staff);
    } catch {
        grid.innerHTML = '<div style="text-align:center;padding:40px;color:#9ca3af;">Failed to load staff.</div>';
    }
}

function renderStaffGrid(staff) {
    const grid = document.getElementById('staff-grid');
    if (!grid) return;

    if (!staff.length) {
        grid.innerHTML = '<div style="text-align:center;padding:40px;color:#9ca3af;">No faculty members yet. Add members and check "Teaching Personnel" in the Manage page.</div>';
        return;
    }

    console.log('✅ Rendering', staff.length, 'faculty members');

    let html = '';
    staff.forEach(s => {
        const initial = (s.fullName || 'U')[0].toUpperCase();
        const photoHtml = s.photo_url
            ? `<img src="${s.photo_url}" class="staff-photo" alt="${s.fullName}">`
            : `<div class="staff-photo-placeholder">${initial}</div>`;

        // Sample data for now - will be replaced with real backend data later
        const extensionCount = Math.floor(Math.random() * 10) + 1;
        const researchCount = Math.floor(Math.random() * 8) + 1;

        html += `
            <div class="staff-card" data-staff-id="${s.id}" onclick="toggleStaffSelection(event, '${s.id}')">
                <input type="checkbox" class="staff-card-checkbox" data-staff-id="${s.id}" onclick="toggleStaffCheckbox(event, '${s.id}')">
                <div class="staff-photo-container">
                    ${photoHtml}
                </div>
                <div class="staff-name-container">
                    <div class="staff-name">${s.fullName}</div>
                    <div class="staff-stats">
                        <div class="staff-stat-item">
                            <span class="staff-stat-label">
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                                </svg>
                                Extensions
                            </span>
                            <span class="staff-stat-value">${extensionCount}</span>
                        </div>
                        <div class="staff-stat-item">
                            <span class="staff-stat-label">
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                </svg>
                                Research
                            </span>
                            <span class="staff-stat-value">${researchCount}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    grid.innerHTML = html;
}

// Track selected staff for deletion
let selectedStaffIds = new Set();

function toggleStaffCheckbox(event, staffId) {
    event.stopPropagation();
    const checkbox = event.target;
    const card = document.querySelector(`.staff-card[data-staff-id="${staffId}"]`);

    if (checkbox.checked) {
        selectedStaffIds.add(staffId);
        card.classList.add('selected');
    } else {
        selectedStaffIds.delete(staffId);
        card.classList.remove('selected');
    }

    updateBulkDeleteButton();
}

function toggleStaffSelection(event, staffId) {
    // Don't toggle if clicking the checkbox directly
    if (event.target.classList.contains('staff-card-checkbox')) {
        return;
    }

    const checkbox = document.querySelector(`.staff-card-checkbox[data-staff-id="${staffId}"]`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        toggleStaffCheckbox({ target: checkbox, stopPropagation: () => { } }, staffId);
    }
}

function updateBulkDeleteButton() {
    const deleteBtn = document.getElementById('bulk-delete-btn');
    if (deleteBtn) {
        if (selectedStaffIds.size > 0) {
            deleteBtn.style.display = 'flex';
        } else {
            deleteBtn.style.display = 'none';
        }
    }
}

function confirmBulkDeleteStaff() {
    if (selectedStaffIds.size === 0) return;

    document.getElementById('delete-count').textContent = selectedStaffIds.size;
    document.getElementById('bulk-delete-modal').classList.add('open');
}

function closeBulkDeleteModal() {
    document.getElementById('bulk-delete-modal').classList.remove('open');
}

async function executeBulkDelete() {
    const deleteBtn = document.querySelector('#bulk-delete-modal .btn-danger');
    const originalText = deleteBtn.textContent;
    deleteBtn.disabled = true;
    deleteBtn.textContent = 'Deleting...';

    try {
        const deletePromises = Array.from(selectedStaffIds).map(id =>
            fetch(`/api/staff/${id}`, { method: 'DELETE' })
        );

        await Promise.all(deletePromises);

        closeBulkDeleteModal();
        selectedStaffIds.clear();
        await loadStaff();
        updateBulkDeleteButton();
        showSuccessModal(`${deletePromises.length} faculty member(s) deleted successfully!`);
    } catch (error) {
        alert('Failed to delete some faculty members. Please try again.');
        deleteBtn.disabled = false;
        deleteBtn.textContent = originalText;
    }
}

// Load staff on page load
if (document.getElementById('staff-grid')) {
    loadStaff();
}

function showSuccessModal(message) {
    const modal = document.getElementById('success-modal');
    const messageEl = document.getElementById('success-message');
    if (modal && messageEl) {
        messageEl.textContent = message;
        modal.classList.add('open');
        setTimeout(() => modal.classList.remove('open'), 2000);
    }
}

function closeSuccessModal() {
    document.getElementById('success-modal')?.classList.remove('open');
}

// Make functions globally accessible
window.openAddStaffModal = openAddStaffModal;
window.closeAddStaffModal = closeAddStaffModal;
window.onFacultyMemberChange = onFacultyMemberChange;
window.previewStaffPhoto = previewStaffPhoto;
window.submitAddStaff = submitAddStaff;
window.showSuccessModal = showSuccessModal;
window.closeSuccessModal = closeSuccessModal;

// ── Subject Selection ──────────────────────────────────────────

// All Subjects by Year and Semester
const ALL_SUBJECTS = {
    '1-1': [
        { code: 'HIST/KAS 1', name: 'Philippine History', units: 3 },
        { code: 'ETHICS 1', name: 'Ethics and Moral Reasoning', units: 3 },
        { code: 'HFDS 101', name: 'Family and Environment', units: 3 },
        { code: 'HUME 100', name: 'Introduction to Human Ecology', units: 3 },
        { code: 'CERP 101', name: 'Fundamentals of Human Settlements', units: 3 },
        { code: 'SDS 101', name: 'Introduction to Social Development', units: 3 },
        { code: 'HK 11', name: 'Concept in Wellness and Basic Injury Management', units: 2 }
    ],
    '1-2': [
        { code: 'ARTS 1', name: 'Critical Perspectives in the Arts', units: 3 },
        { code: 'HUME 112', name: 'Sustainability Science', units: 3 },
        { code: 'HUME 107', name: 'Principles of Human Development', units: 3 },
        { code: 'HUME 105', name: 'Humans and their Environment', units: 3 },
        { code: 'SOC 140', name: 'Introduction to Demography', units: 3 },
        { code: 'BIO 150', name: 'Principles of Ecology', units: 4 },
        { code: 'HK 12/13', name: 'Human Kinetics Activities', units: 2 },
        { code: 'NSTP 1', name: 'National Service Training Program 1', units: 3 }
    ],
    '2-1': [
        { code: 'PI 10', name: 'Life and Works of Rizal', units: 3 },
        { code: 'HUME 110', name: 'Ecology and Value Systems', units: 3 },
        { code: 'HUME 111', name: 'Human Ecological Perspective in Development', units: 3 },
        { code: 'HUME 113', name: 'Community Study in Human Welfare', units: 3 },
        { code: 'HK 12 or 13', name: 'Human Kinetics Activities', units: 2 },
        { code: 'NSTP 2', name: 'National Service Training Program 2', units: 3 }
    ],
    '2-2': [
        { code: 'STS 1', name: 'Science, Technology, and Society', units: 3 },
        { code: 'STAT 166', name: 'Statistics for Social Sciences', units: 3 },
        { code: 'HUME 114', name: 'Material and Energy Flows', units: 3 },
        { code: 'CERP 161', name: 'Planning Theory and Practice I', units: 3 },
        { code: 'HUME 115', name: 'Social Policies', units: 3 },
        { code: 'HK 12 or 13', name: 'Human Kinetics Activities', units: 2 }
    ],
    '3-1': [
        { code: 'COMM 10', name: 'Critical Perspectives in Communication', units: 3 },
        { code: 'HUME 195', name: 'Research Methods in Human Ecology', units: 3 },
        { code: 'HUME 122', name: 'Human Needs and the Built Environment', units: 3 },
        { code: 'HUME 123', name: 'Climate Change Adaptation and Disaster Risk Reduction in Human Ecosystems', units: 3 },
        { code: 'CERP 140', name: 'Fundamentals of Environmental Economics', units: 3 },
        { code: 'CERP 122', name: 'Conservation of Natural Resources', units: 3 },
        { code: 'SDS 172', name: 'Techniques in Community Organizing', units: 3 }
    ],
    '3-2': [
        { code: 'HUME 125', name: 'Human Ecological Systems Mapping', units: 5 },
        { code: 'HUME 124', name: 'Environmental Health', units: 3 },
        { code: 'SDS 173', name: 'Consumer Education', units: 3 },
        { code: 'HFDS 110', name: 'Migration', units: 3 },
        { code: 'CERP 162', name: 'Planning Theory and Practice II', units: 3 },
        { code: 'CERP 163', name: 'Land Use Planning for Human Settlements', units: 5 },
        { code: 'CERP 165', name: 'Human Settlements Planning I', units: 5 }
    ],
    '4-1': [
        { code: 'HNF 141', name: 'Food and Nutrition Systems', units: 3 },
        { code: 'CERP 166', name: 'Human Settlements Planning II', units: 7 },
        { code: 'CERP 170', name: 'Environmental Project Planning & Administration', units: 3 },
        { code: 'CERP 164', name: 'Spatial Analysis & Planning for Human Settlements', units: 5 },
        { code: 'CERP 200', name: 'Undergraduate Thesis', units: 3 }
    ],
    '4-2': [
        { code: 'HUME 200a', name: 'Supervised Field Experience', units: 6 },
        { code: 'HUME 199', name: 'Seminar in Human Ecology', units: 1 },
        { code: 'CERP 200', name: 'Undergraduate Thesis', units: 3 }
    ]
};

let selectedSubjects = [];

// Handle year level checkbox changes
function onStaffYearCheckChange(mode) {
    const checkboxes = document.querySelectorAll('input[name="yearLevel"]:checked');
    const selectedYears = Array.from(checkboxes).map(cb => cb.value);

    // Reset selected subjects when year selection changes
    selectedSubjects = [];

    if (selectedYears.length === 0) {
        document.getElementById('subject-chips').innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:0.8rem;width:100%;">Please select a year level first</div>';
        return;
    }

    renderSubjectChipsMultiYear(selectedYears);
}

function renderSubjectChipsMultiYear(years) {
    const container = document.getElementById('subject-chips');
    if (!container) return;

    let html = '';

    // For each selected year, show subjects grouped by semester
    years.sort().forEach(year => {
        const sem1Key = year + '-1';
        const sem2Key = year + '-2';
        const sem1Subjects = ALL_SUBJECTS[sem1Key] || [];
        const sem2Subjects = ALL_SUBJECTS[sem2Key] || [];

        // Year header
        html += `
            <div style="font-weight:700;color:#6b0f1a;font-size:0.85rem;margin-top:${years[0] === year ? '0' : '24px'};margin-bottom:4px;border-bottom:2px solid #6b0f1a;padding-bottom:4px;">
                ${year}${['st', 'nd', 'rd', 'th'][year - 1]} Year
            </div>
        `;

        // 1st Semester
        if (sem1Subjects.length > 0) {
            html += '<div style="font-size:0.75rem;font-weight:600;color:#6b7280;margin-top:12px;margin-bottom:10px;">1st Semester</div>';
            html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px;">';
            sem1Subjects.forEach(subj => {
                const isSelected = selectedSubjects.some(s => s.code === subj.code);
                html += `<div class="subject-chip ${isSelected ? 'selected' : ''}" 
                    data-code="${subj.code}" data-name="${subj.name}" data-year="${year}"
                    onclick="toggleSubject('${subj.code}', '${subj.name.replace(/'/g, "\\'")}', '${year}')">
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
                html += `<div class="subject-chip ${isSelected ? 'selected' : ''}" 
                    data-code="${subj.code}" data-name="${subj.name}" data-year="${year}"
                    onclick="toggleSubject('${subj.code}', '${subj.name.replace(/'/g, "\\'")}', '${year}')">
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

function toggleSubject(code, name, year) {
    const index = selectedSubjects.findIndex(s => s.code === code);
    if (index > -1) {
        selectedSubjects.splice(index, 1);
    } else {
        selectedSubjects.push({ code, name, year });
    }

    // Re-render the chips
    const checkboxes = document.querySelectorAll('input[name="yearLevel"]:checked');
    const selectedYears = Array.from(checkboxes).map(cb => cb.value);
    if (selectedYears.length > 0) {
        renderSubjectChipsMultiYear(selectedYears);
    }
}

function showStaffDetails(staffId) {
    console.log('Show details for staff:', staffId);
    // TODO: Implement staff details modal
}

// Make additional functions globally accessible
window.onStaffYearCheckChange = onStaffYearCheckChange;
window.toggleSubject = toggleSubject;
window.showStaffDetails = showStaffDetails;
window.toggleStaffCheckbox = toggleStaffCheckbox;
window.toggleStaffSelection = toggleStaffSelection;
window.confirmBulkDeleteStaff = confirmBulkDeleteStaff;
window.closeBulkDeleteModal = closeBulkDeleteModal;
window.executeBulkDelete = executeBulkDelete;
