/**
 * ═══════════════════════════════════════════════════════════════════════
 * COURSES V2 - MODERN REDESIGN
 * Production-quality JavaScript with enhanced UX
 * ═══════════════════════════════════════════════════════════════════════
 */

// ══════════════════════════════════════════════════════════════════════
// STATE MANAGEMENT
// ══════════════════════════════════════════════════════════════════════

// Helper functions for school year/semester
function getCurrentSchoolYear() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1; // 0-indexed

    // If before August, use previous year
    if (month < 8) {
        return `${year - 1}-${year}`;
    }
    return `${year}-${year + 1}`;
}

function getCurrentSemester() {
    const now = new Date();
    const month = now.getMonth() + 1;

    // Aug-Dec: 1st semester, Jan-May: 2nd semester, Jun-Jul: Summer
    if (month >= 8 && month <= 12) return '1';
    if (month >= 1 && month <= 5) return '2';
    return '3'; // Summer
}


const state = {
    // Data
    courses: [],
    faculty: [],
    eligibility: [],
    sections: [],
    roomAllocations: [],
    assignments: [],
    availableRooms: [],

    // UI State
    currentStep: 1, // Always start at Step 1 on page load
    selectedFacultyId: null,
    selectedCourses: new Map(), // courseId => Set<sections>
    expandedCourse: null,
    editingCourseId: null, // Track which course card is being edited

    // Batch editing state for Step 1
    unsavedEligibilityChanges: new Map(), // courseId => Map<facultyId, boolean>
    hasUnsavedChanges: false,

    // School year/semester - normalize semester to just number
    schoolYear: localStorage.getItem('cerp_schoolYear') || getCurrentSchoolYear(),
    semester: (localStorage.getItem('cerp_semester') || getCurrentSemester()).replace('Semester ', ''),
};

// ══════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Courses V2 Initializing...');

    // Always start at Step 1 on page load (clear any saved step)
    localStorage.removeItem('courses_v2_current_step');

    // Check if onboarding was dismissed
    if (localStorage.getItem('courses_v2_onboarding_dismissed') === 'true') {
        dismissOnboarding(false);
    }

    // Load data
    await Promise.all([
        loadCourses(),
        loadFaculty(),
        loadEligibility(),
        loadSections(),
        loadRooms(),
        loadRoomAllocations(),
        loadAssignments()
    ]);

    // Render initial state
    renderFacultyGrid();
    renderCoursesList();
    updateStepCompletion();
    updateCompleteButton();

    // Force render Step 1 on initial load if navigating to it
    if (state.currentStep === 1) {
        renderEligibilityGrid();
    } else if (state.currentStep === 2) {
        renderSectionsGrid();
    } else if (state.currentStep === 3) {
        // Faculty Assignment step - no special prerequisites check needed
    } else if (state.currentStep === 4) {
        renderRoomsGrid();
        checkStep4Prerequisites();
    }

    console.log('✅ Courses V2 Ready');
    console.log('State:', {
        courses: state.courses.length,
        faculty: state.faculty.length,
        eligibility: state.eligibility.length,
        sections: state.sections.length,
        roomAllocations: state.roomAllocations.length,
        rooms: state.availableRooms.length
    });
});

// ══════════════════════════════════════════════════════════════════════
// DATA LOADING
// ══════════════════════════════════════════════════════════════════════

async function loadCourses() {
    try {
        const response = await fetch('/api/courses');
        if (!response.ok) throw new Error('Failed to load courses');
        const data = await response.json();
        // Handle both {courses: [...]} and plain array formats
        const coursesArray = data.courses || data;
        state.courses = coursesArray.map(c => ({
            id: c.id,
            code: c.course_code,
            name: c.course_name,
            units: c.units || 3
        }));
        console.log(`📚 Loaded ${state.courses.length} courses`);
    } catch (error) {
        console.error('Error loading courses:', error);
        showToast('Failed to load courses', 'error');
        state.courses = [];
    }
}

async function loadFaculty() {
    try {
        const response = await fetch('/api/members?faculty=true');
        if (!response.ok) throw new Error('Failed to load faculty');
        const data = await response.json();
        state.faculty = data.map(m => ({
            id: m.id,
            firstName: m.first || '',
            lastName: m.last || '',
            fullName: `${m.first || ''} ${m.last || ''}`.trim(),
            profilePic: m.profile_pic || null,
            units: 0
        }));
        console.log(`👥 Loaded ${state.faculty.length} faculty`);
        updateFacultyCount();
    } catch (error) {
        console.error('Error loading faculty:', error);
        showToast('Failed to load faculty', 'error');
        state.faculty = [];
    }
}

async function loadEligibility() {
    try {
        // Load from faculty_course_units table
        const response = await fetch('/api/faculty-course-units');
        if (!response.ok) throw new Error('Failed to load eligibility');
        state.eligibility = await response.json();
        console.log(`✅ Loaded eligibility data: ${state.eligibility.length} entries`);
    } catch (error) {
        console.error('Error loading eligibility:', error);
        state.eligibility = [];
    }
}

async function loadSections() {
    try {
        // Load configured sections
        const url = `/api/course-sections?school_year=${encodeURIComponent(state.schoolYear)}&semester=${encodeURIComponent(state.semester)}`;
        console.log(`🔍 Fetching sections from: ${url}`);
        console.log(`   School Year: "${state.schoolYear}"`);
        console.log(`   Semester: "${state.semester}"`);

        const response = await fetch(url);
        if (!response.ok) {
            console.warn(`Section API returned ${response.status}`);
            state.sections = [];
            return;
        }
        state.sections = await response.json();
        console.log(`📊 Loaded ${state.sections.length} section configurations:`, state.sections);
    } catch (error) {
        console.error('Error loading sections:', error);
        // Don't show toast, sections might not exist yet
        state.sections = [];
    }
}

async function loadRooms() {
    try {
        const response = await fetch('/api/rooms');
        if (!response.ok) throw new Error('Failed to load rooms');
        const data = await response.json();

        // Build rooms list with proper structure {id, name}
        const rooms = [];

        // Add custom rooms from database (have IDs)
        if (data.available && data.rooms) {
            data.rooms.forEach(room => {
                rooms.push({
                    id: room.id,
                    name: room.name
                });
            });
        }

        // Add default rooms (no IDs, represented as null)
        if (data.default_rooms) {
            data.default_rooms.forEach(roomName => {
                // Only add if not already in custom rooms
                if (!rooms.some(r => r.name === roomName)) {
                    rooms.push({
                        id: null,
                        name: roomName
                    });
                }
            });
        }

        state.availableRooms = rooms;
        console.log(`🏠 Loaded ${state.availableRooms.length} available rooms`);
    } catch (error) {
        console.error('Error loading rooms:', error);
        state.availableRooms = [];
    }
}

async function loadRoomAllocations() {
    try {
        const url = `/api/section-rooms?school_year=${encodeURIComponent(state.schoolYear)}&semester=${encodeURIComponent(state.semester)}`;
        console.log(`🔍 Fetching room allocations from: ${url}`);

        const response = await fetch(url);
        if (!response.ok) {
            console.warn(`Room allocations API returned ${response.status}`);
            state.roomAllocations = [];
            return;
        }
        state.roomAllocations = await response.json();
        console.log(`🏠 Loaded ${state.roomAllocations.length} room allocations:`, state.roomAllocations);
    } catch (error) {
        console.error('Error loading room allocations:', error);
        state.roomAllocations = [];
    }
}

