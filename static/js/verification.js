/**
 * Email Verification and First Login Flow
 * Handles verification code input and password change for first-time users
 */

// State - userEmail should be set by inline script before this file loads
// If not set, initialize it
if (typeof userEmail === 'undefined') {
    var userEmail = '';
}
if (typeof isFirstLogin === 'undefined') {
    var isFirstLogin = false;
}

// Check on page load if we need verification
window.addEventListener('DOMContentLoaded', () => {
    // Check if first login flag is passed from template or set in sessionStorage
    const firstLoginFromTemplate = document.body.dataset.firstLogin === 'true';
    isFirstLogin = firstLoginFromTemplate || sessionStorage.getItem('first_login') === 'true';

    if (isFirstLogin) {
        showVerificationModal();
    }
});

function showVerificationModal() {
    const modal = document.getElementById('verification-modal');
    modal.classList.add('open');

    // Set up code inputs
    setupCodeInputs();
}

function setupCodeInputs() {
    const inputs = document.querySelectorAll('.code-input');

    inputs.forEach((input, index) => {
        // Auto-focus next input
        input.addEventListener('input', (e) => {
            const value = e.target.value;

            // Only allow numbers
            e.target.value = value.replace(/[^0-9]/g, '');

            if (e.target.value) {
                e.target.classList.add('filled');

                // Move to next input
                if (index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
            } else {
                e.target.classList.remove('filled');
            }

            // Clear error state when typing
            inputs.forEach(inp => inp.classList.remove('error'));
            document.getElementById('verification-error').textContent = '';
        });

        // Handle backspace
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                inputs[index - 1].focus();
                inputs[index - 1].value = '';
                inputs[index - 1].classList.remove('filled');
            }

            // Submit on Enter
            if (e.key === 'Enter') {
                submitVerificationCode();
            }
        });

        // Handle paste
        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '');

            // Fill inputs with pasted code
            for (let i = 0; i < Math.min(pastedData.length, inputs.length); i++) {
                inputs[i].value = pastedData[i];
                inputs[i].classList.add('filled');
            }

            // Focus last filled input
            const lastFilledIndex = Math.min(pastedData.length - 1, inputs.length - 1);
            if (lastFilledIndex >= 0) {
                inputs[lastFilledIndex].focus();
            }
        });
    });

    // Focus first input
    inputs[0].focus();
}

async function submitVerificationCode() {
    const inputs = document.querySelectorAll('.code-input');
    const code = Array.from(inputs).map(input => input.value).join('');

    if (code.length !== 6) {
        showVerificationError('Please enter all 6 digits');
        return;
    }

    const errorDiv = document.getElementById('verification-error');
    const submitBtn = document.getElementById('verify-submit-btn');

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying...';
        errorDiv.textContent = '';

        const response = await fetch('/api/auth/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: userEmail,
                code: code
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Verification successful - show password change modal
            document.getElementById('verification-modal').classList.remove('open');
            document.getElementById('password-change-modal').classList.add('open');
        } else {
            showVerificationError(data.error || 'Invalid code. Please try again.');

            // Clear inputs and show error state
            inputs.forEach(input => {
                input.value = '';
                input.classList.remove('filled');
                input.classList.add('error');
            });

            setTimeout(() => {
                inputs.forEach(input => input.classList.remove('error'));
                inputs[0].focus();
            }, 400);
        }
    } catch (error) {
        console.error('Verification error:', error);
        showVerificationError('Network error. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Verify Code';
    }
}

function showVerificationError(message) {
    const errorDiv = document.getElementById('verification-error');
    errorDiv.textContent = message;
}

async function resendVerificationCode() {
    const resendBtn = document.getElementById('resend-code-btn');
    const originalText = resendBtn.textContent;

    try {
        resendBtn.disabled = true;
        resendBtn.textContent = 'Sending...';

        const response = await fetch('/api/auth/resend-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmail })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            resendBtn.textContent = 'Code sent! ✓';
            document.getElementById('verification-error').textContent = '';
            document.getElementById('verification-error').style.color = '#10b981';
            document.getElementById('verification-error').textContent = 'New code sent to your email!';

            setTimeout(() => {
                document.getElementById('verification-error').textContent = '';
                document.getElementById('verification-error').style.color = '#ef4444';
            }, 3000);

            // Clear and reset inputs
            const inputs = document.querySelectorAll('.code-input');
            inputs.forEach(input => {
                input.value = '';
                input.classList.remove('filled', 'error');
            });
            inputs[0].focus();
        } else {
            showVerificationError(data.error || 'Failed to resend code');
        }
    } catch (error) {
        console.error('Resend error:', error);
        showVerificationError('Network error. Please try again.');
    } finally {
        setTimeout(() => {
            resendBtn.disabled = false;
            resendBtn.textContent = originalText;
        }, 3000);
    }
}

