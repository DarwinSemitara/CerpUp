/* ══════════════════════════════════════════════════════════════
   CERP Admin Dashboard - Shared JavaScript
   ══════════════════════════════════════════════════════════════ */

// ── Navigation ────────────────────────────────────────────────

function setNavActive(element) {
    if (!element) return;
    document.querySelectorAll('.nav-item, .sub-nav-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
}

async function loadPartial(url, title, element) {
    setNavActive(element);
    document.getElementById('page-title').textContent = title;
    const content = document.getElementById('content');
    content.innerHTML = '<div class="content-spinner"><div class="spinner-ring"></div> Loading…</div>';

    // Update URL without reloading page
    const newUrl = url.startsWith('/') ? url : '/' + url;
    history.pushState({ url, title }, title, newUrl);

    try {
        const res = await fetch(url, { headers: { 'X-Partial': '1' }, cache: 'no-store' });
        if (!res.ok) throw new Error('Failed to load');
        const html = await res.text();
        content.innerHTML = html;

        // Execute any scripts in the loaded partial
        const scripts = content.querySelectorAll('script');
        scripts.forEach(oldScript => {
            const s = document.createElement('script');
            if (oldScript.src) {
                s.src = oldScript.src;
            } else {
                s.textContent = oldScript.textContent;
            }
            document.body.appendChild(s);
            // Keep script in DOM briefly to ensure execution
            setTimeout(() => {
                if (s.parentNode) document.body.removeChild(s);
            }, 100);
        });
    } catch (err) {
        content.innerHTML = `<div class="welcome-section"><div class="welcome-title">${title}</div><div class="welcome-text">Failed to load content. Please try again.</div></div>`;
    }
}

// Handle browser back/forward buttons
window.addEventListener('popstate', (event) => {
    if (event.state && event.state.url) {
        const content = document.getElementById('content');
        content.innerHTML = '<div class="content-spinner"><div class="spinner-ring"></div> Loading…</div>';
        fetch(event.state.url, { headers: { 'X-Partial': '1' }, cache: 'no-store' })
            .then(res => res.text())
            .then(html => {
                content.innerHTML = html;
                document.getElementById('page-title').textContent = event.state.title;
                // Re-execute scripts
                const scripts = content.querySelectorAll('script');
                scripts.forEach(oldScript => {
                    const s = document.createElement('script');
                    if (oldScript.src) {
                        s.src = oldScript.src;
                    } else {
                        s.textContent = oldScript.textContent;
                    }
                    document.body.appendChild(s);
                    setTimeout(() => {
                        if (s.parentNode) document.body.removeChild(s);
                    }, 100);
                });
            })
            .catch(() => {
                content.innerHTML = `<div class="welcome-section"><div class="welcome-title">${event.state.title}</div><div class="welcome-text">Failed to load content. Please try again.</div></div>`;
            });
    }
});

function toggleSubNav(subNavId, button, isSubItem = false) {
    const subNav = document.getElementById(subNavId);
    if (!subNav) return;

    // Toggle only this specific dropdown, don't close others
    subNav.classList.toggle('open');

    // Rotate chevron if present
    const chevron = isSubItem
        ? document.getElementById('tap-chevron')
        : button.querySelector('.nav-chevron');
    if (chevron) chevron.style.transform = subNav.classList.contains('open') ? 'rotate(180deg)' : '';
}

// ── Logout ────────────────────────────────────────────────────

let logoutModal = null;

function openLogoutModal() {
    if (!logoutModal) {
        logoutModal = document.getElementById('logout-modal');
    }
    if (logoutModal) {
        logoutModal.classList.add('open');
    }
}

function closeLogoutModal() {
    if (logoutModal) {
        logoutModal.classList.remove('open');
    }
}

async function confirmLogout() {
    try {
        const response = await fetch('/api/logout', { method: 'POST' });
        const data = await response.json();

        // Clear all session storage and local storage
        sessionStorage.clear();
        localStorage.clear();

        // Force redirect with cache bypass
        window.location.replace(data.redirect || '/login');

        // Prevent back button from working after logout
        window.history.pushState(null, '', window.location.href);
        window.onpopstate = function () {
            window.location.replace('/login');
        };
    } catch (err) {
        console.error('Logout error:', err);
        // Force redirect even if request fails
        sessionStorage.clear();
        localStorage.clear();
        window.location.replace('/login');
    }
}

// ── Utility Functions ─────────────────────────────────────────

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatTime(timeString) {
    if (!timeString) return '';
    const [hours, minutes] = timeString.split(':');
    const h = parseInt(hours);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 || 12;
    return `${h12}:${minutes} ${ampm}`;
}

function toggleDropdown(menuId) {
    const menu = document.getElementById(menuId);
    if (menu) {
        menu.classList.toggle('open');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.gen-report-wrap') && !e.target.closest('.year-selector')) {
        document.querySelectorAll('.gen-report-menu, .year-dropdown').forEach(menu => {
            menu.classList.remove('open');
        });
    }
});

