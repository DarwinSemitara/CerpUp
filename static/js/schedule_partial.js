// Schedule partial HTML — injected by dashboard SPA
window.SCHEDULE_PARTIAL = `
<style>
.sched-filters{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px;}
.sched-filters select,.sched-filters input{padding:7px 10px;border:1px solid #d1d5db;border-radius:8px;font-size:.82rem;color:#374151;background:white;outline:none;}
.sched-filters select:focus,.sched-filters input:focus{border-color:#6b0f1a;}
.sched-filters label{font-size:.78rem;color:#6b7280;font-weight:500;}
.timetable-wrap{background:white;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;margin-bottom:24px;}
.timetable{width:100%;border-collapse:collapse;font-size:.75rem;}
.timetable th{background:#f9fafb;padding:8px 10px;text-align:center;font-weight:600;color:#6b7280;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e5e7eb;white-space:nowrap;}
.timetable th:first-child{width:72px;text-align:right;padding-right:12px;}
.timetable td{border:1px solid #f0f0f0;padding:0;height:32px;vertical-align:middle;position:relative;}
.timetable td:first-child{background:#fafafa;text-align:right;padding-right:10px;color:#9ca3af;font-size:.7rem;white-space:nowrap;border:none;border-bottom:1px solid #f0f0f0;}
.sched-cell{display:flex;flex-direction:column;justify-content:center;padding:2px 6px;height:100%;font-size:.68rem;line-height:1.3;border-radius:4px;margin:1px;cursor:default;}
.sched-cell .sc-subj{font-weight:700;color:#1a1a1a;}
.sched-cell .sc-prof{color:#555;}
.sched-cell .sc-room{color:#888;}
.sched-form-card{background:white;border:1px solid #e5e7eb;border-radius:12px;padding:20px 24px;margin-bottom:24px;}
.sched-form-card h3{font-size:.82rem;font-weight:700;color:#374151;margin:0 0 16px;text-transform:uppercase;letter-spacing:.04em;}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;}
.form-group{display:flex;flex-direction:column;gap:4px;}
.form-group label{font-size:.75rem;font-weight:500;color:#6b7280;}
.form-group input,.form-group select{padding:7px 10px;border:1px solid #d1d5db;border-radius:8px;font-size:.82rem;color:#374151;outline:none;transition:border-color .15s;}
.form-group input:focus,.form-group select:focus{border-color:#6b0f1a;}
.form-actions{display:flex;gap:10px;margin-top:16px;}
.btn-primary{padding:8px 20px;background:#6b0f1a;color:white;border:none;border-radius:8px;font-size:.82rem;font-weight:600;cursor:pointer;}
.btn-primary:hover{background:#850f20;}
.btn-secondary{padding:8px 16px;background:white;color:#374151;border:1px solid #d1d5db;border-radius:8px;font-size:.82rem;cursor:pointer;}
.report-card{background:white;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;}
.report-card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e5e7eb;}
.report-card-header h3{font-size:.82rem;font-weight:700;color:#374151;margin:0;text-transform:uppercase;letter-spacing:.04em;}
.report-table{width:100%;border-collapse:collapse;font-size:.78rem;}
.report-table th{background:#f9fafb;padding:9px 14px;text-align:left;font-weight:600;color:#6b7280;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e5e7eb;white-space:nowrap;}
.report-table td{padding:9px 14px;color:#374151;border-bottom:1px solid #f3f4f6;}
.report-table tr:last-child td{border-bottom:none;}
.report-table tr:hover td{background:#fdf2f3;}
</style>
<div class="sched-filters">
  <label>Filter by:</label>
  <select id="sf-professor" onchange="applySchedFilter()"><option value="">All Professors</option></select>
  <select id="sf-subject" onchange="applySchedFilter()"><option value="">All Subjects</option></select>
  <select id="sf-room" onchange="applySchedFilter()"><option value="">All Classrooms</option></select>
  <select id="sf-day" onchange="applySchedFilter()"><option value="">All Days</option><option>Monday</option><option>Tuesday</option><option>Wednesday</option><option>Thursday</option><option>Friday</option><option>Saturday</option></select>
  <button class="btn-secondary" onclick="clearSchedFilters()" style="font-size:.78rem;padding:6px 12px;">Clear</button>
</div>
<div class="timetable-wrap"><div style="overflow-x:auto;"><table class="timetable" id="timetable"><thead><tr><th>Time</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th><th>Saturday</th></tr></thead><tbody id="timetable-body"></tbody></table></div></div>
<div class="sched-form-card">
  <h3>Add New Schedule</h3>
  <div class="form-grid">
    <div class="form-group"><label>Professor</label><input type="text" id="f-prof" placeholder="e.g. Dr. A. Santos"></div>
    <div class="form-group"><label>Subject Code</label><input type="text" id="f-subj-code" placeholder="e.g. CS 101"></div>
    <div class="form-group"><label>Subject Name</label><input type="text" id="f-subj-name" placeholder="e.g. Intro to Computing"></div>
    <div class="form-group"><label>Day</label><select id="f-day"><option value="">Select day</option><option>Monday</option><option>Tuesday</option><option>Wednesday</option><option>Thursday</option><option>Friday</option><option>Saturday</option></select></div>
    <div class="form-group"><label>Start Time</label><select id="f-start"><option value="">Select start</option></select></div>
    <div class="form-group"><label>End Time</label><select id="f-end"><option value="">Select end</option></select></div>
    <div class="form-group"><label>Classroom</label><input type="text" id="f-room" placeholder="e.g. Room 201"></div>
    <div class="form-group"><label>Units</label><input type="number" id="f-units" placeholder="e.g. 3" min="1" max="6"></div>
    <div class="form-group"><label>Section</label><input type="text" id="f-section" placeholder="e.g. BSCS 2-A"></div>
  </div>
  <div class="form-actions"><button class="btn-primary" onclick="addSchedule()">Add Schedule</button><button class="btn-secondary" onclick="clearSchedForm()">Clear</button></div>
  <p id="form-msg" style="font-size:.78rem;margin:8px 0 0;display:none;"></p>
</div>
<div class="report-card">
  <div class="report-card-header"><h3>Faculty Load Report</h3>
    <div class="gen-report-wrap"><button class="gen-report-btn" onclick="toggleDropdown('sched-report-menu')"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>Generate Report<svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button><div class="gen-report-menu" id="sched-report-menu"><a href="#">📄 Export as DOCX</a><a href="#">📕 Export as PDF</a><a href="#">📊 Export as Excel</a></div></div>
  </div>
  <div style="overflow-x:auto;"><table class="report-table" id="report-table"><thead><tr><th>#</th><th>Professor</th><th>Subject</th><th>Day &amp; Time</th><th>Unit Load</th><th>Classroom</th><th>Section</th></tr></thead><tbody id="report-tbody"></tbody></table></div>
</div>`;

