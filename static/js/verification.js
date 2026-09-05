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
        alert('Please enter a new password');
        return;
    }

    if (newPassword.length < 6) {
        alert('Password must be at least 6 characters');
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
            alert('Password changed successfully! Welcome to CERP.');

            // Reload to show dashboard
            window.location.reload();
        } else {
            alert(data.error || 'Failed to change password');
        }
    } catch (error) {
        console.error('Password change error:', error);
        alert('Network error. Please try again.');
    }
}

async function skipPasswordChange() {
    if (!confirm('Are you sure you want to skip changing your password? You can change it later in Settings.')) {
        return;
    }

    try {
        const response = await fetch('/api/auth/complete-first-login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Clear first login flag
            sessionStorage.removeItem('first_login');

            // Close modal and refresh
            document.getElementById('password-change-modal').classList.remove('open');

            // Show success message
            alert('Welcome to CERP! You can change your password anytime in Settings.');

            // Reload to show dashboard
            window.location.reload();
        } else {
            alert(data.error || 'Failed to complete setup');
        }
    } catch (error) {
        console.error('Skip password error:', error);
        alert('Network error. Please try again.');
    }
}

// Logout function (if not already defined)
function doLogout() {
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            sessionStorage.clear();
            window.location.href = '/login';
        })
        .catch(err => {
            console.error('Logout error:', err);
            window.location.href = '/login';
        });
}
