// Research Wizard Implementation
// Multi-step wizard for research submission

// Wizard State
let currentWizardStep = 1;
const totalWizardSteps = 5;
let uploadedFile = null;

// Initialize wizard when modal opens
function initResearchWizard() {
    currentWizardStep = 1;
    uploadedFile = null;

    // Setup drag and drop
    const uploadArea = document.getElementById('file-upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect({ target: { files } });
            }
        });
    }
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        alert('File size exceeds 50MB limit');
        return;
    }

    uploadedFile = file;

    // Show file preview
    const previewContainer = document.getElementById('file-preview-container');
    const fileSize = (file.size / 1024 / 1024).toFixed(2);

    previewContainer.innerHTML = `
        <div class="file-preview">
            <div class="file-preview-icon">
                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            </div>
            <div class="file-preview-info">
                <div class="file-preview-name">${file.name}</div>
                <div class="file-preview-size">${fileSize} MB</div>
            </div>
            <button type="button" class="file-preview-remove" onclick="removeFile()">Remove</button>
        </div>
    `;
}

// Remove uploaded file
function removeFile() {
    uploadedFile = null;
    document.getElementById('res-file-input').value = '';
    document.getElementById('file-preview-container').innerHTML = '';
}

// Navigate to next step
function wizardNextStep() {
    // Validate current step
    if (!validateWizardStep(currentWizardStep)) {
        return;
    }

    if (currentWizardStep < totalWizardSteps) {
        // Mark current as completed
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.add('completed');
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.remove('active');
        document.querySelector(`.wizard-step-content[data-step="${currentWizardStep}"]`).classList.remove('active');

        // Move to next
        currentWizardStep++;
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.add('active');
        document.querySelector(`.wizard-step-content[data-step="${currentWizardStep}"]`).classList.add('active');

        // Update buttons
        document.getElementById('wizard-back-btn').disabled = false;

        if (currentWizardStep === totalWizardSteps) {
            document.getElementById('wizard-next-btn').style.display = 'none';
            document.getElementById('wizard-submit-btn').style.display = 'block';
        }
    }
}

// Navigate to previous step
function wizardPrevStep() {
    if (currentWizardStep > 1) {
        // Remove active from current
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.remove('active');
        document.querySelector(`.wizard-step-content[data-step="${currentWizardStep}"]`).classList.remove('active');

        // Move to previous
        currentWizardStep--;
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.remove('completed');
        document.querySelector(`.wizard-step[data-step="${currentWizardStep}"]`).classList.add('active');
        document.querySelector(`.wizard-step-content[data-step="${currentWizardStep}"]`).classList.add('active');

        // Update buttons
        if (currentWizardStep === 1) {
            document.getElementById('wizard-back-btn').disabled = true;
        }

        document.getElementById('wizard-next-btn').style.display = 'block';
        document.getElementById('wizard-submit-btn').style.display = 'none';
    }
}

// Validate current wizard step
function validateWizardStep(step) {
    switch (step) {
        case 1:
            const category = document.getElementById('res-category').value;
            const subcategory = document.getElementById('res-subcategory').value;
            const title = document.getElementById('res-title').value;
            if (!category || !subcategory || !title) {
                alert('Please fill in all required fields');
                return false;
            }
            break;
        case 2:
            // Optional step - file or DOI
            break;
        case 3:
            const agency = document.getElementById('res-agency').value;
            const funccode = document.getElementById('res-funccode').value;
            if (!agency || !funccode) {
                alert('Please fill in all required fields');
                return false;
            }
            break;
        case 4:
            const nature = document.getElementById('res-nature').value;
            const projectid = document.getElementById('res-projectid').value;
            const sdg = document.getElementById('res-sdg').value;
            if (!nature || !projectid || !sdg) {
                alert('Please fill in all required fields');
                return false;
            }
            break;
        case 5:
            const role = document.getElementById('res-role').value;
            const coworkers = document.getElementById('res-coworkers').value;
            const startdate = document.getElementById('res-startdate').value;
            const enddate = document.getElementById('res-enddate').value;
            if (!role || !coworkers || !startdate || !enddate) {
                alert('Please fill in all required fields');
                return false;
            }
            break;
    }
    return true;
}

// Open wizard modal
function openResearchWizard() {
    const modal = document.getElementById('research-modal');
    modal.classList.add('open');

    // Reset wizard
    currentWizardStep = 1;
    uploadedFile = null;

    // Reset all steps
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active', 'completed');
    });
    document.querySelectorAll('.wizard-step-content').forEach(content => {
        content.classList.remove('active');
    });

    // Activate first step
    document.querySelector('.wizard-step[data-step="1"]').classList.add('active');
    document.querySelector('.wizard-step-content[data-step="1"]').classList.add('active');

    // Reset buttons
    document.getElementById('wizard-back-btn').disabled = true;
    document.getElementById('wizard-next-btn').style.display = 'block';
    document.getElementById('wizard-submit-btn').style.display = 'none';

    // Clear form
    document.getElementById('res-category').value = '';
    document.getElementById('res-subcategory').value = '';
    document.getElementById('res-title').value = '';
    if (document.getElementById('res-doi')) document.getElementById('res-doi').value = '';
    document.getElementById('res-agency').value = '';
    if (document.getElementById('res-funccode')) document.getElementById('res-funccode').value = '';
    document.getElementById('res-nature').value = '';
    document.getElementById('res-projectid').value = '';
    document.getElementById('res-sdg').value = '';
    document.getElementById('res-role').value = '';
    document.getElementById('res-coworkers').value = '';
    document.getElementById('res-startdate').value = '';
    document.getElementById('res-enddate').value = '';
    if (document.getElementById('file-preview-container')) document.getElementById('file-preview-container').innerHTML = '';

    // Initialize drag and drop
    initResearchWizard();
}

// Close wizard modal
function closeResearchWizard() {
    const modal = document.getElementById('research-modal');
    modal.classList.remove('open');
}

// Submit research wizard
async function submitResearchWizard() {
    if (!validateWizardStep(5)) {
        return;
    }

    const formData = new FormData();
    formData.append('category', document.getElementById('res-category').value);
    formData.append('subcategory', document.getElementById('res-subcategory').value);
    formData.append('title', document.getElementById('res-title').value);
    if (document.getElementById('res-doi')) {
        formData.append('doi', document.getElementById('res-doi').value);
    }
    formData.append('agency', document.getElementById('res-agency').value);
    formData.append('funccode', document.getElementById('res-funccode') ? document.getElementById('res-funccode').value : document.getElementById('res-fundcode').value);
    formData.append('nature', document.getElementById('res-nature').value);
    formData.append('projectid', document.getElementById('res-projectid').value);
    formData.append('sdg', document.getElementById('res-sdg').value);
    formData.append('role', document.getElementById('res-role').value);
    formData.append('coworkers', document.getElementById('res-coworkers').value);
    formData.append('startdate', document.getElementById('res-startdate').value);
    formData.append('enddate', document.getElementById('res-enddate').value);

    if (uploadedFile) {
        formData.append('file', uploadedFile);
    }

    try {
        // TODO: Send to API
        console.log('Submitting research:', Object.fromEntries(formData));

        // Close modal and reload data
        closeResearchWizard();
        if (typeof loadResearchData === 'function') {
            loadResearchData();
        }

        // Show success message
        alert('Research submitted successfully!');
    } catch (error) {
        console.error('Error submitting research:', error);
        alert('Failed to submit research. Please try again.');
    }
}
