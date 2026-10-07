/**
 * Forgot Password Flow with CAPTCHA Protection
 * 
 * Flow:
 * 1. User enters their User ID (employee/student ID)
 * 2. System sends 6-digit code to registered email
 * 3. User enters the code
 * 4. User completes CAPTCHA verification
 * 5. User sets new password
 */

// Global state for the forgot password flow
const forgotPasswordState = {
    step: 1, // 1: Enter ID, 2: Enter Code, 3: CAPTCHA, 4: Reset Password
    userId: null,
    userEmail: null,
    codeVerified: false,
    captchaVerified: false,
    resendCooldown: 0,
    resendTimer: null
};

/**
 * Show the forgot password modal
 */
function showForgotPasswordModal() {
    // Reset state
    forgotPasswordState.step = 1;
    forgotPasswordState.userId = null;
    forgotPasswordState.userEmail = null;
    forgotPasswordState.codeVerified = false;
    forgotPasswordState.captchaVerified = false;

    // Create modal HTML
    const modalHTML = `
        <div id="forgot-password-overlay" class="modal-overlay">
            <div class="modal-container" onclick="event.stopPropagation()">
                <button class="modal-close-btn" onclick="closeForgotPasswordModal()">
                    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>

                <div class="modal-header">
                    <div class="modal-icon">
                        <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
                        </svg>
                    </div>
                    <h2 class="modal-title">Forgot Password</h2>
                    <p class="modal-subtitle" id="modal-subtitle">Enter your User ID to receive a reset code</p>
                </div>

                <div class="modal-body">
                    <!-- Step 1: Enter User ID -->
                    <div id="step-user-id" class="step-container">
                        <div class="form-group">
                            <label for="user-id-input" class="form-label">User ID</label>
                            <input 
                                type="text" 
                                id="user-id-input" 
                                class="form-input" 
                                placeholder="e.g., 2021-12345"
                                autocomplete="off"
                                maxlength="20"
                            />
                            <p class="form-hint">Enter your employee or student ID (format: YYYY-XXXXX)</p>
                        </div>
                        <div id="step1-error" class="error-message"></div>
                        <button class="btn-primary" onclick="submitUserId()">
                            <span class="btn-text">Send Reset Code</span>
                            <span class="btn-loader"></span>
                        </button>
                    </div>

                    <!-- Step 2: Enter Verification Code -->
                    <div id="step-verify-code" class="step-container" style="display: none;">
                        <div class="email-sent-notice">
                            <svg width="48" height="48" fill="none" viewBox="0 0 24 24">
                                <path stroke="#10b981" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                            <p>We've sent a 6-digit code to <strong id="user-email-display"></strong></p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Enter Verification Code</label>
                            <div class="code-inputs">
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                                <input type="text" class="code-input" maxlength="1" pattern="[0-9]" inputmode="numeric" />
                            </div>
                            <p class="form-hint">Check your email for the verification code</p>
                        </div>
                        <div id="step2-error" class="error-message"></div>
                        <button class="btn-primary" onclick="submitVerificationCode()">
                            <span class="btn-text">Verify Code</span>
                            <span class="btn-loader"></span>
                        </button>
                        <button class="btn-secondary" id="resend-code-btn" onclick="resendCode()">
                            Resend Code
                        </button>
                    </div>

                    <!-- Step 3: CAPTCHA Verification -->
                    <div id="step-captcha" class="step-container" style="display: none;">
                        <div class="captcha-container">
                            <p class="captcha-instruction">Please verify you're human</p>
                            <div class="captcha-box">
                                <canvas id="captcha-canvas" width="240" height="80"></canvas>
                                <button class="captcha-refresh" onclick="generateCaptcha()" title="Generate new CAPTCHA">
                                    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                    </svg>
                                </button>
                            </div>
                            <div class="form-group" style="margin-top: 16px;">
                                <label for="captcha-input" class="form-label">Enter the text above</label>
                                <input 
                                    type="text" 
                                    id="captcha-input" 
                                    class="form-input" 
                                    placeholder="Type the characters you see"
                                    autocomplete="off"
                                    maxlength="6"
                                />
                            </div>
                        </div>
                        <div id="step3-error" class="error-message"></div>
                        <button class="btn-primary" onclick="submitCaptcha()">
                            <span class="btn-text">Verify CAPTCHA</span>
                            <span class="btn-loader"></span>
                        </button>
                    </div>

                    <!-- Step 4: Reset Password -->
                    <div id="step-reset-password" class="step-container" style="display: none;">
                        <div class="success-notice">
                            <svg width="48" height="48" fill="none" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="10" stroke="#10b981" stroke-width="1.5"/>
                                <path stroke="#10b981" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/>
                            </svg>
                            <p>Verification successful! Set your new password.</p>
                        </div>
                        <div class="form-group">
                            <label for="new-password" class="form-label">New Password</label>
                            <div class="password-field">
                                <input 
                                    type="password" 
                                    id="new-password" 
                                    class="form-input" 
                                    placeholder="Enter new password"
                                    autocomplete="new-password"
                                    minlength="6"
                                />
                                <button type="button" class="password-toggle-inline" onclick="togglePasswordField('new-password')">
                                    <svg class="icon-show" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12s3.75-6.75 9.75-6.75S21.75 12 21.75 12s-3.75 6.75-9.75 6.75S2.25 12 2.25 12z" />
                                        <circle cx="12" cy="12" r="3" />
                                    </svg>
                                    <svg class="icon-hide" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18M10.5 10.7a3 3 0 004.1 4.1M9.9 5.5A10.7 10.7 0 0112 5.25C18 5.25 21.75 12 21.75 12a18.4 18.4 0 01-4.2 4.7M6.4 6.6A18.5 18.5 0 002.25 12S6 18.75 12 18.75c1.4 0 2.7-.3 3.9-.8" />
                                    </svg>
                                </button>
                            </div>
                            <p class="form-hint">At least 6 characters</p>
                        </div>
                        <div class="form-group">
                            <label for="confirm-password" class="form-label">Confirm Password</label>
                            <div class="password-field">
                                <input 
                                    type="password" 
                                    id="confirm-password" 
                                    class="form-input" 
                                    placeholder="Confirm new password"
                                    autocomplete="new-password"
                                    minlength="6"
                                />
                                <button type="button" class="password-toggle-inline" onclick="togglePasswordField('confirm-password')">
                                    <svg class="icon-show" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12s3.75-6.75 9.75-6.75S21.75 12 21.75 12s-3.75 6.75-9.75 6.75S2.25 12 2.25 12z" />
                                        <circle cx="12" cy="12" r="3" />
                                    </svg>
                                    <svg class="icon-hide" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18M10.5 10.7a3 3 0 004.1 4.1M9.9 5.5A10.7 10.7 0 0112 5.25C18 5.25 21.75 12 21.75 12a18.4 18.4 0 01-4.2 4.7M6.4 6.6A18.5 18.5 0 002.25 12S6 18.75 12 18.75c1.4 0 2.7-.3 3.9-.8" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                        <div id="step4-error" class="error-message"></div>
                        <button class="btn-primary" onclick="submitPasswordReset()">
                            <span class="btn-text">Reset Password</span>
                            <span class="btn-loader"></span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('forgot-password-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    // Insert modal into DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Setup code inputs for step 2
    setupCodeInputs();

    // Show modal with animation
    setTimeout(() => {
        document.getElementById('forgot-password-overlay').classList.add('active');
    }, 10);

    // Focus first input
    setTimeout(() => {
        document.getElementById('user-id-input').focus();
    }, 300);
}

/**
 * Close the forgot password modal
 */
function closeForgotPasswordModal() {
    const overlay = document.getElementById('forgot-password-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300);
    }
}

/**
 * Step 1: Submit User ID
 */
async function submitUserId() {
    const input = document.getElementById('user-id-input');
    const userId = input.value.trim();
    const errorDiv = document.getElementById('step1-error');
    const btn = event.target.closest('.btn-primary');

    // Validate input
    if (!userId) {
        showError(errorDiv, 'Please enter your User ID');
        return;
    }

    // User ID format validation (YYYY-XXXXX or similar)
    if (userId.length < 4) {
        showError(errorDiv, 'Invalid User ID format');
        return;
    }

    // Set loading state
    setButtonLoading(btn, true);
    errorDiv.textContent = '';

    try {
        const response = await fetch('/api/forgot-password/send-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Store state and move to step 2
            forgotPasswordState.userId = userId;
            forgotPasswordState.userEmail = data.email_masked;

            showStep(2);
            document.getElementById('user-email-display').textContent = data.email_masked;

            // Start resend cooldown
            startResendCooldown(60); // 60 seconds
        } else {
            showError(errorDiv, data.error || 'User not found. Please check your User ID.');
        }
    } catch (error) {
        console.error('Send code error:', error);
        showError(errorDiv, 'Network error. Please try again.');
    } finally {
        setButtonLoading(btn, false);
    }
}

/**
 * Step 2: Submit Verification Code
 */
async function submitVerificationCode() {
    const inputs = document.querySelectorAll('#step-verify-code .code-input');
    const code = Array.from(inputs).map(input => input.value).join('');
    const errorDiv = document.getElementById('step2-error');
    const btn = event.target.closest('.btn-primary');

    if (code.length !== 6) {
        showError(errorDiv, 'Please enter all 6 digits');
        return;
    }

    setButtonLoading(btn, true);
    errorDiv.textContent = '';

    try {
        const response = await fetch('/api/forgot-password/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: forgotPasswordState.userId,
                code: code
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            forgotPasswordState.codeVerified = true;

            // Move to CAPTCHA step
            showStep(3);
            generateCaptcha();
        } else {
            showError(errorDiv, data.error || 'Invalid code. Please try again.');

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
        console.error('Verify code error:', error);
        showError(errorDiv, 'Network error. Please try again.');
    } finally {
        setButtonLoading(btn, false);
    }
}

/**
 * Step 3: Submit CAPTCHA
 */
function submitCaptcha() {
    const input = document.getElementById('captcha-input');
    const userAnswer = input.value.trim().toUpperCase();
    const errorDiv = document.getElementById('step3-error');
    const btn = event.target.closest('.btn-primary');

    if (!userAnswer) {
        showError(errorDiv, 'Please enter the CAPTCHA text');
        return;
    }

    // Verify CAPTCHA
    if (userAnswer === window.captchaAnswer) {
        forgotPasswordState.captchaVerified = true;

        // Move to password reset step
        showStep(4);
    } else {
        showError(errorDiv, 'Incorrect CAPTCHA. Please try again.');
        generateCaptcha(); // Generate new CAPTCHA
        input.value = '';
        input.focus();
    }
}

/**
 * Step 4: Submit Password Reset
 */
async function submitPasswordReset() {
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const errorDiv = document.getElementById('step4-error');
    const btn = event.target.closest('.btn-primary');

    // Validate passwords
    if (!newPassword || !confirmPassword) {
        showError(errorDiv, 'Please fill in both password fields');
        return;
    }

    if (newPassword.length < 6) {
        showError(errorDiv, 'Password must be at least 6 characters');
        return;
    }

    if (newPassword !== confirmPassword) {
        showError(errorDiv, 'Passwords do not match');
        return;
    }

    setButtonLoading(btn, true);
    errorDiv.textContent = '';

    try {
        const response = await fetch('/api/forgot-password/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: forgotPasswordState.userId,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Show success message and redirect to login
            closeForgotPasswordModal();

            showSuccessNotification(
                'Password reset successful!',
                'You can now log in with your new password.',
                () => {
                    // Optionally auto-fill the email field
                    const emailInput = document.getElementById('email');
                    if (emailInput && forgotPasswordState.userEmail) {
                        // Remove masking if we have full email
                        emailInput.value = data.email || '';
                    }
                }
            );
        } else {
            showError(errorDiv, data.error || 'Failed to reset password. Please try again.');
        }
    } catch (error) {
        console.error('Reset password error:', error);
        showError(errorDiv, 'Network error. Please try again.');
    } finally {
        setButtonLoading(btn, false);
    }
}

/**
 * Resend verification code
 */
async function resendCode() {
    if (forgotPasswordState.resendCooldown > 0) {
        return; // Still in cooldown
    }

    const btn = document.getElementById('resend-code-btn');
    const originalText = btn.textContent;

    try {
        btn.disabled = true;
        btn.textContent = 'Sending...';

        const response = await fetch('/api/forgot-password/send-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: forgotPasswordState.userId })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            btn.textContent = 'Code sent! ✓';

            // Clear inputs
            const inputs = document.querySelectorAll('#step-verify-code .code-input');
            inputs.forEach(input => {
                input.value = '';
                input.classList.remove('filled', 'error');
            });
            inputs[0].focus();

            // Start cooldown again
            startResendCooldown(60);

            setTimeout(() => {
                if (forgotPasswordState.resendCooldown === 0) {
                    btn.textContent = originalText;
                }
            }, 3000);
        } else {
            btn.textContent = originalText;
            showError(document.getElementById('step2-error'), data.error || 'Failed to resend code');
        }
    } catch (error) {
        console.error('Resend error:', error);
        btn.textContent = originalText;
        showError(document.getElementById('step2-error'), 'Network error. Please try again.');
    }
}

/**
 * Start resend cooldown timer
 */
function startResendCooldown(seconds) {
    forgotPasswordState.resendCooldown = seconds;
    const btn = document.getElementById('resend-code-btn');

    if (forgotPasswordState.resendTimer) {
        clearInterval(forgotPasswordState.resendTimer);
    }

    forgotPasswordState.resendTimer = setInterval(() => {
        forgotPasswordState.resendCooldown--;

        if (forgotPasswordState.resendCooldown > 0) {
            btn.textContent = `Resend Code (${forgotPasswordState.resendCooldown}s)`;
            btn.disabled = true;
        } else {
            btn.textContent = 'Resend Code';
            btn.disabled = false;
            clearInterval(forgotPasswordState.resendTimer);
        }
    }, 1000);
}

/**
 * Generate CAPTCHA
 */
function generateCaptcha() {
    const canvas = document.getElementById('captcha-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // Exclude confusing characters
    let captchaText = '';

    // Generate 6 random characters
    for (let i = 0; i < 6; i++) {
        captchaText += chars.charAt(Math.floor(Math.random() * chars.length));
    }

    // Store answer
    window.captchaAnswer = captchaText;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Add background with noise
    ctx.fillStyle = '#f9fafb';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Add noise lines
    for (let i = 0; i < 5; i++) {
        ctx.strokeStyle = `rgba(${Math.random() * 100 + 100}, ${Math.random() * 100 + 100}, ${Math.random() * 100 + 100}, 0.3)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.stroke();
    }

    // Draw text
    ctx.font = 'bold 32px Arial';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < captchaText.length; i++) {
        const char = captchaText[i];
        const x = 20 + i * 35;
        const y = 40 + (Math.random() - 0.5) * 10;
        const angle = (Math.random() - 0.5) * 0.4;

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);

        // Random color for each character
        const hue = Math.random() * 360;
        ctx.fillStyle = `hsl(${hue}, 70%, 40%)`;
        ctx.fillText(char, 0, 0);

        ctx.restore();
    }

    // Add dots
    for (let i = 0; i < 30; i++) {
        ctx.fillStyle = `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.3)`;
        ctx.beginPath();
        ctx.arc(Math.random() * canvas.width, Math.random() * canvas.height, Math.random() * 2, 0, Math.PI * 2);
        ctx.fill();
    }

    // Clear input
    const input = document.getElementById('captcha-input');
    if (input) {
        input.value = '';
    }
}