async function loadAssignments() {
    try {
        const url = `/api/allocation/assignments?school_year=${encodeURIComponent(state.schoolYear)}&semester=${encodeURIComponent(state.semester)}`;
        console.log(`🔍 Fetching assignments from: ${url}`);

        const response = await fetch(url);
        if (!response.ok) {
            console.warn(`Assignments API returned ${response.status}`);
            state.assignments = [];
            return;
        }
        state.assignments = await response.json();
        console.log(`📋 Loaded ${state.assignments.length} assignments:`, state.assignments);
        calculateFacultyLoads();
    } catch (error) {
        console.error('Error loading assignments:', error);
        state.assignments = [];
    }
}

// ══════════════════════════════════════════════════════════════════════
// ONBOARDING
// ══════════════════════════════════════════════════════════════════════

function dismissOnboarding(animate = true) {
    const banner = document.getElementById('onboarding-banner');
    if (!banner) return;

    if (animate) {
        banner.style.animation = 'slideUp 0.3s ease forwards';
        setTimeout(() => banner.remove(), 300);
        localStorage.setItem('courses_v2_onboarding_dismissed', 'true');
    } else {
        banner.remove();
    }
}

// ══════════════════════════════════════════════════════════════════════
// WORKFLOW STEPPER
// ══════════════════════════════════════════════════════════════════════

function navigateToStep(step) {
    // Update state
    state.currentStep = step;

    // Save to localStorage so it persists
    localStorage.setItem('courses_v2_current_step', step);

    // Update stepper UI
    document.querySelectorAll('.step-item').forEach((item, index) => {
        item.classList.toggle('active', index + 1 === step);
    });

    // Update panels
    for (let i = 1; i <= 4; i++) {
        const panel = document.getElementById(`step-panel-${i}`);
        if (panel) {
            const isActive = i === step;
            panel.classList.toggle('active', isActive);
            panel.style.display = isActive ? 'block' : 'none';
            console.log(`Step ${i} panel: ${isActive ? 'VISIBLE' : 'hidden'}`);
        } else {
            console.error(`❌ step-panel-${i} not found!`);
        }
    }

    // Load step-specific data - ensure it renders
    if (step === 1) {
        console.log('Rendering Step 1: Eligibility');
        setTimeout(() => renderEligibilityGrid(), 100);
    } else if (step === 2) {
        console.log('Rendering Step 2: Sections');
        setTimeout(() => renderSectionsGrid(), 100);
    } else if (step === 3) {
        console.log('Rendering Step 3: Faculty Assignment');
        renderCoursesList();
    } else if (step === 4) {
        console.log('Rendering Step 4: Room Allocation');
        checkStep4Prerequisites();
        setTimeout(() => renderRoomsGrid(), 100);
    }

    console.log(`📍 Navigated to Step ${step}`);
}

function checkStep4Prerequisites() {
    const warning = document.getElementById('step4-prerequisites-warning');
    if (!warning) return;

    const hasEligibility = state.eligibility.length > 0;
    const hasSections = state.sections.length > 0;
    const hasAssignments = state.assignments.length > 0;
    const missingPrereqs = !hasEligibility || !hasSections || !hasAssignments;

    warning.style.display = missingPrereqs ? 'flex' : 'none';
}

function updateStepCompletion() {
    // Step 1: Complete if any eligibility is configured
    const step1Complete = state.eligibility.length > 0;
    updateStepStatus(1, step1Complete);

    // Step 2: Complete if any sections are configured for current school year/semester
    const currentSections = state.sections.filter(s =>
        s.school_year === state.schoolYear &&
        s.semester === state.semester
    );
    const step2Complete = currentSections.length > 0;
    updateStepStatus(2, step2Complete);

    // Step 3: Complete if any assignments exist for current school year/semester
    const currentAssignments = state.assignments.filter(a =>
        a.school_year === state.schoolYear &&
        a.semester === state.semester
    );
    const step3Complete = currentAssignments.length > 0;
    updateStepStatus(3, step3Complete);

    // Step 4: Complete if any room allocations exist for current school year/semester
    const currentAllocations = state.roomAllocations.filter(a =>
        a.school_year === state.schoolYear &&
        a.semester === state.semester
    );
    const step4Complete = currentAllocations.length > 0;
    updateStepStatus(4, step4Complete);
}

function updateStepStatus(stepNum, isComplete) {
    const stepItem = document.querySelector(`.step-item[data-step="${stepNum}"]`);
    if (stepItem) {
        stepItem.classList.toggle('completed', isComplete);
    }
}

// ══════════════════════════════════════════════════════════════════════
// FACULTY GRID
// ══════════════════════════════════════════════════════════════════════

