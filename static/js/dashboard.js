/* CERP Admin dashboard — ARIMA volume outlook + this-year mix */

const adminForecastCharts = { line: { current: null }, mix: { current: null } };

function initAdminForecast() {
    if (typeof loadDashboardForecast !== 'function') {
        console.warn('Forecast chart script is not loaded');
        return;
    }
    loadDashboardForecast({
        lineCanvasId: 'publicationsChart',
        mixCanvasId: 'tapChart',
        legendId: 'forecast-line-legend',
        lineLegendId: 'forecast-line-legend',
        summaryId: 'forecast-summary',
        subtitleId: 'forecast-subtitle',
        scope: 'admin',
        lineChartRef: adminForecastCharts.line,
        mixChartRef: adminForecastCharts.mix,
    });
}

// ── Faculty List ──────────────────────────────────────────────

function loadDashboardFacultyList() {
    const container = document.getElementById('dashboard-faculty-list');
    if (!container) return;

    // Show loading state
    container.innerHTML = `
        <div style="text-align:center;padding:40px 20px;color:#9ca3af;">
            <div class="content-spinner"></div>
            <div style="margin-top:12px;font-size:0.9rem;">Loading faculty...</div>
        </div>
    `;

    fetch('/api/members')
        .then(res => res.json())
        .then(data => {
            // API returns array directly, not wrapped in object
            const members = Array.isArray(data) ? data : (data.members || []);

            if (members.length === 0) {
                container.innerHTML = `
                    <div style="text-align:center;padding:40px 20px;color:#9ca3af;">
                        <div style="font-size:0.95rem;">No faculty members found</div>
                    </div>
                `;
                return;
            }

            // Sort by name
            members.sort((a, b) => {
                const nameA = `${a.first || ''} ${a.last || ''}`.trim();
                const nameB = `${b.first || ''} ${b.last || ''}`.trim();
                return nameA.localeCompare(nameB);
            });

            // Render faculty list
            container.innerHTML = members.map(member => {
                const fullName = `${member.first || ''} ${member.last || ''}`.trim();
                const displayName = getCleanName(fullName || 'Unnamed');
                const photoUrl = member.photo_url || '';
                const memberId = member.id || member.uid;
                const initial = displayName.charAt(0).toUpperCase();

                return `
                    <div class="faculty-list-item">
                        ${photoUrl ?
                        `<img src="${photoUrl}" alt="${displayName}" class="faculty-list-photo">` :
                        `<div class="faculty-list-photo" style="background:#6b0f1a;color:white;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:18px;">${initial}</div>`
                    }
                        <div style="flex:1;font-size:0.95rem;color:#111827;font-weight:500;">${displayName}</div>
                        <button class="faculty-manage-btn" onclick="manageFaculty('${memberId}')">
                            Manage
                        </button>
                    </div>
                `;
            }).join('');
        })
        .catch(err => {
            console.error('Failed to load faculty list:', err);
            container.innerHTML = `
                <div style="text-align:center;padding:40px 20px;color:#ef4444;">
                    <div style="font-size:0.95rem;">Failed to load faculty members</div>
                </div>
            `;
        });
}

function getCleanName(fullName) {
    // Remove common suffixes and honorifics
    let name = fullName
        .replace(/,?\s*(Jr\.?|Sr\.?|III?|IV|Ph\.?D\.?|M\.?S\.?|B\.?S\.?|Dr\.?|Prof\.?)$/gi, '')
        .replace(/^(Dr\.?|Prof\.?|Mr\.?|Ms\.?|Mrs\.?)\s+/gi, '')
        .trim();

    return name || fullName;
}

function manageFaculty(memberId) {
    // Open comprehensive management modal
    openFacultyManagementModal(memberId);
}

// ── Faculty Management Modal ──────────────────────────────────

let currentFacultyData = null;
let fmActivityChart = null;

function openFacultyManagementModal(memberId) {
    const modal = document.getElementById('faculty-mgmt-modal');
    if (!modal) return;

    modal.classList.add('active');
    currentFacultyData = { id: memberId };

    // Load faculty data
    loadFacultyData(memberId);
}

function closeFacultyManagementModal() {
    const modal = document.getElementById('faculty-mgmt-modal');
    if (modal) modal.classList.remove('active');

    // Destroy chart if exists
    if (fmActivityChart) {
        fmActivityChart.destroy();
        fmActivityChart = null;
    }
}