/**
 * Show specific step
 */
function showStep(stepNumber) {
    forgotPasswordState.step = stepNumber;

    // Hide all steps
    document.querySelectorAll('.step-container').forEach(container => {
        container.style.display = 'none';
    });

    // Update subtitle
    const subtitles = {
        1: 'Enter your User ID to receive a reset code',
        2: 'Check your email for the verification code',
        3: 'Verify you\'re human to proceed',
        4: 'Create a strong new password for your account'
    };

    document.getElementById('modal-subtitle').textContent = subtitles[stepNumber];

    // Show current step
    const steps = {
        1: 'step-user-id',
        2: 'step-verify-code',
        3: 'step-captcha',
        4: 'step-reset-password'
    };

    const currentStep = document.getElementById(steps[stepNumber]);
    if (currentStep) {
        currentStep.style.display = 'block';

        // Focus first input in step
        setTimeout(() => {
            const firstInput = currentStep.querySelector('input:not([type="hidden"])');
            if (firstInput) {
                firstInput.focus();
            }
        }, 100);
    }
}

/**
 * Setup code inputs for auto-advance and paste handling
 */
function setupCodeInputs() {
    setTimeout(() => {
        const inputs = document.querySelectorAll('#step-verify-code .code-input');

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
                document.getElementById('step2-error').textContent = '';
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
    }, 100);
}