function renderFacultyGrid() {
    const grid = document.getElementById('faculty-grid-v2');
    if (!grid) return;

    // Filter faculty to show only those with at least one eligibility
    const facultyWithEligibility = state.faculty.filter(faculty => {
        return state.eligibility.some(e => e.faculty_id === faculty.id);
    });

    if (facultyWithEligibility.length === 0) {
        grid.innerHTML = `
            <div class="empty-state-full" style="grid-column: 1/-1;">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <circle cx="60" cy="35" r="18" fill="#fef2f2" stroke="#6b0f1a" stroke-width="3"/>
                    <path d="M35 85c0-13.8 11.2-25 25-25s25 11.2 25 25" stroke="#6b0f1a" stroke-width="3" stroke-linecap="round" fill="none"/>
                    <circle cx="45" cy="30" r="2" fill="#6b0f1a"/>
                    <circle cx="75" cy="30" r="2" fill="#6b0f1a"/>
                    <path d="M50 42c2 2 4 3 10 3s8-1 10-3" stroke="#6b0f1a" stroke-width="2" stroke-linecap="round" fill="none"/>
                </svg>
                <h3>No Eligible Faculty</h3>
                <p>Go back to Step 1 and configure course eligibility for faculty first.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = facultyWithEligibility.map(faculty => {
        const initials = getInitials(faculty.fullName);
        const isSelected = state.selectedFacultyId === faculty.id;

        // Use profile picture if available, otherwise show initials
        const avatarContent = faculty.profilePic
            ? `<img src="${faculty.profilePic}" alt="${escapeHtml(faculty.fullName)}" class="faculty-avatar-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
               <div class="faculty-avatar-fallback" style="display:none;">${initials}</div>`
            : `<div class="faculty-avatar-fallback">${initials}</div>`;

        return `
            <div class="faculty-card-v2 ${isSelected ? 'selected' : ''}" 
                 data-faculty-id="${faculty.id}"
                 onclick="selectFaculty('${faculty.id}')">
                <div class="faculty-avatar-v2">${avatarContent}</div>
                <div class="faculty-name-v2">${escapeHtml(faculty.fullName)}</div>
                <div class="faculty-load-v2" id="faculty-load-${faculty.id}">${faculty.units} units</div>
            </div>
        `;
    }).join('');
}

function selectFaculty(facultyId) {
    // Update state
    state.selectedFacultyId = facultyId;

    // Update faculty cards
    document.querySelectorAll('.faculty-card-v2').forEach(card => {
        card.classList.toggle('selected', card.dataset.facultyId === facultyId);
    });

    // Show active header
    const emptyHeader = document.getElementById('assignment-header-empty');
    const activeHeader = document.getElementById('assignment-header-active');

    if (emptyHeader && activeHeader) {
        emptyHeader.style.display = 'none';
        activeHeader.style.display = 'flex';
    }

    // Update header info
    const faculty = state.faculty.find(f => f.id === facultyId);
    if (faculty) {
        const avatar = document.getElementById('selected-faculty-avatar');
        const name = document.getElementById('selected-faculty-name');
        const units = document.getElementById('selected-faculty-units');

        if (avatar) {
            // Use profile picture if available, otherwise initials
            if (faculty.profilePic) {
                avatar.innerHTML = `<img src="${faculty.profilePic}" alt="${escapeHtml(faculty.fullName)}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;" onerror="this.style.display='none'; this.parentElement.textContent='${getInitials(faculty.fullName)}';">`;
            } else {
                avatar.textContent = getInitials(faculty.fullName);
            }
        }
        if (name) name.textContent = faculty.fullName;
        if (units) units.textContent = faculty.units;
    }

    // Load faculty's current assignments
    loadFacultyAssignments(facultyId);

    // Update course list to show eligibility
    renderCoursesList();

    console.log(`👤 Selected faculty: ${faculty.fullName}`);
}

function clearFacultySelection() {
    state.selectedFacultyId = null;
    state.selectedCourses.clear();
    state.expandedCourse = null;

    // Update UI
    document.querySelectorAll('.faculty-card-v2').forEach(card => {
        card.classList.remove('selected');
    });

    const emptyHeader = document.getElementById('assignment-header-empty');
    const activeHeader = document.getElementById('assignment-header-active');

    if (emptyHeader && activeHeader) {
        emptyHeader.style.display = 'flex';
        activeHeader.style.display = 'none';
    }

    renderCoursesList();
}

function calculateFacultyLoads() {
    // Reset all loads
    state.faculty.forEach(f => f.units = 0);

    // Sum up from assignments
    state.assignments.forEach(assignment => {
        const faculty = state.faculty.find(f => f.id === assignment.faculty_id);
        if (faculty) {
            const course = state.courses.find(c => c.id === assignment.course_id);
            let units = course ? course.units : 3; // Default course units

            // Check if this section has custom units (for custom blocks)
            if (assignment.section) {
                const section = state.sections.find(s =>
                    s.course_id === assignment.course_id &&
                    s.section_letter === assignment.section
                );

                // If section has custom units (custom block), use those instead
                if (section && section.units) {
                    units = section.units;
                }
            }

            faculty.units += units;
        }
    });

    // Update UI
    state.faculty.forEach(faculty => {
        const loadEl = document.getElementById(`faculty-load-${faculty.id}`);
        if (loadEl) {
            loadEl.textContent = `${faculty.units} units`;
        }
    });
}

function updateFacultyCount() {
    const countEl = document.getElementById('faculty-count-display');
    if (countEl) {
        // Count only faculty with eligibility
        const count = state.faculty.filter(faculty => {
            return state.eligibility.some(e => e.faculty_id === faculty.id);
        }).length;
        countEl.textContent = `${count} ${count === 1 ? 'member' : 'members'}`;
    }
}

// ══════════════════════════════════════════════════════════════════════
// COURSES LIST
// ══════════════════════════════════════════════════════════════════════

function renderCoursesList() {
    const list = document.getElementById('courses-list-v2');
    if (!list) return;

    if (state.courses.length === 0) {
        list.innerHTML = `
            <div class="empty-state-full">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <circle cx="60" cy="60" r="50" fill="#fef2f2"/>
                    <path d="M40 50h40M40 60h40M40 70h25" stroke="#6b0f1a" stroke-width="3" stroke-linecap="round"/>
                    <rect x="35" y="35" width="50" height="50" rx="5" stroke="#6b0f1a" stroke-width="3" fill="none"/>
                </svg>
                <h3>No Courses Available</h3>
                <p>Courses will appear here once they are configured in the system.</p>
            </div>
        `;
        return;
    }

    // Filter courses: if faculty selected, show only eligible courses
    let displayCourses = state.courses;
    if (state.selectedFacultyId) {
        displayCourses = state.courses.filter(course =>
            isFacultyEligible(state.selectedFacultyId, course.id)
        );
    }

    // Check if faculty is selected
    const noFacultySelected = !state.selectedFacultyId;

    if (!noFacultySelected && displayCourses.length === 0) {
        list.innerHTML = `
            <div class="empty-state-full">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <circle cx="60" cy="60" r="50" fill="#fef2f2"/>
                    <path d="M40 50h40M40 60h40M40 70h25" stroke="#6b0f1a" stroke-width="3" stroke-linecap="round"/>
                </svg>
                <h3>No Eligible Courses</h3>
                <p>This faculty member is not eligible to teach any courses yet. Configure eligibility in Step 1.</p>
                <button class="btn-primary-v2" onclick="navigateToStep(1)" style="margin-top: 1rem;">
                    Go to Step 1
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                </button>
            </div>
        `;
        return;
    }

    list.innerHTML = displayCourses.map(course => {
        const isExpanded = state.expandedCourse === course.id;
        const isEligible = !noFacultySelected && isFacultyEligible(state.selectedFacultyId, course.id);
        const isDisabled = noFacultySelected || !isEligible;
        const hasSections = getAvailableSections(course.id).length > 0;

        return `
            <div class="course-card-v2 ${isExpanded ? 'expanded' : ''} ${isDisabled ? 'disabled-card' : ''} ${!hasSections ? 'no-sections' : ''}" 
                 data-course-id="${course.id}"
                 onclick="toggleCourseExpansion('${course.id}')">
                <div class="course-card-header">
                    <div class="course-title-group">
                        <div class="course-code-v2">${escapeHtml(course.code)}</div>
                        <p class="course-name-v2">${escapeHtml(course.name)}</p>
                    </div>
                    <div class="course-units-badge">${course.units} ${course.units === 1 ? 'unit' : 'units'}</div>
                </div>
                ${!hasSections ? '<p class="no-sections-warning">⚠️ No sections configured</p>' : ''}
                ${isExpanded && !isDisabled && hasSections ? renderSectionSelector(course) : ''}
            </div>
        `;
    }).join('');
}

function toggleCourseExpansion(courseId) {
    if (!state.selectedFacultyId) {
        showToast('Please select a faculty member first', 'warning');
        return;
    }

    if (!isFacultyEligible(state.selectedFacultyId, courseId)) {
        showToast('This faculty member is not eligible to teach this course', 'warning');
        return;
    }

    // Toggle expansion
    if (state.expandedCourse === courseId) {
        state.expandedCourse = null;
    } else {
        state.expandedCourse = courseId;
    }

    renderCoursesList();
}

function renderSectionSelector(course) {
    const availableSections = getAvailableSections(course.id);
    const selectedSections = state.selectedCourses.get(course.id) || new Set();

    if (availableSections.length === 0) {
        return `
            <div class="section-selector-v2">
                <p class="no-sections-msg">No sections configured for this course. Complete Step 2 first.</p>
            </div>
        `;
    }

    return `
        <div class="section-selector-v2">
            <div class="section-selector-header">
                <span class="section-selector-title">Select Sections</span>
                <button class="legend-trigger" onclick="event.stopPropagation(); openLegend();">
                    <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Legend
                </button>
            </div>
            <div class="section-buttons-v2">
                ${availableSections.map(sectionData => {
        const section = sectionData.section_letter;
        const isSelected = selectedSections.has(section);
        const isAssigned = isSectionAssigned(course.id, section);
        const isShared = isSectionShared(course.id, section);
        const isCustomBlock = sectionData.is_custom_block;
        const roomAllocation = state.roomAllocations.find(r =>
            r.course_id === course.id && r.section_letter === section
        );
        const roomName = roomAllocation?.custom_room_name ||
            (roomAllocation?.room_id ? 'Room assigned' : 'No room');

        let className = 'section-btn-v2';
        if (isSelected) className += ' selected';
        else if (isShared) className += ' shared';
        else if (isAssigned) className += ' assigned';
        if (isCustomBlock) className += ' custom-block';

        const title = `Section ${section}${isCustomBlock ? ' (Custom Block)' : ''}\nRoom: ${roomName}`;

        return `
                        <button class="${className}" 
                                onclick="event.stopPropagation(); toggleSection('${course.id}', '${section}');"
                                title="${title}">
                            ${section}${isCustomBlock ? '🎓' : ''}
                        </button>
                    `;
    }).join('')}
            </div>
        </div>
    `;
}

function toggleSection(courseId, section) {
    if (!state.selectedCourses.has(courseId)) {
        state.selectedCourses.set(courseId, new Set());
    }

    const sections = state.selectedCourses.get(courseId);

    if (sections.has(section)) {
        sections.delete(section);
        if (sections.size === 0) {
            state.selectedCourses.delete(courseId);
        }
    } else {
        sections.add(section);
    }

    renderCoursesList();
}

// ══════════════════════════════════════════════════════════════════════
// ASSIGNMENT OPERATIONS
// ══════════════════════════════════════════════════════════════════════

async function saveAssignments() {
    if (!state.selectedFacultyId) {
        showToast('No faculty selected', 'warning');
        return;
    }

    if (state.selectedCourses.size === 0) {
        showToast('No courses selected', 'warning');
        return;
    }

    const btn = document.getElementById('btn-save-assignments');
    const spinner = btn.querySelector('.btn-spinner');

    try {
        btn.disabled = true;
        if (spinner) spinner.style.display = 'block';

        // Build assignments array
        const assignments = [];
        state.selectedCourses.forEach((sections, courseId) => {
            sections.forEach(section => {
                assignments.push({
                    faculty_id: state.selectedFacultyId,
                    course_id: courseId,
                    section: section,
                    school_year: state.schoolYear,
                    semester: state.semester
                });
            });
        });

        const response = await fetch('/api/allocation/assignments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ assignments })
        });

        if (!response.ok) throw new Error('Failed to save assignments');

        // Reload assignments
        await loadAssignments();

        // Clear selection
        state.selectedCourses.clear();
        state.expandedCourse = null;

        // Update UI
        renderCoursesList();
        calculateFacultyLoads();
        updateStepCompletion();

        // Show step completion animation
        showStepCompletionAnimation(3);

        showToast('Assignments saved successfully!', 'success');

    } catch (error) {
        console.error('Error saving assignments:', error);
        showToast('Failed to save assignments', 'error');
    } finally {
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
    }
}

function loadFacultyAssignments(facultyId) {
    // Pre-select courses/sections this faculty is already assigned to
    state.selectedCourses.clear();

    const facultyAssignments = state.assignments.filter(a => a.faculty_id === facultyId);

    facultyAssignments.forEach(assignment => {
        if (!state.selectedCourses.has(assignment.course_id)) {
            state.selectedCourses.set(assignment.course_id, new Set());
        }
        state.selectedCourses.get(assignment.course_id).add(assignment.section);
    });
}

// ══════════════════════════════════════════════════════════════════════
// SEARCH & FILTER
// ══════════════════════════════════════════════════════════════════════

function filterCourses() {
    const input = document.getElementById('course-search');
    if (!input) return;

    const query = input.value.toLowerCase().trim();

    document.querySelectorAll('.course-card-v2').forEach(card => {
        const code = card.querySelector('.course-code-v2')?.textContent.toLowerCase() || '';
        const name = card.querySelector('.course-name-v2')?.textContent.toLowerCase() || '';

        const matches = code.includes(query) || name.includes(query);
        card.style.display = matches ? '' : 'none';
    });
}

// ══════════════════════════════════════════════════════════════════════
// LEGEND MODAL
// ══════════════════════════════════════════════════════════════════════

function openLegend() {
    const modal = document.getElementById('legend-modal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeLegend(event) {
    if (!event || event.target.id === 'legend-modal') {
        const modal = document.getElementById('legend-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }
}

// ══════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════

function isFacultyEligible(facultyId, courseId) {
    return state.eligibility.some(e =>
        e.faculty_id === facultyId && e.course_id === courseId
    );
}

function getAvailableSections(courseId) {
    // Return sections that are configured for this course (from Step 2)
    const courseSections = state.sections.filter(s => s.course_id === courseId);
    return courseSections.sort((a, b) =>
        a.section_letter.localeCompare(b.section_letter)
    );
}

function isSectionAssigned(courseId, section) {
    return state.assignments.some(a =>
        a.course_id === courseId &&
        a.section === section &&
        a.faculty_id !== state.selectedFacultyId
    );
}

function isSectionShared(courseId, section) {
    const assignedCount = state.assignments.filter(a =>
        a.course_id === courseId && a.section === section
    ).length;
    return assignedCount > 1;
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) {
        console.warn('Toast container not found');
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />',
        error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />',
        warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />',
        info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />'
    };

    toast.innerHTML = `
        <div class="toast-icon">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                ${icons[type] || icons.info}
            </svg>
        </div>
        <div class="toast-content">
            <p class="toast-message">${escapeHtml(message)}</p>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    `;

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ══════════════════════════════════════════════════════════════════════
// STEP 1 & 2 RENDERS (Full implementations)
// ══════════════════════════════════════════════════════════════════════

function renderEligibilityGrid() {
    const grid = document.getElementById('eligibility-grid');
    if (!grid) {
        console.error('❌ eligibility-grid element not found!');
        return;
    }

    console.log('Rendering eligibility grid:', {
        courses: state.courses.length,
        faculty: state.faculty.length
    });

    if (state.courses.length === 0 || state.faculty.length === 0) {
        grid.innerHTML = `
            <div class="empty-state-full" style="grid-column: 1/-1;">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <rect x="20" y="30" width="80" height="60" rx="8" fill="#fef2f2" stroke="#6b0f1a" stroke-width="3"/>
                    <path d="M35 50h50M35 60h50M35 70h30" stroke="#6b0f1a" stroke-width="3" stroke-linecap="round"/>
                </svg>
                <h3>Prerequisites Missing</h3>
                <p>You need both courses and faculty members configured before defining eligibility.</p>
                ${state.courses.length === 0 ? '<p style="margin-top: 0.5rem;">⚠️ No courses found</p>' : ''}
                ${state.faculty.length === 0 ? '<p style="margin-top: 0.5rem;">⚠️ No faculty found</p>' : ''}
            </div>
        `;
        return;
    }

    grid.innerHTML = state.courses.map(course => {
        const eligibleFaculty = state.eligibility.filter(e => e.course_id === course.id);
        const eligibleCount = eligibleFaculty.length;
        const isEditing = state.editingCourseId === course.id;

        return `
            <div class="eligibility-card ${isEditing ? 'editing' : 'locked'}" data-course-id="${course.id}">
                <div class="eligibility-card-header">
                    <div class="eligibility-course-info">
                        <h4>${escapeHtml(course.code)}</h4>
                        <p>${escapeHtml(course.name)}</p>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button class="btn-edit-save" onclick="toggleEditMode('${course.id}')">
                            ${isEditing ? 'Save' : 'Edit'}
                        </button>
                        <div class="eligibility-count-badge">
                            ${eligibleCount} ${eligibleCount === 1 ? 'faculty' : 'faculty'}
                        </div>
                    </div>
                </div>

                <div class="faculty-checklist">
                    ${state.faculty.map(faculty => {
            const isEligible = eligibleFaculty.some(e => e.faculty_id === faculty.id);
            return `
                            <label class="faculty-checkbox-item">
                                <input type="checkbox" 
                                       ${isEligible ? 'checked' : ''}
                                       ${isEditing ? '' : 'disabled'}
                                       onchange="toggleEligibility('${faculty.id}', '${course.id}', this.checked)">
                                <span class="faculty-checkbox-label">${escapeHtml(faculty.fullName)}</span>
                            </label>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    }).join('');

    console.log(`✅ Rendered ${state.courses.length} eligibility cards`);
}

function renderSectionsGrid() {
    const grid = document.getElementById('sections-grid');
    if (!grid) {
        console.error('❌ sections-grid element not found!');
        return;
    }

    // Filter courses to show only those with eligibility configured
    const coursesWithEligibility = state.courses.filter(course => {
        return state.eligibility.some(e => e.course_id === course.id);
    });

    console.log('Rendering sections grid:', {
        totalCourses: state.courses.length,
        coursesWithEligibility: coursesWithEligibility.length
    });

    if (coursesWithEligibility.length === 0) {
        grid.innerHTML = `
            <div class="empty-state-full" style="grid-column: 1/-1;">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <rect x="20" y="30" width="80" height="60" rx="8" fill="#fef2f2" stroke="#6b0f1a" stroke-width="3"/>
                    <circle cx="40" cy="50" r="5" fill="#6b0f1a"/>
                    <circle cx="60" cy="50" r="5" fill="#6b0f1a"/>
                    <circle cx="80" cy="50" r="5" fill="#6b0f1a"/>
                </svg>
                <h3>No Courses with Eligibility</h3>
                <p>Go back to Step 1 and configure faculty eligibility for courses first.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = coursesWithEligibility.map(course => {
        // Get sections for this course
        const courseSections = state.sections.filter(s => s.course_id === course.id);

        return `
            <div class="section-config-card" data-course-id="${course.id}">
                <div class="section-card-header">
                    <div class="section-course-info">
                        <h4>${escapeHtml(course.code)}</h4>
                        <p>${escapeHtml(course.name)}</p>
                    </div>
                    <div class="section-count-badge">
                        ${courseSections.length} ${courseSections.length === 1 ? 'section' : 'sections'}
                    </div>
                </div>

                <div class="sections-list-v2">
                    ${courseSections.map(section => `
                        <span class="section-badge ${section.is_custom_block ? 'custom-block' : ''}" 
                              title="${section.is_custom_block ? 'Custom Block - Straight scheduling' : 'Regular lecture'}">
                            ${escapeHtml(section.section_letter)}
                            ${section.is_custom_block ? '🎓' : ''}
                            <button onclick="event.stopPropagation(); deleteSection('${section.id}', '${course.id}')" 
                                    title="Remove section">×</button>
                        </span>
                    `).join('')}
                    <button class="add-section-btn" onclick="openAddSectionModal('${course.id}', '${escapeHtml(course.code)}')">
                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                        </svg>
                        Add Section
                    </button>
                </div>
            </div>
        `;
    }).join('');

    console.log(`✅ Rendered ${coursesWithEligibility.length} section config cards`);
}

// ══════════════════════════════════════════════════════════════════════
// ELIGIBILITY & SECTION MANAGEMENT
// ══════════════════════════════════════════════════════════════════════

async function toggleEligibility(facultyId, courseId, isEligible) {
    // Track change instead of immediately saving
    if (!state.unsavedEligibilityChanges.has(courseId)) {
        state.unsavedEligibilityChanges.set(courseId, new Map());
    }

    state.unsavedEligibilityChanges.get(courseId).set(facultyId, isEligible);
    state.hasUnsavedChanges = true;

    // Update the "Save All" button to show unsaved state
    updateSaveAllButton();

    // Update badge count (optimistic UI update)
    updateEligibilityCount(courseId);
}

async function toggleSectionConfig(courseId, sectionLetter, isEnabled) {
    try {
        if (isEnabled) {
            // Enable section
            const response = await fetch('/api/course-sections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    course_id: courseId,
                    section_letter: sectionLetter,
                    school_year: state.schoolYear,
                    semester: state.semester
                })
            });

            if (!response.ok) throw new Error('Failed to enable section');

            const newSection = await response.json();
            state.sections.push(newSection);

            showToast(`Section ${sectionLetter} enabled`, 'success');
        } else {
            // Disable section
            const section = state.sections.find(s =>
                s.course_id === courseId && s.section_letter === sectionLetter
            );

            if (section && section.id) {
                const response = await fetch(`/api/course-sections/${section.id}`, {
                    method: 'DELETE'
                });

                if (!response.ok) throw new Error('Failed to disable section');

                state.sections = state.sections.filter(s => s.id !== section.id);

                showToast(`Section ${sectionLetter} disabled`, 'info');
            }
        }

        // Update badge count
        updateSectionCount(courseId);
        updateStepCompletion();

    } catch (error) {
        console.error('Error toggling section:', error);
        showToast('Failed to update section', 'error');

        // Revert checkbox
        const checkbox = document.querySelector(
            `.section-config-card[data-course-id="${courseId}"] input[onchange*="${sectionLetter}"]`
        );
        if (checkbox) checkbox.checked = !isEnabled;
    }
}

function updateEligibilityCount(courseId) {
    const card = document.querySelector(`.eligibility-card[data-course-id="${courseId}"]`);
    if (!card) return;

    // Count includes both saved eligibility and unsaved changes
    let count = state.eligibility.filter(e => e.course_id === courseId).length;

    // Adjust for unsaved changes
    if (state.unsavedEligibilityChanges.has(courseId)) {
        const changes = state.unsavedEligibilityChanges.get(courseId);
        changes.forEach((isEligible, facultyId) => {
            const existsInSaved = state.eligibility.some(e =>
                e.course_id === courseId && e.faculty_id === facultyId
            );

            if (isEligible && !existsInSaved) count++; // Adding new
            if (!isEligible && existsInSaved) count--; // Removing existing
        });
    }

    const badge = card.querySelector('.eligibility-count-badge');
    if (badge) {
        badge.textContent = `${count} ${count === 1 ? 'faculty' : 'faculty'}`;
    }
}

function updateSaveAllButton() {
    const btn = document.getElementById('save-all-eligibility');
    if (!btn) return;

    if (state.hasUnsavedChanges) {
        btn.classList.add('has-changes');
        btn.disabled = false;
        const changeCount = Array.from(state.unsavedEligibilityChanges.values())
            .reduce((sum, map) => sum + map.size, 0);
        btn.querySelector('.change-count').textContent = changeCount;
        btn.querySelector('.change-count').style.display = 'inline';
    } else {
        btn.classList.remove('has-changes');
        btn.querySelector('.change-count').style.display = 'none';
    }
}

async function saveAllEligibility() {
    if (!state.hasUnsavedChanges) return;

    const btn = document.getElementById('save-all-eligibility');
    const spinner = btn.querySelector('.btn-spinner');
    const btnText = btn.querySelector('.btn-text');

    // Show loading state
    btn.disabled = true;
    spinner.style.display = 'inline-block';
    btnText.textContent = 'Saving...';

    try {
        const operations = [];

        // Process all unsaved changes
        for (const [courseId, facultyMap] of state.unsavedEligibilityChanges) {
            for (const [facultyId, isEligible] of facultyMap) {
                if (isEligible) {
                    // Add eligibility
                    operations.push(
                        fetch('/api/faculty-course-units', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ faculty_id: facultyId, course_id: courseId })
                        }).then(async (response) => {
                            if (!response.ok) throw new Error('Failed to add eligibility');
                            const newEntry = await response.json();
                            state.eligibility.push(newEntry);
                        })
                    );
                } else {
                    // Remove eligibility
                    const entry = state.eligibility.find(e =>
                        e.faculty_id === facultyId && e.course_id === courseId
                    );

                    if (entry && entry.id) {
                        operations.push(
                            fetch(`/api/faculty-course-units/${entry.id}`, {
                                method: 'DELETE'
                            }).then((response) => {
                                if (!response.ok) throw new Error('Failed to remove eligibility');
                                state.eligibility = state.eligibility.filter(e => e.id !== entry.id);
                            })
                        );
                    }
                }
            }
        }

        // Execute all operations
        await Promise.all(operations);

        // Clear unsaved changes
        state.unsavedEligibilityChanges.clear();
        state.hasUnsavedChanges = false;

        // Update UI
        updateStepCompletion();
        updateSaveAllButton();
        btnText.textContent = 'Save All';
        spinner.style.display = 'none';

        // Show success animation
        showStepCompletionAnimation(1);
        showToast('All eligibility changes saved successfully!', 'success');

        // Auto-navigate to Step 2 after short delay
        setTimeout(() => {
            navigateToStep(2);
        }, 1500);

    } catch (error) {
        console.error('Error saving eligibility:', error);
        showToast('Failed to save some changes. Please try again.', 'error');
        btnText.textContent = 'Save All';
        spinner.style.display = 'none';
        btn.disabled = false;
    }
}

