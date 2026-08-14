/* ══════════════════════════════════════════════════════════════
   FSR Admin - Full Faculty Service Record (Sections I–IX)
   ══════════════════════════════════════════════════════════════ */

let fsrMembers = [];
let fsrCurrentMemberId = null;
let fsrCurrentMemberData = null;
// Default to current school year: if month >= August, use current year, otherwise previous year
let _currentYear = new Date().getFullYear();
let _month = new Date().getMonth(); // 0-11, where 7 = August
let _schoolYearStart = _month >= 7 ? _currentYear : _currentYear - 1;
let fsrCurrentYear = _schoolYearStart + '-' + (_schoolYearStart + 1);
// Default to 1st semester (August-December) if month >= 7 and < 0 (Jan), otherwise 2nd semester
let fsrCurrentSemester = (_month >= 7 || _month < 1) ? '1st Semester' : '2nd Semester';

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    fsrLoadMembers();
    fsrPopulateYears();
    // Set default semester based on current date
    const semSelect = document.getElementById('fsrSemesterSelect');
    if (semSelect) {
        semSelect.value = fsrCurrentSemester;
    }
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.fsr-download-group')) {
            document.getElementById('fsrDownloadDropdown')?.classList.remove('open');
        }
    });
});

async function fsrLoadMembers() {
    try {
        const res = await fetch('/api/members');
        if (!res.ok) throw new Error('Failed to fetch members');
        fsrMembers = await res.json();
        fsrPopulateDropdown();
    } catch (e) {
        console.error('FSR: Error loading members:', e);
        fsrShowError('Failed to load members');
    }
}

function fsrPopulateDropdown() {
    const sel = document.getElementById('fsrMemberSelect');
    if (!sel) return;

    // Sort alphabetically by last name
    fsrMembers.sort((a, b) => (a.last || '').localeCompare(b.last || ''));

    // Clear and populate
    sel.innerHTML = '';
    fsrMembers.forEach((m, index) => {
        const o = document.createElement('option');
        o.value = m.uid;
        o.textContent = `${m.last || ''}, ${m.first || ''} ${m.middle || ''}`.trim();
        sel.appendChild(o);
    });

    // Select first member by default
    if (fsrMembers.length > 0) {
        sel.value = fsrMembers[0].uid;
        fsrOnMemberChange();
    }
}

function fsrPopulateYears() {
    const sel = document.getElementById('fsrYearSelect');
    if (!sel) return;

    const currentYear = new Date().getFullYear();
    const month = new Date().getMonth();
    const schoolYearStart = month >= 7 ? currentYear : currentYear - 1;
    const startYear = 2020;

    sel.innerHTML = '';
    for (let year = currentYear; year >= startYear; year--) {
        const o = document.createElement('option');
        const academicYear = `${year}-${year + 1}`;
        o.value = academicYear;
        o.textContent = academicYear;
        // Select current school year by default
        if (year === schoolYearStart) o.selected = true;
        sel.appendChild(o);
    }
}

function fsrOnMemberChange() {
    const sel = document.getElementById('fsrMemberSelect');
    fsrCurrentMemberId = sel.value;
    if (fsrCurrentMemberId) {
        fsrCurrentMemberData = fsrMembers.find(m => m.uid === fsrCurrentMemberId);
        document.getElementById('fsrDownloadBtn').disabled = false;
        fsrLoadPreview();
    } else {
        document.getElementById('fsrDownloadBtn').disabled = true;
        fsrCurrentMemberData = null;
        fsrShowEmpty();
    }
}

function fsrOnFilterChange() {
    const yearSel = document.getElementById('fsrYearSelect');
    const semSel = document.getElementById('fsrSemesterSelect');
    fsrCurrentYear = yearSel.value;
    fsrCurrentSemester = semSel.value;
    if (fsrCurrentMemberId) {
        fsrLoadPreview();
    }
}

// Download dropdown toggle
window.toggleDownloadDropdown = function (event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('fsrDownloadDropdown');
    dropdown.classList.toggle('open');
};