async function loadFacultyData(memberId) {
    try {
        // Fetch member details
        const memberRes = await fetch(`/api/members`);
        const members = await memberRes.json();
        const memberData = (Array.isArray(members) ? members : members.members || [])
            .find(m => m.id === memberId || m.uid === memberId);

        if (!memberData) {
            console.error('Member not found');
            return;
        }

        currentFacultyData = memberData;

        // Update header
        const fullName = `${memberData.first || ''} ${memberData.last || ''}`.trim();
        const displayName = getCleanName(fullName);
        document.getElementById('fm-name').textContent = fullName;
        document.getElementById('fm-email').textContent = memberData.email || 'No email';

        // Update photo
        const photoEl = document.getElementById('fm-photo');
        if (memberData.photo_url) {
            photoEl.src = memberData.photo_url;
            photoEl.alt = displayName;
        } else {
            const initial = displayName.charAt(0).toUpperCase();
            photoEl.style.display = 'none';
            const photoContainer = photoEl.parentElement;
            photoContainer.innerHTML = `
                <div class="fm-photo" style="background:#6b0f1a;color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:24px;">
                    ${initial}
                </div>
            `;
        }

        // Update details tab (if it exists - removed in recent update)
        const detailName = document.getElementById('fm-detail-name');
        if (detailName) {
            detailName.textContent = fullName;
            document.getElementById('fm-detail-email').textContent = memberData.email || '—';
            document.getElementById('fm-detail-roles').textContent = memberData.role || '—';
            document.getElementById('fm-detail-type').textContent = memberData.type || '—';

            const isDisabled = memberData.disabled || false;
            document.getElementById('fm-detail-status').innerHTML = isDisabled
                ? '<span style="color:#dc2626;font-weight:600;">Disabled</span>'
                : '<span style="color:#16a34a;font-weight:600;">Active</span>';

            const availability = Array.isArray(memberData.availability) && memberData.availability.length > 0
                ? memberData.availability.join(', ')
                : '—';
            document.getElementById('fm-detail-availability').textContent = availability;
        }

        const isDisabled = memberData.disabled || false;

        // Update disable button
        const disableBtn = document.getElementById('fm-disable-btn');
        if (isDisabled) {
            disableBtn.textContent = 'Enable';
            disableBtn.classList.remove('fm-btn-disable');
            disableBtn.classList.add('fm-btn-enable');
        } else {
            disableBtn.textContent = 'Disable';
            disableBtn.classList.remove('fm-btn-enable');
            disableBtn.classList.add('fm-btn-disable');
        }

        // Load activity data
        loadFacultyActivity(memberId);

    } catch (error) {
        console.error('Failed to load faculty data:', error);
    }
}

async function loadFacultyActivity(memberId) {
    try {
        const res = await fetch(`/api/members/${memberId}/activity`);
        const data = await res.json();

        // Update stats
        const researchCount = data.research_count || 0;
        const extensionsCount = data.extensions_count || 0;
        const adminCount = data.admin_count || 0;
        const totalCount = researchCount + extensionsCount + adminCount;

        document.getElementById('fm-research-count').textContent = researchCount;
        document.getElementById('fm-extensions-count').textContent = extensionsCount;
        document.getElementById('fm-admin-count').textContent = adminCount;
        document.getElementById('fm-total-count').textContent = totalCount;

        // Render activity calendar
        renderFMActivityCalendar(data.daily || {});

        // Render activity chart
        renderFMActivityChart(researchCount, extensionsCount, adminCount);

        // Render timeline
        renderFMTimeline(data);

    } catch (error) {
        console.error('Failed to load faculty activity:', error);
    }
}