function showStepCompletionAnimation(stepNum) {
    const stepItem = document.querySelector(`.step-item[data-step="${stepNum}"]`);
    if (!stepItem) return;

    // Add completion animation class
    stepItem.classList.add('completing');

    setTimeout(() => {
        stepItem.classList.remove('completing');
        stepItem.classList.add('completed');
    }, 800);
}

function updateSectionCount(courseId) {
    const card = document.querySelector(`.section-config-card[data-course-id="${courseId}"]`);
    if (!card) return;

    const count = state.sections.filter(s => s.course_id === courseId).length;
    const badge = card.querySelector('.section-count-badge');
    if (badge) {
        badge.textContent = `${count} ${count === 1 ? 'section' : 'sections'}`;
    }
}

// ══════════════════════════════════════════════════════════════════════
// SEARCH FILTERS
// ══════════════════════════════════════════════════════════════════════

function getDepartmentFromCourseCode(courseCode) {
    const code = courseCode.toUpperCase();
    if (code.includes('NSTP')) return 'nstp';
    if (code.includes('HUME')) return 'hume';
    return 'cerp'; // Default to CERP
}

function filterEligibilityByDept() {
    const select = document.getElementById('eligibility-dept-filter');
    const selectedDept = select.value;

    document.querySelectorAll('.eligibility-card').forEach(card => {
        const courseInfo = card.querySelector('.eligibility-course-info h4');
        const courseCode = courseInfo?.textContent || '';
        const dept = getDepartmentFromCourseCode(courseCode);

        if (selectedDept === 'all' || dept === selectedDept) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Also apply search filter
    filterEligibilityCards();
}

function filterEligibilityCards() {
    const input = document.getElementById('eligibility-search');
    const select = document.getElementById('eligibility-dept-filter');
    if (!input) return;

    const query = input.value.toLowerCase().trim();
    const selectedDept = select ? select.value : 'all';

    document.querySelectorAll('.eligibility-card').forEach(card => {
        const courseInfo = card.querySelector('.eligibility-course-info');
        const code = courseInfo?.querySelector('h4')?.textContent.toLowerCase() || '';
        const name = courseInfo?.querySelector('p')?.textContent.toLowerCase() || '';
        const dept = getDepartmentFromCourseCode(code);

        const matchesSearch = code.includes(query) || name.includes(query);
        const matchesDept = selectedDept === 'all' || dept === selectedDept;

        card.style.display = (matchesSearch && matchesDept) ? '' : 'none';
    });
}

function filterSectionsByDept() {
    const select = document.getElementById('sections-dept-filter');
    const selectedDept = select.value;

    document.querySelectorAll('.section-config-card').forEach(card => {
        const courseInfo = card.querySelector('.section-course-info h4');
        const courseCode = courseInfo?.textContent || '';
        const dept = getDepartmentFromCourseCode(courseCode);

        if (selectedDept === 'all' || dept === selectedDept) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Also apply search filter
    filterSectionCards();
}

function filterSectionCards() {
    const input = document.getElementById('sections-search');
    const select = document.getElementById('sections-dept-filter');
    if (!input) return;

    const query = input.value.toLowerCase().trim();
    const selectedDept = select ? select.value : 'all';

    document.querySelectorAll('.section-config-card').forEach(card => {
        const courseInfo = card.querySelector('.section-course-info');
        const code = courseInfo?.querySelector('h4')?.textContent.toLowerCase() || '';
        const name = courseInfo?.querySelector('p')?.textContent.toLowerCase() || '';
        const dept = getDepartmentFromCourseCode(code);

        const matchesSearch = code.includes(query) || name.includes(query);
        const matchesDept = selectedDept === 'all' || dept === selectedDept;

        card.style.display = (matchesSearch && matchesDept) ? '' : 'none';
    });
}

// ══════════════════════════════════════════════════════════════════════
// EXPOSE GLOBALS
// ══════════════════════════════════════════════════════════════════════

window.dismissOnboarding = dismissOnboarding;
window.navigateToStep = navigateToStep;
window.selectFaculty = selectFaculty;
window.clearFacultySelection = clearFacultySelection;
window.toggleCourseExpansion = toggleCourseExpansion;
window.toggleSection = toggleSection;
window.saveAssignments = saveAssignments;
window.filterCourses = filterCourses;
window.openLegend = openLegend;
window.closeLegend = closeLegend;
window.toggleEligibility = toggleEligibility;
window.toggleSectionConfig = toggleSectionConfig;
window.filterEligibilityCards = filterEligibilityCards;
window.filterSectionCards = filterSectionCards;
window.filterEligibilityByDept = filterEligibilityByDept;
window.filterSectionsByDept = filterSectionsByDept;


// ══════════════════════════════════════════════════════════════════════
// LOADING STATES
// ══════════════════════════════════════════════════════════════════════

function showLoadingStates() {
    const coursesList = document.getElementById('courses-list-v2');
    const facultyGrid = document.getElementById('faculty-grid-v2');

    if (coursesList) {
        coursesList.innerHTML = `
            <div class="loading-skeleton-list">
                ${Array(5).fill().map(() => '<div class="skeleton-course-card"></div>').join('')}
            </div>
        `;
    }

    if (facultyGrid) {
        facultyGrid.innerHTML = `
            ${Array(8).fill().map(() => '<div class="skeleton-faculty-card"></div>').join('')}
        `;
    }
}


function toggleEditMode(courseId) {
    if (state.editingCourseId === courseId) {
        // Save mode - lock the card (but changes are only tracked, not saved yet)
        state.editingCourseId = null;
    } else {
        // Warn if there are unsaved changes in another card
        if (state.editingCourseId && state.unsavedEligibilityChanges.has(state.editingCourseId)) {
            const proceed = confirm('You have unsaved changes in another course. Those changes will be kept but not saved until you click "Save All". Continue?');
            if (!proceed) return;
        }

        // Edit mode - unlock the card
        state.editingCourseId = courseId;
    }

    // Re-render to update UI
    renderEligibilityGrid();
}

window.toggleEditMode = toggleEditMode;


// ══════════════════════════════════════════════════════════════════════
// ADD SECTION MODAL
// ══════════════════════════════════════════════════════════════════════

let currentModalCourseId = null;

function openAddSectionModal(courseId, courseCode) {
    currentModalCourseId = courseId;

    const modal = document.getElementById('add-section-modal');
    const courseCodeSpan = document.getElementById('modal-course-code');
    const sectionInput = document.getElementById('section-name-input');
    const regularRadio = document.querySelector('input[name="section-type"][value="regular"]');

    if (courseCodeSpan) courseCodeSpan.textContent = courseCode;
    if (sectionInput) sectionInput.value = '';
    if (regularRadio) regularRadio.checked = true;

    toggleCustomBlockFields(false);

    if (modal) modal.classList.add('active');
}

function closeAddSectionModal(event) {
    if (!event || event.target.id === 'add-section-modal' || event.type === 'click') {
        const modal = document.getElementById('add-section-modal');
        if (modal) modal.classList.remove('active');
        currentModalCourseId = null;
    }
}

function toggleCustomBlockFields(show) {
    const fields = document.getElementById('custom-block-fields');
    if (fields) {
        fields.style.display = show ? 'block' : 'none';
    }
}

async function submitAddSection() {
    if (!currentModalCourseId) {
        showToast('No course selected', 'error');
        return;
    }

    const sectionInput = document.getElementById('section-name-input');
    const sectionName = sectionInput?.value.trim();

    if (!sectionName) {
        showToast('Please enter a section name', 'warning');
        return;
    }

    const isCustomBlock = document.querySelector('input[name="section-type"][value="custom"]')?.checked || false;
    const unitsInput = document.getElementById('custom-units-input');
    const roomInput = document.getElementById('custom-room-input');

    const payload = {
        course_id: currentModalCourseId,
        section_letter: sectionName,
        school_year: state.schoolYear,
        semester: state.semester,
        is_custom_block: isCustomBlock
    };

    if (isCustomBlock) {
        if (unitsInput?.value) {
            payload.units = parseInt(unitsInput.value);
        }
        if (roomInput?.value.trim()) {
            payload.custom_room_name = roomInput.value.trim();
        }
    }

    const btn = document.querySelector('#add-section-modal .btn-primary-v2');
    const spinner = document.getElementById('add-section-spinner');

    try {
        if (btn) btn.disabled = true;
        if (spinner) spinner.style.display = 'block';

        const response = await fetch('/api/course-sections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add section');
        }

        const newSection = await response.json();
        state.sections.push(newSection);

        showToast(`Section "${sectionName}" added${isCustomBlock ? ' as custom block' : ''}!`, 'success');

        closeAddSectionModal();
        renderSectionsGrid();
        updateStepCompletion();

    } catch (error) {
        console.error('Error adding section:', error);
        showToast(error.message || 'Failed to add section', 'error');
    } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
    }
}

async function deleteSection(sectionId, courseId) {
    if (!confirm('Remove this section? This will also remove any faculty assignments for this section.')) {
        return;
    }

    try {
        const response = await fetch(`/api/course-sections/${sectionId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete section');

        // Remove from state
        state.sections = state.sections.filter(s => s.id !== sectionId);

        showToast('Section removed', 'info');
        renderSectionsGrid();
        updateStepCompletion();

    } catch (error) {
        console.error('Error deleting section:', error);
        showToast('Failed to remove section', 'error');
    }
}

// Expose modal functions
window.openAddSectionModal = openAddSectionModal;
window.closeAddSectionModal = closeAddSectionModal;
window.toggleCustomBlockFields = toggleCustomBlockFields;
window.submitAddSection = submitAddSection;
window.deleteSection = deleteSection;


// ══════════════════════════════════════════════════════════════════════
// STEP 3: ROOM ALLOCATION
// ══════════════════════════════════════════════════════════════════════

function renderRoomsGrid() {
    const grid = document.getElementById('rooms-grid');
    if (!grid) {
        console.error('❌ rooms-grid element not found!');
        return;
    }

    console.log('Rendering rooms grid:', {
        courses: state.courses.length,
        sections: state.sections.length,
        rooms: state.availableRooms.length
    });

    if (state.courses.length === 0) {
        grid.innerHTML = `
            <div class="empty-state-full" style="grid-column: 1/-1;">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <rect x="20" y="30" width="80" height="60" rx="8" fill="#fef2f2" stroke="#6b0f1a" stroke-width="3"/>
                    <path d="M40 40h40M40 55h40M40 70h40" stroke="#6b0f1a" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <h3>No Courses Available</h3>
                <p>Configure courses and sections first before allocating rooms.</p>
            </div>
        `;
        return;
    }

    // Group sections by course, filter to show only courses with sections AND faculty assignments
    const coursesWithSections = state.courses.map(course => {
        const courseSections = state.sections.filter(s => s.course_id === course.id);
        return { course, sections: courseSections };
    })
        .filter(item => item.sections.length > 0) // Only courses with sections
        .filter(item => {
            // Only courses with at least one faculty assignment
            return state.assignments.some(a => a.course_id === item.course.id);
        });

    if (coursesWithSections.length === 0) {
        grid.innerHTML = `
            <div class="empty-state-full" style="grid-column: 1/-1;">
                <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                    <circle cx="60" cy="60" r="45" fill="#fef2f2" stroke="#6b0f1a" stroke-width="3"/>
                    <path d="M45 55l10 10 20-20" stroke="#6b0f1a" stroke-width="3" stroke-linecap="round" fill="none"/>
                </svg>
                <h3>No Courses Ready for Room Allocation</h3>
                <p>Complete Steps 2 and 3 first: configure sections and assign faculty before allocating rooms.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = coursesWithSections.map(({ course, sections }) => {
        return `
            <div class="room-allocation-card" data-course-id="${course.id}">
                <div class="room-card-header">
                    <div class="room-course-info">
                        <h4>${escapeHtml(course.code)}</h4>
                        <p>${escapeHtml(course.name)}</p>
                    </div>
                    <div class="room-count-badge">
                        ${sections.length} ${sections.length === 1 ? 'section' : 'sections'}
                    </div>
                </div>

                <div class="room-allocations-list">
                    ${sections.map(section => {
            const allocation = state.roomAllocations.find(a =>
                a.course_id === course.id && a.section_letter === section.section_letter
            );
            const currentRoom = allocation?.custom_room_name ||
                (allocation?.room_id ? getRoomNameById(allocation.room_id) : '');

            return `
                            <div class="room-allocation-row">
                                <div class="section-label-v2">
                                    <span class="section-badge ${section.is_custom_block ? 'custom-block' : ''}">
                                        ${escapeHtml(section.section_letter)}
                                        ${section.is_custom_block ? '🎓' : ''}
                                    </span>
                                </div>
                                ${section.is_custom_block && section.custom_room_name ? `
                                    <input type="text" 
                                           class="room-input-v2" 
                                           value="${escapeHtml(section.custom_room_name)}"
                                           readonly
                                           title="Room set in Step 2 for custom block">
                                ` : `
                                    <select class="room-select-v2" 
                                            onchange="saveRoomAllocation('${course.id}', '${section.section_letter}', this.value)"
                                            data-course="${course.id}" 
                                            data-section="${section.section_letter}">
                                        <option value="">Select room...</option>
                                        ${state.availableRooms.map(room => `
                                            <option value="${escapeHtml(room.name)}" ${currentRoom === room.name ? 'selected' : ''}>
                                                ${escapeHtml(room.name)}
                                            </option>
                                        `).join('')}
                                        <option value="__custom__" ${allocation?.custom_room_name && !state.availableRooms.some(r => r.name === currentRoom) ? 'selected' : ''}>
                                            Custom Room...
                                        </option>
                                    </select>
                                `}
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    }).join('');

    console.log(`✅ Rendered ${coursesWithSections.length} room allocation cards`);
}

function getRoomNameById(roomId) {
    // In future, could map room IDs to names from rooms table
    // For now, just return from available rooms
    return state.availableRooms.find(r => r.id === roomId)?.name || '';
}

async function saveRoomAllocation(courseId, sectionLetter, selectedValue) {
    console.log('💾 Saving room allocation:', { courseId, sectionLetter, selectedValue });

    if (!selectedValue) {
        // Clear allocation
        const allocation = state.roomAllocations.find(a =>
            a.course_id === courseId && a.section_letter === sectionLetter
        );
        if (allocation && allocation.id) {
            await deleteRoomAllocation(allocation.id);
        }
        return;
    }

    if (selectedValue === '__custom__') {
        // Prompt for custom room name
        const customRoom = prompt('Enter custom room name:');
        if (!customRoom) return;

        await saveRoomAllocationAPI(courseId, sectionLetter, null, customRoom);
    } else {
        // Use predefined room
        await saveRoomAllocationAPI(courseId, sectionLetter, null, selectedValue);
    }
}

async function saveRoomAllocationAPI(courseId, sectionLetter, roomId, customRoomName) {
    try {
        const payload = {
            course_id: courseId,
            section_letter: sectionLetter,
            school_year: state.schoolYear,
            semester: state.semester,
            room_id: roomId,
            custom_room_name: customRoomName
        };

        console.log('📤 Sending room allocation to API:', payload);

        const response = await fetch('/api/section-rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Room allocation API error:', response.status, errorText);
            throw new Error(`Failed to save room allocation: ${response.status}`);
        }

        const result = await response.json();
        console.log('✅ Room allocation saved:', result);

        // Update state
        const existingIndex = state.roomAllocations.findIndex(a =>
            a.course_id === courseId && a.section_letter === sectionLetter
        );

        if (existingIndex >= 0) {
            state.roomAllocations[existingIndex] = result;
        } else {
            state.roomAllocations.push(result);
        }

        showToast(`Room allocated for section ${sectionLetter}`, 'success');
        updateStepCompletion();
        updateCompleteButton();

    } catch (error) {
        console.error('Error saving room allocation:', error);
        showToast('Failed to save room allocation', 'error');
    }
}

async function deleteRoomAllocation(allocationId) {
    try {
        const response = await fetch(`/api/section-rooms/${allocationId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete room allocation');

        state.roomAllocations = state.roomAllocations.filter(a => a.id !== allocationId);
        showToast('Room allocation removed', 'info');
        updateStepCompletion();

    } catch (error) {
        console.error('Error deleting room allocation:', error);
        showToast('Failed to remove room allocation', 'error');
    }
}

// Room search/filter functions
function filterRoomsByDept() {
    const select = document.getElementById('rooms-dept-filter');
    const selectedDept = select.value;

    document.querySelectorAll('.room-allocation-card').forEach(card => {
        const courseInfo = card.querySelector('.room-course-info h4');
        const courseCode = courseInfo?.textContent || '';
        const dept = getDepartmentFromCourseCode(courseCode);

        if (selectedDept === 'all' || dept === selectedDept) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    filterRoomCards();
}

function filterRoomCards() {
    const input = document.getElementById('rooms-search');
    const select = document.getElementById('rooms-dept-filter');
    if (!input) return;

    const query = input.value.toLowerCase().trim();
    const selectedDept = select ? select.value : 'all';

    document.querySelectorAll('.room-allocation-card').forEach(card => {
        const courseInfo = card.querySelector('.room-course-info');
        const code = courseInfo?.querySelector('h4')?.textContent.toLowerCase() || '';
        const name = courseInfo?.querySelector('p')?.textContent.toLowerCase() || '';
        const dept = getDepartmentFromCourseCode(code);

        const matchesSearch = code.includes(query) || name.includes(query);
        const matchesDept = selectedDept === 'all' || dept === selectedDept;

        card.style.display = (matchesSearch && matchesDept) ? '' : 'none';
    });
}

// Expose functions
window.saveRoomAllocation = saveRoomAllocation;
window.filterRoomsByDept = filterRoomsByDept;
window.filterRoomCards = filterRoomCards;


// ══════════════════════════════════════════════════════════════════════
// WORKFLOW COMPLETION
// ══════════════════════════════════════════════════════════════════════

function completeWorkflow() {
    // Show step 4 completion animation
    showStepCompletionAnimation(4);

    // Show success modal after short delay
    setTimeout(() => {
        const modal = document.getElementById('success-modal');
        if (modal) {
            modal.style.display = 'flex';

            // Play "ting" sound if available (optional)
            try {
                const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBzGH0fPTgjMGHm7A7+OZFQ0XZrbi7a5aEwxPqeTxuWgeBDGN1PLPfzAHJHzL8N+UQw==');
                audio.volume = 0.3;
                audio.play().catch(() => { }); // Ignore if fails
            } catch (e) { }
        }
    }, 600);
}

function closeSuccessModal() {
    const modal = document.getElementById('success-modal');
    if (modal) {
        modal.style.animation = 'modalFadeIn 0.2s ease-out reverse';
        setTimeout(() => {
            modal.style.display = 'none';
            modal.style.animation = '';
        }, 200);
    }
}

// Show/hide "Complete Setup" button based on step 4 completion
function updateCompleteButton() {
    const btn = document.getElementById('btn-complete-workflow');
    if (!btn) return;

    // Show button only when on Step 4 and step is complete
    const onStep4 = state.currentStep === 4;
    const step4Complete = state.roomAllocations.length > 0;

    btn.style.display = (onStep4 && step4Complete) ? 'inline-flex' : 'none';
}

// Call this whenever room allocations change or step changes
document.addEventListener('DOMContentLoaded', () => {
    // Update complete button visibility
    const originalNavigate = window.navigateToStep;
    window.navigateToStep = function (step) {
        originalNavigate(step);
        setTimeout(updateCompleteButton, 100);
    };
});