// Schedule logic — runs after partial is injected
window.initSchedule = function () {
    const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const slots = [];
    for (let h = 7; h < 17; h++) { slots.push(`${h}:00`); slots.push(`${h}:30`); }
    slots.push('17:00');
    function fmt(t) { const [h, m] = t.split(':').map(Number); const ampm = h >= 12 ? 'PM' : 'AM'; const hh = h > 12 ? h - 12 : h === 0 ? 12 : h; return `${hh}:${m === 0 ? '00' : '30'} ${ampm}`; }
    ['f-start', 'f-end'].forEach(id => { const sel = document.getElementById(id); slots.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = fmt(s); sel.appendChild(o); }); });
    function slotIdx(t) { return slots.indexOf(t); }
    const palette = ['#fde8ea', '#e8f4fd', '#e8fdf0', '#fdf6e8', '#f0e8fd', '#fde8f8', '#e8fdfd'];
    const subjectColors = {}; let colorIdx = 0;
    function colorFor(subj) { if (!subjectColors[subj]) subjectColors[subj] = palette[colorIdx++ % palette.length]; return subjectColors[subj]; }
    let schedules = [
        { prof: 'Dr. A. Santos', subjCode: 'CS 101', subjName: 'Intro to Computing', day: 'Monday', start: '7:00', end: '8:30', room: 'Room 101', units: 3, section: 'BSCS 1-A' },
        { prof: 'Prof. B. Cruz', subjCode: 'MATH 2', subjName: 'Calculus II', day: 'Monday', start: '9:00', end: '10:30', room: 'Room 202', units: 3, section: 'BSCS 2-B' },
        { prof: 'Dr. A. Santos', subjCode: 'CS 201', subjName: 'Data Structures', day: 'Tuesday', start: '7:30', end: '9:00', room: 'Room 101', units: 3, section: 'BSCS 2-A' },
        { prof: 'Engr. C. Reyes', subjCode: 'ENG 3', subjName: 'Engineering Drawing', day: 'Wednesday', start: '10:00', end: '11:30', room: 'Lab 1', units: 2, section: 'BSEE 1-A' },
        { prof: 'Prof. B. Cruz', subjCode: 'MATH 3', subjName: 'Differential Equations', day: 'Thursday', start: '8:00', end: '9:30', room: 'Room 202', units: 3, section: 'BSCS 3-A' },
        { prof: 'Dr. D. Lim', subjCode: 'BIO 1', subjName: 'General Biology', day: 'Friday', start: '7:00', end: '8:30', room: 'Lab 2', units: 3, section: 'BSED 1-A' },
    ];
    let filtered = [...schedules];
    function refreshFilterOptions() {
        const profs = [...new Set(schedules.map(s => s.prof))].sort();
        const subjs = [...new Set(schedules.map(s => s.subjCode + ' – ' + s.subjName))].sort();
        const rooms = [...new Set(schedules.map(s => s.room))].sort();
        [['sf-professor', profs], ['sf-subject', subjs], ['sf-room', rooms]].forEach(([id, opts]) => {
            const sel = document.getElementById(id); if (!sel) return; const cur = sel.value;
            sel.innerHTML = `<option value="">All ${id === 'sf-professor' ? 'Professors' : id === 'sf-subject' ? 'Subjects' : 'Classrooms'}</option>`;
            opts.forEach(o => { const el = document.createElement('option'); el.value = o; el.textContent = o; sel.appendChild(el); }); sel.value = cur;
        });
    }
    window.applySchedFilter = function () {
        const prof = document.getElementById('sf-professor').value;
        const subj = document.getElementById('sf-subject').value;
        const room = document.getElementById('sf-room').value;
        const day = document.getElementById('sf-day').value;
        filtered = schedules.filter(s => (!prof || s.prof === prof) && (!subj || (s.subjCode + ' – ' + s.subjName) === subj) && (!room || s.room === room) && (!day || s.day === day));
        renderTimetable(); renderReport();
    };
    window.clearSchedFilters = function () { ['sf-professor', 'sf-subject', 'sf-room', 'sf-day'].forEach(id => document.getElementById(id).value = ''); filtered = [...schedules]; renderTimetable(); renderReport(); };
    function renderTimetable() {
        const tbody = document.getElementById('timetable-body'); if (!tbody) return;
        const grid = {}; DAYS.forEach(d => { grid[d] = {}; });
        filtered.forEach(s => { const si = slotIdx(s.start), ei = slotIdx(s.end); if (si < 0 || ei < 0) return; for (let i = si; i < ei; i++) { if (!grid[s.day][i]) grid[s.day][i] = { ...s, span: ei - si, isFirst: i === si }; } });
        const covered = {}; let html = '';
        for (let si = 0; si < slots.length - 1; si++) {
            const isHour = slots[si].endsWith(':00'); html += `<tr><td style="opacity:${isHour ? 1 : 0.4}">${isHour ? fmt(slots[si]) : ''}</td>`;
            DAYS.forEach(day => {
                const key = `${day}-${si}`; if (covered[key]) return;
                const entry = grid[day][si];
                if (entry && entry.isFirst) { const span = entry.span; const bg = colorFor(entry.subjCode); for (let k = 1; k < span; k++)covered[`${day}-${si + k}`] = true; html += `<td rowspan="${span}" style="padding:0;"><div class="sched-cell" style="background:${bg};height:${span * 32 - 2}px;"><span class="sc-subj">${entry.subjCode}</span><span class="sc-prof">${entry.prof.split(' ').slice(-1)[0]}</span><span class="sc-room">${entry.room}</span></div></td>`; }
                else if (!entry) { html += `<td></td>`; }
            }); html += `</tr>`;
        }
        tbody.innerHTML = html;
    }
    function renderReport() {
        const tbody = document.getElementById('report-tbody'); if (!tbody) return;
        if (!filtered.length) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#9ca3af;padding:20px;">No schedules found.</td></tr>`; return; }
        tbody.innerHTML = filtered.map((s, i) => `<tr><td style="color:#9ca3af;font-size:.72rem;">${i + 1}</td><td>${s.prof}</td><td>${s.subjCode} — ${s.subjName}</td><td>${s.day}, ${fmt(s.start)} – ${fmt(s.end)}</td><td style="text-align:center;">${s.units}</td><td>${s.room}</td><td>${s.section}</td></tr>`).join('');
    }
    window.addSchedule = function () {
        const prof = document.getElementById('f-prof').value.trim(); const code = document.getElementById('f-subj-code').value.trim(); const name = document.getElementById('f-subj-name').value.trim();
        const day = document.getElementById('f-day').value; const start = document.getElementById('f-start').value; const end = document.getElementById('f-end').value;
        const room = document.getElementById('f-room').value.trim(); const units = document.getElementById('f-units').value; const sec = document.getElementById('f-section').value.trim();
        const msg = document.getElementById('form-msg');
        if (!prof || !code || !name || !day || !start || !end || !room || !units || !sec) { msg.textContent = 'Please fill in all fields.'; msg.style.color = '#dc2626'; msg.style.display = 'block'; return; }
        if (slotIdx(start) >= slotIdx(end)) { msg.textContent = 'End time must be after start time.'; msg.style.color = '#dc2626'; msg.style.display = 'block'; return; }
        schedules.push({ prof, subjCode: code, subjName: name, day, start, end, room, units: Number(units), section: sec });
        filtered = [...schedules]; refreshFilterOptions(); renderTimetable(); renderReport(); clearSchedForm();
        msg.textContent = 'Schedule added successfully.'; msg.style.color = '#16a34a'; msg.style.display = 'block'; setTimeout(() => msg.style.display = 'none', 3000);
    };
    window.clearSchedForm = function () { ['f-prof', 'f-subj-code', 'f-subj-name', 'f-room', 'f-units', 'f-section'].forEach(id => document.getElementById(id).value = '');['f-day', 'f-start', 'f-end'].forEach(id => document.getElementById(id).value = ''); document.getElementById('form-msg').style.display = 'none'; };
    refreshFilterOptions(); renderTimetable(); renderReport();
};