/**
 * Toggle password visibility
 */
function togglePasswordField(fieldId) {
    const input = document.getElementById(fieldId);
    const btn = event.target.closest('.password-toggle-inline');

    if (!input || !btn) return;

    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';

    const showIcon = btn.querySelector('.icon-show');
    const hideIcon = btn.querySelector('.icon-hide');

    if (showIcon && hideIcon) {
        showIcon.style.display = isPassword ? 'none' : 'block';
        hideIcon.style.display = isPassword ? 'block' : 'none';
    }
}

/**
 * Helper: Show error message
 */
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
}

/**
 * Helper: Set button loading state
 */
function setButtonLoading(button, isLoading) {
    if (!button) return;

    const text = button.querySelector('.btn-text');
    const loader = button.querySelector('.btn-loader');

    if (isLoading) {
        button.disabled = true;
        button.classList.add('loading');
        if (text) text.style.opacity = '0';
        if (loader) loader.style.display = 'block';
    } else {
        button.disabled = false;
        button.classList.remove('loading');
        if (text) text.style.opacity = '1';
        if (loader) loader.style.display = 'none';
    }
}

/**
 * Show success notification
 */
function showSuccessNotification(title, message, callback = null) {
    const overlay = document.createElement('div');
    overlay.id = 'success-notification-overlay';
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
        <div style="background: white; border-radius: 12px; padding: 32px; max-width: 400px; width: 90%; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); animation: slideUp 0.3s ease; text-align: center;">
            <div style="width: 64px; height: 64px; border-radius: 50%; background: #10b98120; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                <svg width="32" height="32" fill="none" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="#10b981" stroke-width="2"/>
                    <path stroke="#10b981" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/>
                </svg>
            </div>
            <h3 style="font-size: 20px; font-weight: 700; color: #111827; margin: 0 0 8px 0;">${title}</h3>
            <p style="font-size: 14px; color: #6b7280; margin: 0 0 24px 0; line-height: 1.6;">${message}</p>
            <button onclick="document.getElementById('success-notification-overlay').remove(); ${callback ? 'this.callbackFn()' : ''}" 
                    style="width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                Continue to Login
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
}
