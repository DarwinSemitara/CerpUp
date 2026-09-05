/**
 * GA Progress Tracker
 * Handles real-time polling and UI updates for async GA schedule generation
 */

class GAProgressTracker {
    constructor() {
        this.sessionId = null;
        this.pollInterval = null;
        this.pollIntervalMs = 2000; // Poll every 2 seconds
        this.progressCallback = null;
        this.completionCallback = null;
        this.errorCallback = null;
    }

    /**
     * Start tracking a GA session
     * @param {string} sessionId - The GA session ID to track
     * @param {function} onProgress - Callback for progress updates (progress object)
     * @param {function} onComplete - Callback when generation completes (result object)
     * @param {function} onError - Callback for errors (error message)
     */
    start(sessionId, onProgress, onComplete, onError) {
        this.sessionId = sessionId;
        this.progressCallback = onProgress;
        this.completionCallback = onComplete;
        this.errorCallback = onError;

        // Start polling
        this.poll();
        this.pollInterval = setInterval(() => this.poll(), this.pollIntervalMs);
    }

    /**
     * Stop tracking and clean up
     */
    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.sessionId = null;
    }

    /**
     * Cancel the running GA session
     */
    async cancel() {
        if (!this.sessionId) return;

        try {
            const response = await fetch(`/api/schedule/ga-cancel/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error('Failed to cancel generation');
            }

            this.stop();
            return await response.json();
        } catch (error) {
            console.error('Cancel error:', error);
            if (this.errorCallback) {
                this.errorCallback(error.message);
            }
        }
    }

    /**
     * Poll the GA status endpoint
     */
    async poll() {
        if (!this.sessionId) return;

        try {
            const response = await fetch(`/api/schedule/ga-status/${this.sessionId}`);

            if (!response.ok) {
                if (response.status === 404) {
                    this.stop();
                    if (this.errorCallback) {
                        this.errorCallback('Session not found or expired');
                    }
                    return;
                }
                if (response.status === 501) {
                    // Not implemented - stop polling and show message
                    this.stop();
                    const data = await response.json();
                    if (this.errorCallback) {
                        this.errorCallback(data.error || 'Async generation not yet implemented');
                    }
                    return;
                }
                throw new Error('Failed to fetch status');
            }

            const data = await response.json();

            if (data.status === 'running') {
                // Update progress
                if (this.progressCallback && data.progress) {
                    this.progressCallback(data.progress);
                }
            } else if (data.status === 'completed') {
                // Generation finished
                this.stop();
                if (this.completionCallback && data.result) {
                    this.completionCallback(data.result);
                }
            } else if (data.status === 'failed') {
                // Generation failed
                this.stop();
                if (this.errorCallback) {
                    this.errorCallback(data.error || 'Generation failed');
                }
            }
        } catch (error) {
            console.error('Poll error:', error);
            // Don't stop polling on network errors - might be temporary
        }
    }
}

/**
 * GA Progress UI Manager
 * Handles displaying progress indicators in the chat panel
 */
class GAProgressUI {
    constructor(containerId = 'ga-progress-container') {
        this.containerId = containerId;
        this.tracker = new GAProgressTracker();
    }

    /**
     * Show progress UI with initial message
     */
    show(sessionId) {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('GA progress container not found');
            return;
        }

        container.innerHTML = `
            <div class="ga-progress-card">
                <div class="ga-progress-header">
                    <div class="ga-progress-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                        </svg>
                    </div>
                    <div class="ga-progress-title">Generating Schedule...</div>
                    <button class="ga-progress-cancel" onclick="window.gaProgressUI.cancel()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="ga-progress-body">
                    <div class="ga-progress-stat">
                        <span class="ga-stat-label">Generation:</span>
                        <span class="ga-stat-value" id="ga-generation">0</span>
                    </div>
                    <div class="ga-progress-stat">
                        <span class="ga-stat-label">Best Score:</span>
                        <span class="ga-stat-value" id="ga-score">—</span>
                    </div>
                    <div class="ga-progress-stat">
                        <span class="ga-stat-label">Feasible:</span>
                        <span class="ga-stat-value" id="ga-feasible">—</span>
                    </div>
                    <div class="ga-progress-stat">
                        <span class="ga-stat-label">Violations:</span>
                        <span class="ga-stat-value" id="ga-violations">—</span>
                    </div>
                    <div class="ga-progress-bar">
                        <div class="ga-progress-fill" id="ga-progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="ga-progress-message" id="ga-progress-message">Initializing...</div>
                </div>
            </div>
        `;

        container.style.display = 'block';

        // Start tracking
        this.tracker.start(
            sessionId,
            (progress) => this.updateProgress(progress),
            (result) => this.onComplete(result),
            (error) => this.onError(error)
        );
    }

    /**
     * Update progress UI with new data
     */
    updateProgress(progress) {
        document.getElementById('ga-generation').textContent = progress.generation || 0;
        document.getElementById('ga-score').textContent =
            progress.best_score !== undefined ? progress.best_score.toFixed(2) : '—';
        document.getElementById('ga-feasible').textContent = progress.is_feasible ? '✓ Yes' : '✗ No';

        const hardViolations = progress.hard_penalty || 0;
        const softViolations = progress.soft_penalty || 0;
        document.getElementById('ga-violations').textContent =
            `${hardViolations.toFixed(0)} hard, ${softViolations.toFixed(0)} soft`;

        // Update progress bar (estimate based on generation count)
        const maxGenerations = 1000; // Default max
        const progressPercent = Math.min((progress.generation / maxGenerations) * 100, 95);
        document.getElementById('ga-progress-fill').style.width = `${progressPercent}%`;

        // Update message
        const elapsed = progress.elapsed_seconds || 0;
        const msg = `Generation ${progress.generation} • ${elapsed.toFixed(1)}s elapsed`;
        document.getElementById('ga-progress-message').textContent = msg;

        // Add spinning animation to icon
        const icon = document.querySelector('.ga-progress-icon svg');
        if (icon && !icon.classList.contains('spinning')) {
            icon.classList.add('spinning');
        }
    }

    /**
     * Handle completion
     */
    onComplete(result) {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Update to success state
        container.innerHTML = `
            <div class="ga-progress-card ga-success">
                <div class="ga-progress-header">
                    <div class="ga-progress-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                    </div>
                    <div class="ga-progress-title">Generation Complete!</div>
                    <button class="ga-progress-close" onclick="window.gaProgressUI.hide()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="ga-progress-body">
                    <div class="ga-result-summary">
                        ${result.message || 'Schedule generated successfully'}
                    </div>
                    ${result.schedules ? `
                        <div class="ga-result-stats">
                            <span>${result.schedules.length} schedule blocks created</span>
                        </div>
                    ` : ''}
                    <button class="btn-primary" onclick="window.gaProgressUI.applyResults(); window.gaProgressUI.hide();" style="width: 100%; margin-top: 12px;">
                        Apply to Schedule
                    </button>
                </div>
            </div>
        `;

        this.lastResult = result;

        // Auto-hide after 10 seconds
        setTimeout(() => this.hide(), 10000);
    }

    /**
     * Handle error
     */
    onError(error) {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Check if this is a "not implemented" error
        const isNotImplemented = error && (
            error.includes('not yet implemented') ||
            error.includes('under development') ||
            error.includes('Not Implemented')
        );

        const title = isNotImplemented ? 'Feature In Development' : 'Generation Failed';
        const iconColor = isNotImplemented ? '#f59e0b' : '#dc2626';
        const messageClass = isNotImplemented ? 'ga-info-message' : 'ga-error-message';

        container.innerHTML = `
            <div class="ga-progress-card ga-error">
                <div class="ga-progress-header">
                    <div class="ga-progress-icon" style="color: ${iconColor}">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <div class="ga-progress-title">${title}</div>
                    <button class="ga-progress-close" onclick="window.gaProgressUI.hide()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="ga-progress-body">
                    <div class="${messageClass}">${error}</div>
                    ${isNotImplemented ? '<div class="ga-info-note" style="margin-top: 10px; font-size: 0.75rem; color: #6b7280;">The async generation feature with real-time progress tracking is coming soon. For now, schedules can be managed manually using the timetable interface.</div>' : ''}
                </div>
            </div>
        `;

        // Auto-hide after 8 seconds for not-implemented, 5 seconds for errors
        setTimeout(() => this.hide(), isNotImplemented ? 8000 : 5000);
    }

    /**
     * Cancel generation
     */
    async cancel() {
        const result = await this.tracker.cancel();
        if (result) {
            this.hide();
        }
    }

    /**
     * Hide progress UI
     */
    hide() {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.style.display = 'none';
            container.innerHTML = '';
        }
        this.tracker.stop();
    }

    /**
     * Apply results to schedule (to be implemented by app)
     */
    applyResults() {
        if (this.lastResult && this.lastResult.schedules) {
            // Trigger schedule refresh
            if (window.refreshScheduleFromServer) {
                window.refreshScheduleFromServer();
            }
            console.log('Applied GA results:', this.lastResult.schedules.length, 'schedules');
        }
    }
}

// Initialize global instance
window.gaProgressUI = new GAProgressUI();