// ── Initialize ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Close modals when clicking outside
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('open');
        }
        // Close logout modal when clicking outside
        if (e.target.id === 'logout-modal') {
            closeLogoutModal();
        }
    });
});


// ══════════════════════════════════════════════════════════════
// Notification System
// ══════════════════════════════════════════════════════════════

let notificationsCache = [];

// Load notifications on page load
document.addEventListener('DOMContentLoaded', function () {
    loadNotifications();

    // Refresh notifications every 30 seconds
    setInterval(loadNotifications, 30000);

    // Close dropdown when clicking outside
    document.addEventListener('click', function (e) {
        const dropdown = document.getElementById('notification-dropdown');
        const bell = document.getElementById('notification-bell');

        if (dropdown && bell && !dropdown.contains(e.target) && !bell.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });
});

function toggleNotifications() {
    const dropdown = document.getElementById('notification-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');

        if (dropdown.classList.contains('active')) {
            loadNotifications();
        }
    }
}

async function loadNotifications() {
    try {
        const res = await fetch('/api/audit-log?unread=true&limit=7');
        if (!res.ok) throw new Error('Failed to load notifications');

        const data = await res.json();
        notificationsCache = data.notifications || [];

        renderNotifications();
        updateNotificationBadge();
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function renderNotifications() {
    const container = document.getElementById('notification-list');
    if (!container) return;

    if (notificationsCache.length === 0) {
        container.innerHTML = `
            <div class="notification-empty">
                <svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                </svg>
                <div class="notification-empty-title">All caught up!</div>
                <div class="notification-empty-desc">No new notifications</div>
            </div>
        `;
        return;
    }

    let html = '';
    notificationsCache.forEach(notif => {
        const icon = getNotificationIcon(notif.action_type);
        const timeAgo = getTimeAgo(notif.created_at);
        const unreadClass = notif.is_read ? '' : 'unread';

        html += `
            <div class="notification-item ${unreadClass}" data-id="${notif.id}">
                <div class="notification-item-header">
                    <div class="notification-item-icon" style="background:${icon.bg};color:${icon.color};">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icon.path}"/>
                        </svg>
                    </div>
                    <div class="notification-item-content">
                        <div class="notification-item-title">${escapeHtml(notif.description)}</div>
                        <div class="notification-item-desc">By ${escapeHtml(notif.performed_by)}</div>
                    </div>
                </div>
                <div class="notification-item-footer">
                    <span class="notification-item-time">${timeAgo}</span>
                    ${!notif.is_read ? '<button class="notification-item-action" onclick="markAsRead(\'' + notif.id + '\', event)">Mark as read</button>' : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function getNotificationIcon(actionType) {
    const icons = {
        'MEMBER_CREATED': {
            path: 'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z',
            color: '#16a34a',
            bg: '#f0fdf4'
        },
        'MEMBER_DELETED': {
            path: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
            color: '#dc2626',
            bg: '#fef3f2'
        },
        'MEMBER_DISABLED': {
            path: 'M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636',
            color: '#f59e0b',
            bg: '#fef9e7'
        },
        'MEMBER_ENABLED': {
            path: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
            color: '#16a34a',
            bg: '#f0fdf4'
        },
        'SCHEDULE_CREATED': {
            path: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
            color: '#2563eb',
            bg: '#eff6ff'
        },
        'SCHEDULE_MODIFIED': {
            path: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
            color: '#f59e0b',
            bg: '#fef9e7'
        },
        'DEFAULT': {
            path: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            color: '#6b7280',
            bg: '#f3f4f6'
        }
    };

    return icons[actionType] || icons.DEFAULT;
}

function getTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return then.toLocaleDateString();
}

function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    const bell = document.getElementById('notification-bell');

    if (!badge || !bell) return;

    const unreadCount = notificationsCache.filter(n => !n.is_read).length;

    if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.style.display = 'block';
        bell.classList.add('has-unread');
    } else {
        badge.style.display = 'none';
        bell.classList.remove('has-unread');
    }
}

async function markAsRead(notificationId, event) {
    if (event) {
        event.stopPropagation();
    }

    try {
        const res = await fetch(`/api/audit-log/${notificationId}/read`, {
            method: 'POST'
        });

        if (res.ok) {
            // Update cache
            const notif = notificationsCache.find(n => n.id === notificationId);
            if (notif) {
                notif.is_read = true;
            }

            renderNotifications();
            updateNotificationBadge();
        }
    } catch (error) {
        console.error('Error marking as read:', error);
    }
}

async function markAllAsRead() {
    try {
        const res = await fetch('/api/audit-log/mark-all-read', {
            method: 'POST'
        });

        if (res.ok) {
            // Update cache
            notificationsCache.forEach(n => n.is_read = true);

            renderNotifications();
            updateNotificationBadge();
        }
    } catch (error) {
        console.error('Error marking all as read:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