async function submitPasswordChange() {
    const passwordInput = document.getElementById('new-password-input');
    const newPassword = passwordInput.value.trim();

    if (!newPassword) {
        showNotificationModal('Please enter a new password', 'warning');
        return;
    }

    if (newPassword.length < 6) {
        showNotificationModal('Password must be at least 6 characters', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/auth/complete-first-login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_password: newPassword })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Clear first login flag
            sessionStorage.removeItem('first_login');

            // Close modal and refresh
            document.getElementById('password-change-modal').classList.remove('open');

            // Show success message
            showNotificationModal('Password changed successfully! Welcome to CERP.', 'success', () => {
                window.location.reload();
            });
        } else {
            showNotificationModal(data.error || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Password change error:', error);
        showNotificationModal('Network error. Please try again.', 'error');
    }
}

async function skipPasswordChange() {
    // Show confirmation modal with warning
    showConfirmModal(
        'Skip Password Change?',
        '⚠️ Are you sure you want to skip changing your password?\n\n' +
        'Security Risk: Your account will remain with the default password.\n' +
        'We strongly recommend changing it now for your account security.\n\n' +
        'You can change it later in Account Settings.',
        async () => {
            try {
                const response = await fetch('/api/auth/complete-first-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skip_password_change: true })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Clear first login flag
                    sessionStorage.removeItem('first_login');

                    // Close modal and refresh
                    document.getElementById('password-change-modal').classList.remove('open');

                    // Show success message
                    showNotificationModal('Welcome to CERP! Remember to change your password in Settings for better security.', 'success', () => {
                        window.location.reload();
                    });
                } else {
                    showNotificationModal(data.error || 'Failed to complete setup', 'error');
                }
            } catch (error) {
                console.error('Skip password error:', error);
                showNotificationModal('Network error. Please try again.', 'error');
            }
        }
    );
}

// Reusable notification modal
function showNotificationModal(message, type = 'info', callback = null) {
    // Remove existing notification modal if any
    const existingModal = document.getElementById('notification-modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    const overlay = document.createElement('div');
    overlay.id = 'notification-modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        animation: fadeIn 0.2s ease;
    `;

    overlay.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 400px; width: 90%; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); animation: slideUp 0.3s ease;">
            <div style="text-align: center; margin-bottom: 16px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: ${colors[type]}20; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                    <span style="font-size: 24px; color: ${colors[type]};">${icons[type]}</span>
                </div>
                <p style="font-size: 15px; color: #374151; margin: 0; white-space: pre-wrap; line-height: 1.6;">${message}</p>
            </div>
            <button onclick="document.getElementById('notification-modal-overlay').remove(); ${callback ? 'this.callbackFn()' : ''}" 
                    style="width: 100%; padding: 10px; background: ${colors[type]}; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;">
                OK
            </button>
        </div>
        <style>
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
        </style>
    `;

    if (callback) {
        overlay.querySelector('button').callbackFn = callback;
    }

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
            if (callback) callback();
        }
    });
}

// Reusable confirmation modal
function showConfirmModal(title, message, onConfirm, onCancel = null) {
    // Remove existing confirm modal if any
    const existingModal = document.getElementById('confirm-modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    const overlay = document.createElement('div');
    overlay.id = 'confirm-modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        animation: fadeIn 0.2s ease;
    `;

    overlay.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 450px; width: 90%; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); animation: slideUp 0.3s ease;">
            <h3 style="font-size: 18px; font-weight: 700; color: #111827; margin: 0 0 12px 0;">${title}</h3>
            <p style="font-size: 14px; color: #6b7280; margin: 0 0 24px 0; white-space: pre-wrap; line-height: 1.6;">${message}</p>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button class="cancel-btn" style="padding: 10px 20px; background: white; color: #374151; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;">
                    Cancel
                </button>
                <button class="confirm-btn" style="padding: 10px 20px; background: #ef4444; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;">
                    Continue
                </button>
            </div>
        </div>
        <style>
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            .cancel-btn:hover {
                background: #f9fafb;
                border-color: #9ca3af;
            }
            .confirm-btn:hover {
                background: #dc2626;
            }
        </style>
    `;

    document.body.appendChild(overlay);

    // Handle cancel
    const cancelBtn = overlay.querySelector('.cancel-btn');
    cancelBtn.addEventListener('click', () => {
        overlay.remove();
        if (onCancel) onCancel();
    });

    // Handle confirm
    const confirmBtn = overlay.querySelector('.confirm-btn');
    confirmBtn.addEventListener('click', () => {
        overlay.remove();
        if (onConfirm) onConfirm();
    });

    // Close on overlay click (acts as cancel)
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
            if (onCancel) onCancel();
        }
    });
}

// Logout function (if not already defined)
async function doLogout() {
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