function renderFMActivityCalendar(dailyData) {
    const container = document.getElementById('fm-activity-calendar');
    if (!container) return;

    const now = new Date();

    // Calculate date range: last 12 months from today
    const endDate = new Date(now);
    const startDate = new Date(now);
    startDate.setMonth(startDate.getMonth() - 11);
    startDate.setDate(1); // Start from first day of the month 12 months ago

    // Build continuous grid of all days in range
    const allDays = [];
    const currentDate = new Date(startDate);

    while (currentDate <= endDate) {
        allDays.push(new Date(currentDate));
        currentDate.setDate(currentDate.getDate() + 1);
    }

    // Find first Sunday before or on start date for grid alignment
    const firstDay = new Date(allDays[0]);
    while (firstDay.getDay() !== 0) { // 0 = Sunday
        firstDay.setDate(firstDay.getDate() - 1);
    }

    // Build grid starting from first Sunday
    const gridDays = [];
    const gridDate = new Date(firstDay);
    const lastDayPlusOne = new Date(endDate);
    lastDayPlusOne.setDate(lastDayPlusOne.getDate() + 1);

    // Add days until we complete the last week
    while (gridDate < lastDayPlusOne || gridDate.getDay() !== 0) {
        gridDays.push(new Date(gridDate));
        gridDate.setDate(gridDate.getDate() + 1);

        // Safety check: don't go beyond 400 days
        if (gridDays.length > 400) break;
    }

    // Calculate number of weeks
    const numWeeks = Math.ceil(gridDays.length / 7);

    // Group days into weeks for rendering
    const weeks = [];
    for (let i = 0; i < numWeeks; i++) {
        weeks.push(gridDays.slice(i * 7, (i + 1) * 7));
    }

    // Build HTML - GitHub style with month labels on top
    let html = '<div style="display:flex;flex-direction:column;gap:0;">';

    // Month labels row
    html += '<div style="display:flex;gap:0;margin-bottom:4px;padding-left:28px;">';
    let lastMonth = -1;
    let accumulatedWidth = 0;
    const monthLabels = [];

    weeks.forEach((week, weekIndex) => {
        const middleDay = week[3] || week[0]; // Use Wednesday or first available
        const month = middleDay.getMonth();

        if (month !== lastMonth) {
            if (accumulatedWidth > 0) {
                monthLabels.push({ month: lastMonth, width: accumulatedWidth });
            }
            lastMonth = month;
            accumulatedWidth = 12;
        } else {
            accumulatedWidth += 12;
        }
    });

    // Add last month
    if (accumulatedWidth > 0) {
        monthLabels.push({ month: lastMonth, width: accumulatedWidth });
    }

    // Render month labels
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    monthLabels.forEach(label => {
        html += `<div style="width:${label.width}px;font-size:10px;color:#6b7280;font-weight:600;">${monthNames[label.month]}</div>`;
    });
    html += '</div>';

    // Main grid container
    html += '<div style="display:flex;gap:0;">';

    // Weekday labels (left side)
    html += '<div style="display:flex;flex-direction:column;gap:2px;margin-right:6px;justify-content:space-around;height:91px;">';
    html += '<div style="font-size:9px;color:#6b7280;height:11px;line-height:11px;">Mon</div>';
    html += '<div style="height:11px;"></div>';
    html += '<div style="font-size:9px;color:#6b7280;height:11px;line-height:11px;">Wed</div>';
    html += '<div style="height:11px;"></div>';
    html += '<div style="font-size:9px;color:#6b7280;height:11px;line-height:11px;">Fri</div>';
    html += '<div style="height:11px;"></div>';
    html += '<div style="height:11px;"></div>';
    html += '</div>';

    // Calendar grid (weeks as columns, days as rows)
    html += '<div style="display:flex;gap:3px;">';

    weeks.forEach(week => {
        html += '<div style="display:flex;flex-direction:column;gap:3px;">';

        week.forEach(date => {
            const dateStr = date.toISOString().split('T')[0];
            const count = dailyData[dateStr] || 0;
            const level = count === 0 ? 0 : count <= 5 ? 1 : count <= 10 ? 2 : 3;

            // Check if date is in our actual range (not padding)
            const isInRange = date >= allDays[0] && date <= endDate;
            const opacity = isInRange ? '1' : '0.3';

            // Format date as "Oct 7, 2026"
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const formattedDate = `${monthNames[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
            const submitText = count === 1 ? 'submit' : 'submits';

            html += `<div class="fm-activity-box" data-level="${level}" data-count="${count}" data-date="${formattedDate}" title="${formattedDate}: ${count} ${submitText}" style="opacity:${opacity};"></div>`;
        });

        html += '</div>';
    });

    html += '</div>'; // Close grid
    html += '</div>'; // Close main container
    html += '</div>'; // Close outer container

    // Add legend
    html += `
        <div class="fm-activity-legend">
            <span>Less</span>
            <div class="fm-activity-legend-box" style="background:#f3f4f6;"></div>
            <div class="fm-activity-legend-box" style="background:#c6e9d2;"></div>
            <div class="fm-activity-legend-box" style="background:#7fc89c;"></div>
            <div class="fm-activity-legend-box" style="background:#28a745;"></div>
            <span>More</span>
        </div>
    `;

    container.innerHTML = html;
}

function renderFMActivityChart(research, extensions, admin) {
    const canvas = document.getElementById('fm-activity-chart-canvas');
    if (!canvas) return;

    // Destroy existing chart
    if (fmActivityChart) {
        fmActivityChart.destroy();
    }

    const ctx = canvas.getContext('2d');

    fmActivityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Research Papers', 'Extensions', 'Admin Works'],
            datasets: [{
                data: [research, extensions, admin],
                backgroundColor: ['#4f46e5', '#16a34a', '#dc2626'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 13,
                            weight: '600'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function (context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.parsed;
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return ` ${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderFMTimeline(activityData) {
    const container = document.getElementById('fm-timeline');
    if (!container) return;

    // Collect all activities with dates
    const activities = [];

    // Add research papers
    if (activityData.research) {
        activityData.research.forEach(item => {
            activities.push({
                type: 'research',
                title: item.title || 'Research Paper',
                date: item.created_at,
                icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
                color: '#4f46e5',
                bg: '#eef2ff',
                badge: 'Research',
                badgeBg: '#eef2ff',
                badgeColor: '#4f46e5'
            });
        });
    }

    // Add extensions
    if (activityData.extensions) {
        activityData.extensions.forEach(item => {
            activities.push({
                type: 'extension',
                title: item.title || 'Extension Activity',
                date: item.created_at,
                icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
                color: '#16a34a',
                bg: '#f0fdf4',
                badge: 'Extension',
                badgeBg: '#f0fdf4',
                badgeColor: '#16a34a'
            });
        });
    }

    // Add admin works (FSR files)
    if (activityData.admin) {
        activityData.admin.forEach(item => {
            activities.push({
                type: 'admin',
                title: 'Administrative Work',
                date: item.created_at,
                icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
                color: '#dc2626',
                bg: '#fef3f2',
                badge: 'Admin',
                badgeBg: '#fef3f2',
                badgeColor: '#dc2626'
            });
        });
    }

    // Sort by date (most recent first)
    activities.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Limit to 20 most recent
    const recentActivities = activities.slice(0, 20);

    if (recentActivities.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:40px;color:#9ca3af;">
                <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin:0 auto 12px;opacity:0.5;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <div style="font-size:0.95rem;">No activities recorded yet</div>
            </div>
        `;
        return;
    }

    let html = '';
    recentActivities.forEach(activity => {
        const dateObj = new Date(activity.date);
        const formattedDate = dateObj.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        html += `
            <div class="fm-timeline-item">
                <div class="fm-timeline-icon" style="background:${activity.bg};color:${activity.color};">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${activity.icon}"/>
                    </svg>
                </div>
                <div class="fm-timeline-content">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                        <h4 class="fm-timeline-title">${escapeHtml(activity.title)}</h4>
                        <span class="fm-timeline-badge" style="background:${activity.badgeBg};color:${activity.badgeColor};">
                            ${activity.badge}
                        </span>
                    </div>
                    <div class="fm-timeline-date">${formattedDate}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function switchFMTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.fm-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.fm-tab[data-tab="${tabName}"]`).classList.add('active');

    // Update tab panels
    document.querySelectorAll('.fm-tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.querySelector(`.fm-tab-panel[data-panel="${tabName}"]`).classList.add('active');
}

async function toggleFacultyStatus() {
    if (!currentFacultyData) return;

    const memberId = currentFacultyData.id;
    const isCurrentlyDisabled = currentFacultyData.disabled || false;
    const action = isCurrentlyDisabled ? 'enable' : 'disable';

    try {
        const res = await fetch(`/api/members/${memberId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                disabled: !isCurrentlyDisabled
            })
        });

        if (res.ok) {
            alert(`Faculty account ${action}d successfully`);
            loadFacultyData(memberId); // Reload data
            loadDashboardFacultyList(); // Refresh list
        } else {
            alert(`Failed to ${action} faculty account`);
        }
    } catch (error) {
        console.error(`Error ${action}ing faculty:`, error);
        alert(`Failed to ${action} faculty account`);
    }
}

function confirmDeleteFaculty() {
    if (!currentFacultyData) return;

    const fullName = `${currentFacultyData.first || ''} ${currentFacultyData.last || ''}`.trim();
    document.getElementById('fm-delete-name').textContent = fullName;

    const confirmModal = document.getElementById('fm-delete-confirm');
    if (confirmModal) confirmModal.classList.add('active');
}

function closeDeleteConfirm() {
    const confirmModal = document.getElementById('fm-delete-confirm');
    if (confirmModal) confirmModal.classList.remove('active');
}

async function executeFacultyDelete() {
    if (!currentFacultyData) return;

    const memberId = currentFacultyData.id;

    try {
        const res = await fetch(`/api/members/${memberId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            alert('Faculty account deleted successfully');
            closeDeleteConfirm();
            closeFacultyManagementModal();
            loadDashboardFacultyList(); // Refresh list
        } else {
            alert('Failed to delete faculty account');
        }
    } catch (error) {
        console.error('Error deleting faculty:', error);
        alert('Failed to delete faculty account');
    }
}

function editFacultyProfile() {
    if (!currentFacultyData) return;

    // Navigate to manage page to edit
    window.location.href = '/manage';
}

// ── Initialization ────────────────────────────────────────────

function initDashboard() {
    initAdminForecast();
    loadDashboardFacultyList();

    // Add keyboard event listener for ESC key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            const previewModal = document.getElementById('fm-preview-modal');
            const confirmModal = document.getElementById('fm-delete-confirm');
            const modal = document.getElementById('faculty-mgmt-modal');

            if (previewModal && previewModal.classList.contains('active')) {
                closeFMPreviewModal();
            } else if (confirmModal && confirmModal.classList.contains('active')) {
                closeDeleteConfirm();
            } else if (modal && modal.classList.contains('active')) {
                closeFacultyManagementModal();
            }
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
