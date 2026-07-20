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
        const res = await fetch(url, { headers: { 'X-Partial': '1' } });
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
        fetch(event.state.url, { headers: { 'X-Partial': '1' } })
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
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch {
        alert('Logout failed. Please try again.');
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
