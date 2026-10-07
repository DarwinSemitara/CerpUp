// Enhanced Timeline Rendering with Filters and Preview
// This file contains the updated timeline functions for the faculty management modal

function renderFMTimeline(activityData) {
    const container = document.getElementById('fm-timeline');
    if (!container) return;

    // Collect all activities with dates and IDs
    const activities = [];

    // Add research papers
    if (activityData.research) {
        activityData.research.forEach(item => {
            activities.push({
                type: 'research',
                id: item.id,
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
                id: item.id,
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
                id: item.id,
                title: 'Administrative Work (FSR)',
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

    // Store for filtering
    window.allTimelineActivities = activities;
    window.currentTimelineFilter = 'all';

    // Render with filters
    renderTimelineWithFilters('all');
}

function renderTimelineWithFilters(filter) {
    const container = document.getElementById('fm-timeline');
    if (!container) return;

    const activities = window.allTimelineActivities || [];
    window.currentTimelineFilter = filter;

    // Filter activities
    let filteredActivities = activities;
    if (filter !== 'all') {
        filteredActivities = activities.filter(a => a.type === filter);
    }

    // Limit to 30 most recent
    const displayActivities = filteredActivities.slice(0, 30);

    // Build HTML with filter buttons
    let html = `
        <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;">
            <button class="fm-timeline-filter ${filter === 'all' ? 'active' : ''}" onclick="renderTimelineWithFilters('all')">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                </svg>
                All (${activities.length})
            </button>
            <button class="fm-timeline-filter ${filter === 'research' ? 'active' : ''}" onclick="renderTimelineWithFilters('research')">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                Research (${activities.filter(a => a.type === 'research').length})
            </button>
            <button class="fm-timeline-filter ${filter === 'extension' ? 'active' : ''}" onclick="renderTimelineWithFilters('extension')">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
                Extensions (${activities.filter(a => a.type === 'extension').length})
            </button>
            <button class="fm-timeline-filter ${filter === 'admin' ? 'active' : ''}" onclick="renderTimelineWithFilters('admin')">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                Admin (${activities.filter(a => a.type === 'admin').length})
            </button>
        </div>
    `;

    if (displayActivities.length === 0) {
        html += `
            <div style="text-align:center;padding:60px 20px;color:#9ca3af;">
                <svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin:0 auto 16px;opacity:0.3;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <div style="font-size:1rem;font-weight:600;color:#6b7280;">No submissions found</div>
                <div style="font-size:0.875rem;color:#9ca3af;margin-top:4px;">Try selecting a different filter</div>
            </div>
        `;
        container.innerHTML = html;
        return;
    }

    // Render timeline cards in grid
    html += '<div class="fm-timeline-grid">';
    
    displayActivities.forEach(activity => {
        const dateObj = new Date(activity.date);
        const formattedDate = dateObj.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric'
        });
        const formattedTime = dateObj.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        html += `
            <div class="fm-timeline-card">
                <div class="fm-timeline-card-header">
                    <div class="fm-timeline-card-icon" style="background:${activity.bg};color:${activity.color};">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${activity.icon}"/>
                        </svg>
                    </div>
                    <div style="flex:1;min-width:0;">
                        <div class="fm-timeline-card-title">${escapeHtml(activity.title)}</div>
                        <div class="fm-timeline-card-meta">
                            <span>${formattedDate}</span>
                            <span>•</span>
                            <span>${formattedTime}</span>
                        </div>
                    </div>
                    <span class="fm-timeline-card-badge" style="background:${activity.badgeBg};color:${activity.badgeColor};">
                        ${activity.badge}
                    </span>
                </div>
                <div class="fm-timeline-card-actions">
                    <button class="fm-timeline-action-btn" onclick="previewSubmission('${activity.type}', '${activity.id}', '${escapeHtml(activity.title)}')">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        </svg>
                        View
                    </button>
                </div>
            </div>
        `;
    });

    html += '</div>';

    container.innerHTML = html;
}

function previewSubmission(type, id, title) {
    // Open preview modal
    const modal = document.getElementById('fm-preview-modal');
    if (!modal) return;

    const typeLabel = type === 'research' ? 'Research' : type === 'extension' ? 'Extension' : 'Admin Work';
    document.getElementById('fm-preview-title').textContent = title;
    document.getElementById('fm-preview-type').textContent = typeLabel;
    document.getElementById('fm-preview-content').innerHTML = `
        <div style="text-align:center;padding:80px 20px;color:#9ca3af;">
            <svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="margin:0 auto 20px;opacity:0.3;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            <div style="font-size:1.1rem;font-weight:600;color:#6b7280;margin-bottom:8px;">Preview Coming Soon</div>
            <div style="font-size:0.9rem;color:#9ca3af;">File preview functionality will be implemented here</div>
            <div style="margin-top:16px;padding:12px 20px;background:#f3f4f6;border-radius:8px;display:inline-block;">
                <div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Submission ID</div>
                <div style="font-size:0.85rem;font-weight:600;color:#111827;font-family:monospace;">${id}</div>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closeFMPreviewModal() {
    const modal = document.getElementById('fm-preview-modal');
    if (modal) modal.classList.remove('active');
}