// ── Data Loading ──────────────────────────────────────────────
async function fsrLoadPreview() {
    if (!fsrCurrentMemberId) return;
    fsrShowLoading();
    try {
        const semNum = fsrCurrentSemester.charAt(0); // "1st Semester" -> "1"
        const [resR, resE, resS, resC] = await Promise.all([
            fetch(`/api/research?member_id=${fsrCurrentMemberId}`),
            fetch(`/api/extensions?member_id=${fsrCurrentMemberId}`),
            fetch('/api/schedules'),
            fetch(`/api/configured-subjects?school_year=${fsrCurrentYear}&semester=${semNum}`)
        ]);
        const research = resR.ok ? await resR.json() : [];
        const extensions = resE.ok ? await resE.json() : [];
        const configuredSubjects = resC.ok ? await resC.json() : [];
        console.log('📦 Configured subjects loaded:', configuredSubjects.length, configuredSubjects);

        let schedules = [];
        if (resS.ok) {
            const all = await resS.json();
            const ln = (fsrCurrentMemberData.last || '').toLowerCase();
            // Filter schedules by year and semester
            schedules = all.filter(s => {
                const profMatch = ln && (s.prof || '').toLowerCase().includes(ln);
                // API returns schoolYear (camelCase)
                const yearMatch = s.schoolYear === fsrCurrentYear;
                // Semester format: database stores "1" or "2", UI displays "1st Semester"/"2nd Semester"
                // Extract just the number from the filter
                const semesterMatch = s.semester === semNum;
                console.log('Schedule filter:', {
                    prof: s.prof,
                    profMatch,
                    schoolYear: s.schoolYear,
                    yearMatch,
                    semester: s.semester,
                    semesterMatch,
                    filterYear: fsrCurrentYear,
                    filterSem: fsrCurrentSemester,
                    extractedSemNum: semNum
                });
                return profMatch && yearMatch && semesterMatch;
            });
            console.log('Filtered schedules:', schedules.length, 'out of', all.length);
        }

        // Filter configured subjects for this faculty
        const ln = (fsrCurrentMemberData.last || '').toLowerCase();
        console.log('🔍 Filtering configured subjects for faculty:', ln);
        console.log('📦 All configured subjects:', configuredSubjects);
        console.log('📦 All schedules:', schedules);

        const unscheduledSubjects = configuredSubjects.filter(cs => {
            const profMatch = ln && (cs.prof || '').toLowerCase().includes(ln);
            console.log('  - Subject:', cs.subjCode, 'Section:', cs.section, 'Prof:', cs.prof, 'Match:', profMatch);
            // Check if this subject is already scheduled (match by subject code only, ignore section)
            // Because the same subject can be scheduled with different sections
            const isScheduled = schedules.some(s => {
                const codeMatch = s.subjCode === cs.subjCode;
                console.log('    Comparing with schedule:', s.subjCode, s.section, 'CodeMatch:', codeMatch);
                return codeMatch;
            });
            console.log('    Already scheduled:', isScheduled);
            return profMatch && !isScheduled;
        });
        console.log('📦 Unscheduled configured subjects:', unscheduledSubjects.length, unscheduledSubjects);

        fsrRender(fsrCurrentMemberData, research, extensions, schedules, unscheduledSubjects);
    } catch (e) {
        console.error('FSR load error:', e);
        fsrShowError('Failed to load FSR data');
    }
}

// ── Download ──────────────────────────────────────────────────
async function fsrDownload(format) {
    if (!fsrCurrentMemberId) return;

    // Close dropdown
    document.getElementById('fsrDownloadDropdown').classList.remove('open');

    const btn = document.getElementById('fsrDownloadBtn');
    btn.disabled = true;
    btn.innerHTML = '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>';

    try {
        if (format === 'pdf') {
            // Client-side PDF generation from the preview
            await fsrDownloadPDF();
        } else {
            // Server-side Excel generation
            const res = await fetch(`/api/generate-fsr/${fsrCurrentMemberId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    semester: fsrCurrentSemester,
                    academic_year: fsrCurrentYear,
                    format: format
                })
            });
            if (!res.ok) throw new Error('Generation failed');

            const data = await res.json();

            if (!data.success || !data.download_url) {
                throw new Error(data.error || 'Failed to get download URL');
            }

            // Fetch the file from Supabase Storage and trigger download
            const fileRes = await fetch(data.download_url);
            if (!fileRes.ok) throw new Error('Failed to fetch file');

            const blob = await fileRes.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.file_name || `FSR_${fsrCurrentMemberData.last || 'Member'}_${fsrCurrentSemester.replace(' ', '_')}_${fsrCurrentYear.replace('-', '_')}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            console.log('✓ FSR downloaded:', data.file_name);
        }
    } catch (e) {
        console.error('FSR download error:', e);
        alert('Failed to download FSR: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>';
    }
}

async function fsrDownloadPDF() {
    // Use browser's native print dialog for better control and preview
    window.print();
}


// ── Helpers ───────────────────────────────────────────────────
function fsrFmtDate(d) {
    if (!d) return 'N/A';
    try { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' }); }
    catch { return d; }
}

function fsrFmtRange(start, end) {
    if (!start || !end) return '';
    const [hs, ms] = String(start).split(':').map(Number);
    const [he, me] = String(end).split(':').map(Number);
    const ps = hs >= 12 ? 'PM' : 'AM', pe = he >= 12 ? 'PM' : 'AM';
    const hs12 = hs > 12 ? hs - 12 : (hs === 0 ? 12 : hs);
    const he12 = he > 12 ? he - 12 : (he === 0 ? 12 : he);
    if (ps === pe) return `${hs12}:${String(ms).padStart(2, '0')}-${he12}:${String(me).padStart(2, '0')} ${pe}`;
    return `${hs12}:${String(ms).padStart(2, '0')} ${ps}-${he12}:${String(me).padStart(2, '0')} ${pe}`;
}

const FSR_DAY_ABBR = { Monday: 'M', Tuesday: 'T', Wednesday: 'W', Thursday: 'TH', Friday: 'F', Saturday: 'S' };

function fsrConsolidateSchedules(schedules) {
    const map = {};
    (schedules || []).forEach(s => {
        const key = `${s.subjCode}||${s.room}||${s.start}||${s.end}`;
        if (!map[key]) map[key] = { ...s, days: [] };
        const abbr = FSR_DAY_ABBR[s.day] || (s.day || '').slice(0, 2).toUpperCase();
        if (abbr && !map[key].days.includes(abbr)) map[key].days.push(abbr);
    });
    return Object.values(map).sort((a, b) => (a.subjCode || '').localeCompare(b.subjCode || ''));
}

// ── State Displays ────────────────────────────────────────────
function fsrShowEmpty() {
    document.getElementById('fsrPreviewContent').innerHTML = `
        <div class="fsr-empty-state">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <h3>No Member Selected</h3><p>Select a member to preview their Faculty Service Record</p>
        </div>`;
}
function fsrShowLoading() {
    document.getElementById('fsrPreviewContent').innerHTML = `
        <div class="fsr-loading-state"><div class="fsr-spinner"></div><p>Loading FSR data...</p></div>`;
}
function fsrShowError(msg) {
    document.getElementById('fsrPreviewContent').innerHTML = `
        <div class="fsr-error-state">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <h3>Error</h3><p>${msg}</p>
        </div>`;
}


// ══════════════════════════════════════════════════════════════
// MAIN RENDER — Full FSR Structure (Sections I through IX)
// ══════════════════════════════════════════════════════════════
function fsrRender(member, research, extensions, schedules, unscheduledSubjects) {
    unscheduledSubjects = unscheduledSubjects || [];
    const el = document.getElementById('fsrPreviewContent');

    // Categorize extensions
    const mainExt = extensions.filter(e => e.type === 'extensions' || !e.type);
    const trainings = extensions.filter(e => e.type === 'training');
    const infoDiss = extensions.filter(e => e.type === 'info_dissemination');
    const workshops = extensions.filter(e => e.type === 'community_service');
    const symposium = extensions.filter(e => e.type === 'symposium');
    const othersExt = extensions.filter(e => e.type === 'creative_work' || e.type === 'others');

    // Categorize research
    const proposals = research.filter(r => r.research_type === 'proposal');
    const implementations = research.filter(r => r.research_type !== 'proposal');

    // Categorize creative work from research
    const creative_b1 = research.filter(r => r.creative_type === 'oral_poster');
    const creative_b2 = research.filter(r => r.creative_type === 'proceedings');
    const creative_b3 = research.filter(r => r.creative_type === 'monographs');
    const creative_b4 = research.filter(r => r.creative_type === 'refereed_journals');
    const creative_b5 = research.filter(r => r.creative_type === 'book_chapters');
    const creative_b6 = research.filter(r => r.creative_type === 'books');
    const creative_b7 = research.filter(r => r.creative_type === 'others');

    // Consolidated schedules
    const teachingRows = fsrConsolidateSchedules(schedules);

    let html = `<div class="fsr-page"><div class="fsr-spreadsheet"><table class="fsr-table">`;

    // ── HEADER ──
    html += `
        <tr class="fsr-header-row"><th colspan="11">${member.last || ''}, ${member.first || ''} - ${fsrCurrentSemester} ${fsrCurrentYear}</th></tr>
        <tr>
            <th class="fsr-info-label">PRINTED NAME:</th>
            <th class="fsr-info-label" style="font-size:0.7rem;">(Family)</th>
            <td class="fsr-info-cell" colspan="2">${member.last || ''}</td>
            <th class="fsr-info-label" style="font-size:0.7rem;">(Given)</th>
            <td class="fsr-info-cell" colspan="2">${member.first || ''}</td>
            <th class="fsr-info-label" style="font-size:0.7rem;">(MI)</th>
            <td class="fsr-info-cell">${member.middle || ''}</td>
            <th class="fsr-info-label">RANK:</th>
            <td class="fsr-info-cell">${member.rank || 'N/A'}</td>
        </tr>
        <tr>
            <th class="fsr-info-label">HOME DEPARTMENT:</th>
            <td class="fsr-info-cell" colspan="5">${member.department || 'DCERP'}</td>
            <th class="fsr-info-label">HOME COLLEGE:</th>
            <td class="fsr-info-cell" colspan="4">${member.college || 'CHE'}</td>
        </tr>
        <tr class="fsr-spacer"><td colspan="11"></td></tr>`;

    // ── SECTION I: TEACHING LOAD ──
    html += `
        <tr class="fsr-section-row"><td colspan="11">I. TEACHING LOAD in the COLLEGE</td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="2">SUBJECT</th><th>SECTION CODE</th><th>ROOM</th><th>DAYS</th>
            <th>TIME</th><th>HOURS/WEEK</th><th>NO. OF STUDENTS</th><th>COURSE CREDIT</th>
            <th>STUDENT CREDIT UNITS</th><th>TEACHING LOAD CREDITS</th>
        </tr>`;

    if (teachingRows.length > 0 || unscheduledSubjects.length > 0) {
        // First show scheduled subjects
        teachingRows.forEach(row => {
            html += `<tr>
                <td colspan="2" style="font-weight:600;">${row.subjCode || ''}</td>
                <td style="text-align:center;color:#6b7280;font-style:italic;">—</td>
                <td style="text-align:center;">${row.room || ''}</td>
                <td style="text-align:center;">${row.days.join('/')}</td>
                <td style="text-align:center;">${fsrFmtRange(row.start, row.end)}</td>
                <td style="text-align:center;">—</td><td style="text-align:center;">—</td>
                <td style="text-align:center;">—</td><td style="text-align:center;">—</td>
                <td style="text-align:center;">—</td>
            </tr>`;
        });

        // Then show unscheduled subjects as TBA
        console.log('🎨 Rendering', unscheduledSubjects.length, 'unscheduled subjects in FSR');
        unscheduledSubjects.forEach(subj => {
            console.log('  - Adding TBA row for:', subj.subjCode, subj.subjName);
            html += `<tr style="background:#fef9e7;">
                <td colspan="2" style="font-weight:600;">${subj.subjCode || ''} - ${subj.subjName || ''}</td>
                <td style="text-align:center;">TBA</td>
                <td style="text-align:center;">TBA</td>
                <td style="text-align:center;">TBA</td>
                <td style="text-align:center;">TBA</td>
                <td style="text-align:center;">TBA</td>
                <td style="text-align:center;">—</td>
                <td style="text-align:center;">—</td><td style="text-align:center;">—</td>
                <td style="text-align:center;">—</td>
            </tr>`;
        });
    } else {
        html += `<tr><td colspan="11" class="fsr-italic-empty">No schedule entries found for this faculty member.</td></tr>`;
    }

    html += `
        <tr class="fsr-total-row">
            <td colspan="6">TOTAL Teaching Load Credits</td>
            <td style="text-align:center;">—</td><td style="text-align:center;">—</td>
            <td style="text-align:center;">—</td><td colspan="2" style="text-align:center;">—</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:18px;font-size:.78rem;color:#6b7280;font-style:italic;padding:2px 8px;">¹</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:18px;font-size:.78rem;color:#6b7280;font-style:italic;padding:2px 8px;">²</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:18px;font-size:.78rem;color:#6b7280;font-style:italic;padding:2px 8px;">³</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="padding:6px 8px;font-size:.8rem;">
            <strong>Concurrent teaching load outside the college.</strong>&nbsp;Write NONE whenever applicable.
        </td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>
        <tr>
            <td colspan="3" style="text-align:center;font-weight:600;">(NONE)</td>
            <td colspan="4" style="text-align:center;font-weight:600;">(NONE)</td>
            <td colspan="4" style="text-align:center;font-weight:600;">(NONE)</td>
        </tr>
        <tr>
            <td colspan="3" style="font-weight:700;border-top:1px solid #000;">COLLEGE OUTSIDE U.P. SYSTEM</td>
            <td colspan="4" style="text-align:center;border-top:1px solid #000;">No. of subjects</td>
            <td colspan="4" style="text-align:center;border-top:1px solid #000;">No. of units (w/o multipliers)</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>
        <tr>
            <td colspan="3" style="text-align:center;font-weight:600;">(NONE)</td>
            <td colspan="4" style="text-align:center;font-weight:600;">(NONE)</td>
            <td colspan="4" style="text-align:center;font-weight:600;">(NONE)</td>
        </tr>
        <tr>
            <td colspan="3" style="font-weight:700;border-top:1px solid #000;">U.P. COLLEGE/DEPT.</td>
            <td colspan="4" style="text-align:center;border-top:1px solid #000;">No. of subjects</td>
            <td colspan="4" style="text-align:center;border-top:1px solid #000;">No. of units (w/o multipliers)</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="padding:5px 8px;font-size:.78rem;">
            <strong>NOTE:</strong> A faculty member teaching in another college and/or another CU should file a separate Form 67 (FSR) in that institution.
        </td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:8px;"></td></tr>
        <tr class="fsr-no-border">
            <td colspan="6"></td>
            <td colspan="5" style="padding:4px 8px;font-weight:600;">Certified Correct:</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:24px;"></td></tr>
        <tr class="fsr-no-border">
            <td colspan="6"></td>
            <td colspan="5" style="text-align:center;font-weight:700;padding:4px;">MARGARITA CARMEN S. PATERNO</td>
        </tr>
        <tr class="fsr-no-border">
            <td colspan="6"></td>
            <td colspan="5" style="border-top:1px solid #000;text-align:center;font-weight:700;padding:4px;">University Registrar</td>
        </tr>
        <tr class="fsr-spacer"><td colspan="11"></td></tr>`;

    // ── SECTION II: RESEARCH / TEXTBOOK WRITING / CREATIVE WORK ──
    html += `<tr class="fsr-section-row"><td colspan="11">II. RESEARCH / TEXTBOOK WRITING / CREATIVE WORK:</td></tr>`;

    // II.A RESEARCH
    html += `<tr class="fsr-subsection-row"><td colspan="11">II.A RESEARCH</td></tr>`;

    // II.A1 Research Proposal
    html += `
        <tr class="fsr-subsection-row"><td colspan="11" style="padding-left:20px;">II.A1 RESEARCH PROPOSAL</td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="4">TITLE (SPECIFY COMPLETE TITLE)</th><th>ROLE</th>
            <th colspan="2">CO WORKERS INVOLVED</th><th colspan="2">FUNDING AGENCY</th><th colspan="2">APPROVED CREDIT UNITS</th>
        </tr>`;
    if (proposals.length > 0) {
        proposals.forEach((item, i) => {
            html += `<tr>
                <td colspan="4">${item.project_id ? `(${i + 1}) OVCRE ID: ${item.project_id}<br>` : `(${i + 1}) `}${item.title || 'Untitled'}</td>
                <td>${item.role || 'Study Leader'}</td>
                <td colspan="2">${item.co_authors || 'None'}</td>
                <td colspan="2">${item.funding_agency || 'Core Funded'}</td>
                <td colspan="2" style="text-align:center;">${item.credit_units || 3}</td>
            </tr>`;
        });
    } else {
        html += `<tr><td colspan="11" class="fsr-italic-empty">No research proposals recorded</td></tr>`;
    }

    html += `<tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>`;

    // II.A2 Research Implementation
    html += `
        <tr class="fsr-subsection-row"><td colspan="11" style="padding-left:20px;">II.A2 RESEARCH IMPLEMENTATION (Please attach Progress Report)</td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="4">TITLE (SPECIFY COMPLETE TITLE)</th><th>ROLE</th>
            <th colspan="2">CO WORKERS INVOLVED</th><th>START DATE</th><th>END DATE</th><th>FUNDING AGENCY</th><th>APPROVED CREDIT UNITS</th>
        </tr>`;
    if (implementations.length > 0) {
        let totalRLC = 0;
        implementations.forEach((item, i) => {
            const cr = parseFloat(item.credit_units) || 3;
            totalRLC += cr;
            html += `<tr>
                <td colspan="4">${item.project_id ? `(${i + 1}) OVCRE ID: ${item.project_id}<br>` : `(${i + 1}) `}${item.title || 'Untitled'}</td>
                <td>${item.role || 'Study Leader'}</td>
                <td colspan="2">${item.co_authors || 'None'}</td>
                <td>${fsrFmtDate(item.start_date)}</td>
                <td>${fsrFmtDate(item.end_date)}</td>
                <td>${item.funding_agency || 'Core Funded'}</td>
                <td style="text-align:center;">${cr}</td>
            </tr>`;
        });
        html += `<tr class="fsr-total-row"><td colspan="10">Total Research Work Load Credits (RLC)</td><td style="text-align:center;">${totalRLC}</td></tr>`;
    } else {
        html += `<tr><td colspan="11" class="fsr-italic-empty">No research implementation recorded</td></tr>`;
    }

    html += `<tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>`;

    // II.B CREATIVE WORK
    html += `<tr class="fsr-subsection-row"><td colspan="11">II.B CREATIVE WORK</td></tr>`;

    const creativeGroups = [
        { key: creative_b1, label: 'II.B1 ORAL/POSTER PAPERS PRESENTED IN CONFERENCES (Please attach first page)' },
        { key: creative_b2, label: 'II.B2 PAPERS PUBLISHED IN PROCEEDINGS OF CONFERENCES (Please attach first page)' },
        { key: creative_b3, label: 'II.B3 MONOGRAPHS: manuals, training modules (Please attach first page)' },
        { key: creative_b4, label: 'II.B4 ARTICLES IN REFEREED JOURNALS (Please attach first page)' },
        { key: creative_b5, label: 'II.B5 CHAPTERS IN A BOOK (Please attach first page)' },
        { key: creative_b6, label: 'II.B6 BOOKS (Please attach first page)' },
        { key: creative_b7, label: 'II.B7 OTHERS (e.g. plays, poetry, musical arrangements, etc.)' },
    ];

    creativeGroups.forEach(grp => {
        html += `
            <tr class="fsr-subsection-row"><td colspan="11" style="padding-left:20px;">${grp.label}</td></tr>
            <tr class="fsr-column-header-row">
                <th colspan="4">TITLE (SPECIFY COMPLETE TITLE, PLACE, PUBLICATION)</th>
                <th colspan="3">CO-AUTHORS</th><th colspan="2">DATE OF PUBLICATION/COMPLETION</th><th colspan="2">APPROVED CREDIT UNITS</th>
            </tr>`;
        if (grp.key.length > 0) {
            grp.key.forEach(item => {
                html += `<tr>
                    <td colspan="4">${item.title || 'Untitled'}</td>
                    <td colspan="3">${item.co_authors || 'None'}</td>
                    <td colspan="2">${fsrFmtDate(item.publication_date || item.end_date)}</td>
                    <td colspan="2" style="text-align:center;">${item.credit_units || '—'}</td>
                </tr>`;
            });
        } else {
            html += `<tr><td colspan="11" class="fsr-italic-empty">—</td></tr>`;
        }
    });

    html += `<tr class="fsr-no-border"><td colspan="11" style="height:8px;"></td></tr>`;

    // ── SECTION III: ADMINISTRATIVE WORK ──
    html += `
        <tr class="fsr-section-row"><td colspan="11">III. ADMINISTRATIVE WORK:</td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="6">POSITION / NATURE OF ADMINISTRATIVE WORK</th>
            <th colspan="3">OFFICE / UNIT</th><th colspan="2">APPROVED CREDIT UNITS</th>
        </tr>
        <tr><td colspan="11" class="fsr-italic-empty">No administrative work recorded</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:8px;"></td></tr>`;

    // ── SECTION IV: EXTENSION AND COMMUNITY SERVICE ──
    html += `
        <tr class="fsr-section-row"><td colspan="11">IV. EXTENSION AND COMMUNITY SERVICE</td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="4">TITLE (SPECIFY COMPLETE TITLE)</th><th>ROLE</th>
            <th colspan="2">CO WORKERS INVOLVED</th><th>START DATE</th><th>END DATE</th><th>FUNDING AGENCY</th><th>APPROVED CREDIT UNITS</th>
        </tr>`;
    html += fsrBuildExtRows(mainExt);
    html += `<tr class="fsr-no-border"><td colspan="11" style="height:4px;"></td></tr>`;

    // IV.A–E subsections
    const extSubs = [
        { data: trainings, label: 'IV.A TRAININGS' },
        { data: infoDiss, label: 'IV.B INFORMATION DISSEMINATION (e.g. print, broadcast T.V., on-line)' },
        { data: workshops, label: 'IV.C WORKSHOPS' },
        { data: symposium, label: 'IV.D SYMPOSIUM' },
        { data: othersExt, label: 'IV.E OTHERS (e.g. community action services)' },
    ];
    extSubs.forEach(sub => {
        html += `
            <tr class="fsr-subsection-row"><td colspan="11">${sub.label}</td></tr>
            <tr class="fsr-column-header-row">
                <th colspan="4">TITLE OF ACTIVITY / PROGRAM</th>
                <th colspan="2">NO. OF HOURS</th><th>NO. OF PARTICIPANTS</th>
                <th>DURATION</th><th>ROLE</th><th>FUNDING AGENCY</th><th>APPROVED CREDIT UNITS</th>
            </tr>`;
        if (sub.data.length > 0) {
            sub.data.forEach(item => {
                html += `<tr>
                    <td colspan="4">${item.title || 'Untitled'}</td>
                    <td colspan="2" style="text-align:center;">${item.hours || 'N/A'}</td>
                    <td style="text-align:center;">${item.participants || 'N/A'}</td>
                    <td>${item.duration || fsrFmtDate(item.start_date)}</td>
                    <td>${item.role || 'Participant'}</td>
                    <td>${item.funding_agency || 'N/A'}</td>
                    <td style="text-align:center;">${item.credit_units || '—'}</td>
                </tr>`;
            });
        } else {
            html += `<tr><td colspan="11" class="fsr-italic-empty">—</td></tr>`;
        }
        html += `<tr class="fsr-no-border"><td colspan="11" style="height:4px;"></td></tr>`;
    });

    // Extension/Research In-Charge Signatures
    html += `
        <tr class="fsr-no-border"><td colspan="11" style="height:30px;"></td></tr>
        <tr class="fsr-no-border">
            <td colspan="5" style="text-align:center;font-weight:700;">____________________________</td>
            <td></td>
            <td colspan="5" style="text-align:center;font-weight:700;">____________________________</td>
        </tr>
        <tr class="fsr-no-border">
            <td colspan="5" style="text-align:center;font-size:.75rem;color:#6b7280;">In-Charge, Extension, DCERP</td>
            <td></td>
            <td colspan="5" style="text-align:center;font-size:.75rem;color:#6b7280;">In-Charge, Research, DCERP</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:10px;"></td></tr>`;

    // ── SECTION V: STUDY LOAD ──
    html += fsrSectionV();

    // ── SECTION VI: LIMITED PRACTICE OF PROFESSION ──
    html += fsrSectionVI();

    // ── SECTION VII: PROFESSORIAL CHAIR ──
    html += fsrSectionVII();

    // ── SECTION VIII: CONSULTATION HOURS ──
    html += fsrSectionVIII();

    // ── SECTION IX: CERTIFICATION ──
    html += fsrSectionIX();

    html += `</table></div></div>`; // Close table, fsr-spreadsheet, and fsr-page
    el.innerHTML = html;
}

// ── Extension Row Builder ─────────────────────────────────────
function fsrBuildExtRows(items) {
    if (!items || items.length === 0) {
        return `<tr><td colspan="11" class="fsr-italic-empty">No extension projects recorded</td></tr>`;
    }
    let h = '';
    let total = 0;
    items.forEach(item => {
        const cr = parseFloat(item.credit_units) || 2;
        total += cr;
        h += `<tr>
            <td colspan="4">${item.project_id ? `Project ID: ${item.project_id}<br>` : ''}${item.title || 'Untitled'}</td>
            <td>${item.role || 'Project Leader'}</td>
            <td colspan="2">${item.co_workers || 'None'}</td>
            <td>${fsrFmtDate(item.start_date)}</td>
            <td>${fsrFmtDate(item.end_date)}</td>
            <td>${item.funding_agency || 'N/A'}</td>
            <td style="text-align:center;">${cr}</td>
        </tr>`;
    });
    h += `<tr class="fsr-total-row"><td colspan="10">Total Extension Credits</td><td style="text-align:center;">${total}</td></tr>`;
    return h;
}


// ── Section V: Study Load ─────────────────────────────────────
function fsrSectionV() {
    return `
        <tr class="fsr-section-row"><td colspan="11">V. STUDY LOAD:</td></tr>
        <tr>
            <td colspan="2" style="font-weight:600;">Status:</td>
            <td colspan="9">N/A</td>
        </tr>
        <tr>
            <td colspan="2"></td>
            <td colspan="4">Degree enrolled in:</td>
            <td colspan="5">University enrolled in:</td>
        </tr>
        <tr>
            <td colspan="6">On full study leave with pay? Yes ___ No ___</td>
            <td colspan="5">Recipient of faculty fellowship? Yes ___ No ___</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.75rem;color:#6b7280;padding:4px 8px;">
            FOR FACULTY MEMBERS WITH SOME TEACHING LOAD BUT ALSO HAVE STUDY LOADS:
        </td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.75rem;color:#6b7280;padding:2px 8px;">
            Study Load CREDITS (i.e. study load counted as part of normal 12-unit faculty load)
        </td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.75rem;color:#6b7280;padding:2px 8px;">
            Study Load Units (i.e. study load done above a full teaching load)
        </td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="2">Course Number</th><th colspan="2">Course Credit</th>
            <th colspan="2">Day/s</th><th colspan="2">Time</th><th colspan="3">School</th>
        </tr>
        <tr><td colspan="11" class="fsr-italic-empty">—</td></tr>
        <tr class="fsr-total-row"><td colspan="11" style="padding:6px 10px;">Total Study Load Credits (SLC): —</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>
        <tr style="background:#d9d9d9;font-weight:700;">
            <td colspan="11" style="padding:8px 10px;font-size:.85rem;border:2px solid #000;">
                TOTAL FACULTY LOAD IN CREDIT UNITS: —
            </td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:8px;"></td></tr>`;
}

// ── Section VI: Limited Practice of Profession ────────────────
function fsrSectionVI() {
    return `
        <tr class="fsr-section-row"><td colspan="11">VI. LIMITED PRACTICE OF PROFESSION</td></tr>
        <tr>
            <td colspan="7">Have you applied for official permission for limited practice of profession?</td>
            <td colspan="4">N/A</td>
        </tr>
        <tr>
            <td colspan="7" style="font-size:.75rem;">If yes, indicate date (MM/DD/YY) permission was submitted</td>
            <td colspan="4" style="font-size:.75rem;">or approved: ___</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>`;
}

// ── Section VII: Professorial Chair ───────────────────────────
function fsrSectionVII() {
    return `
        <tr class="fsr-section-row"><td colspan="11">VII. PROFESSORIAL CHAIR or FACULTY GRANT RECIPIENT or NOMINEE:</td></tr>
        <tr>
            <td colspan="8" style="font-size:.78rem;">Please write NA on the space on the right if neither a recipient nor a nominee</td>
            <td colspan="3">N/A</td>
        </tr>
        <tr>
            <td colspan="3">PROFESSORIAL CHAIR ___</td>
            <td colspan="2">GRANT ___</td>
            <td colspan="6">CHAIR/GRANT TITLE: ___</td>
        </tr>
        <tr>
            <td colspan="5">APPROVED START DATE (MM/DD/YY): ___</td>
            <td colspan="6">END DATE (MM/DD/YY): ___</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:6px;"></td></tr>`;
}

// ── Section VIII: Consultation Hours ──────────────────────────
function fsrSectionVIII() {
    return `
        <tr class="fsr-section-row"><td colspan="11">VIII. CONSULTATION HOURS:</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.75rem;color:#6b7280;padding:4px 8px;">
            (From the U.P. Faculty Manual: "At least 10 hours per week." Please specify definite days and hours; avoid "By appointment.")
        </td></tr>
        <tr class="fsr-column-header-row">
            <th colspan="3">Days</th><th colspan="4">Time</th><th colspan="4">Place</th>
        </tr>
        <tr><td colspan="11" class="fsr-italic-empty">—</td></tr>
        <tr>
            <td colspan="7" style="border:none;"></td>
            <td colspan="2" style="font-weight:600;">Total hours per week:</td>
            <td colspan="2" style="font-weight:700;">—</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:8px;"></td></tr>`;
}

// ── Section IX: Certification ─────────────────────────────────
function fsrSectionIX() {
    return `
        <tr class="fsr-section-row"><td colspan="11">IX. CERTIFICATION:</td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.78rem;padding:8px;">
            The faculty member certifies that all the information provided in this record are true and correct to the best of his/her knowledge.
        </td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:30px;"></td></tr>
        <tr class="fsr-no-border">
            <td colspan="3" style="text-align:center;font-weight:700;">____________________________</td>
            <td colspan="4" style="text-align:center;font-weight:700;">____________________________</td>
            <td colspan="4" style="text-align:center;font-weight:700;">____________________________</td>
        </tr>
        <tr class="fsr-no-border">
            <td colspan="3" style="text-align:center;font-size:.72rem;color:#6b7280;">Faculty Member</td>
            <td colspan="4" style="text-align:center;font-size:.72rem;color:#6b7280;">Chair, Department</td>
            <td colspan="4" style="text-align:center;font-size:.72rem;color:#6b7280;">Dean</td>
        </tr>
        <tr class="fsr-no-border">
            <td colspan="3" style="text-align:center;font-size:.72rem;color:#9ca3af;">Date: ___</td>
            <td colspan="4" style="text-align:center;font-size:.72rem;color:#9ca3af;">Date: ___</td>
            <td colspan="4" style="text-align:center;font-size:.72rem;color:#9ca3af;">Date: ___</td>
        </tr>
        <tr class="fsr-no-border"><td colspan="11" style="height:10px;"></td></tr>
        <tr class="fsr-no-border"><td colspan="11" style="font-size:.72rem;color:#6b7280;padding:6px 8px;">
            NOTE: Every faculty member in residence (i.e. receiving salary from U.P.), including those on detail/secondment to other agencies, must fill out this report form.
        </td></tr>`;
}
