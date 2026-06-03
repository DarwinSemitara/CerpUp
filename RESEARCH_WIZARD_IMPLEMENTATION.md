# Research Wizard Implementation - User Dashboard

## Overview
Implemented a multi-step research submission wizard for the user dashboard with the following features:

## Changes Made

### 1. **Table Structure Updated**
- **Removed**: "Actions" column
- **Added**: "Book" column (after Title column)
- **Changed**: "FundCode" → "Func-Code"
- **Column Order**: Category, Sub-category, Title, **Book**, Funding Agency, Func-Code, Nature, Project ID, SDG's, Role, Coworkers, Start Date, End Date

### 2. **Multi-Step Wizard Implementation**

#### Step 1: Basic Information
- Category (dropdown: Applied Research, Basic Research, Policy Research)
- Sub-category (text input)
- Research Title (textarea)

#### Step 2: Document Upload
- **File Upload**: Drag-and-drop or click to browse
  - Accepts: PDF, DOCX
  - Max size: 50MB
  - Shows file preview with name, size, and remove option
- **OR**
- **DOI/Link Input**: URL field for DOI or research link

#### Step 3: Funding Details
- Funding Agency (text input)
- Func-Code (text input) - Note: Changed from "FundCode"

#### Step 4: Project Details
- Nature of Project (dropdown: Funded, Unfunded)
- Project ID (text input)
- SDG's (text input with comma separation)

#### Step 5: Team & Timeline
- Your Role (dropdown: Lead Researcher, Co-Researcher, Research Assistant)
- Coworkers Involved (textarea with comma separation)
- Start Date (date picker)
- End Date (date picker)

### 3. **Wizard Features**

#### Progress Indicator
- 5-step visual progress bar at the top
- Shows current step, completed steps, and upcoming steps
- Color-coded:
  - Active step: Primary color (green)
  - Completed steps: Success color (green checkmark)
  - Upcoming steps: Gray

#### Navigation
- **Back Button**: Navigate to previous step (disabled on first step)
- **Continue Button**: Validate and move to next step (hidden on last step)
- **Submit Button**: Final submission (only visible on last step)

#### Validation
- Each step validates required fields before allowing progression
- Alert messages for missing required fields
- File size validation (50MB max)

#### File Upload
- Drag-and-drop support
- Visual feedback on drag over
- File preview with:
  - File icon
  - File name
  - File size in MB
  - Remove button

### 4. **Styling Enhancements**
- Modern, clean wizard interface
- Smooth animations between steps (fadeIn effect)
- Responsive form elements
- Consistent color scheme matching sidebar
- Hover effects on interactive elements
- Professional file upload area

### 5. **Functions Added**

```javascript
// Wizard Management
- initResearchWizard()
- openResearchWizard()
- closeResearchWizard()
- wizardNextStep()
- wizardPrevStep()
- validateWizardStep(step)
- submitResearchWizard()

// File Handling
- handleFileSelect(event)
- removeFile()
```

### 6. **State Management**
```javascript
let currentWizardStep = 1;
const totalWizardSteps = 5;
let uploadedFile = null;
```

## User Experience Flow

1. **Click "Add Research"** → Opens wizard modal
2. **Step 1**: Enter category, sub-category, and title → Click "Continue"
3. **Step 2**: Upload file OR enter DOI link (optional) → Click "Continue"
4. **Step 3**: Enter funding agency and func-code → Click "Continue"
5. **Step 4**: Select nature, enter project ID and SDGs → Click "Continue"
6. **Step 5**: Select role, list coworkers, set dates → Click "Submit Research"
7. **Success**: Modal closes, table refreshes, success message shown

## Technical Notes

### Form Data Collection
- Uses FormData API for file upload support
- Collects all fields including optional file
- Ready for API integration

### Validation Rules
- **Step 1**: Category, Sub-category, Title (required)
- **Step 2**: File or DOI (optional)
- **Step 3**: Funding Agency, Func-Code (required)
- **Step 4**: Nature, Project ID, SDGs (required)
- **Step 5**: Role, Coworkers, Start Date, End Date (required)

### File Upload Specifications
- **Accepted formats**: .pdf, .doc, .docx
- **Maximum size**: 50MB
- **Validation**: Client-side size check
- **Preview**: Shows file name and size
- **Removal**: Can remove and re-upload

## Next Steps for Backend Integration

### API Endpoint Needed
```
POST /api/research/submit
Content-Type: multipart/form-data

Fields:
- category
- subcategory
- title
- doi (optional)
- file (optional)
- agency
- funccode
- nature
- projectid
- sdg
- role
- coworkers
- startdate
- enddate
```

### Database Schema Suggestion
```sql
CREATE TABLE research_submissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    title TEXT,
    file_url VARCHAR(500),
    doi VARCHAR(500),
    funding_agency VARCHAR(200),
    func_code VARCHAR(100),
    nature VARCHAR(50),
    project_id VARCHAR(100),
    sdgs TEXT,
    role VARCHAR(100),
    coworkers TEXT,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id)
);
```

### File Storage
- Store uploaded files in cloud storage (Cloudinary already configured)
- Save file URL in database
- Display "View" button in Book column linking to file/DOI

## Benefits of This Implementation

1. **Better UX**: Step-by-step reduces cognitive load
2. **Validation**: Catches errors early, step-by-step
3. **Flexibility**: Supports both file upload and DOI links
4. **Professional**: Modern wizard interface
5. **Scalable**: Easy to add/modify steps
6. **Accessible**: Clear labels, hints, and error messages

## Testing Checklist

- [ ] Open wizard modal
- [ ] Navigate through all 5 steps
- [ ] Test back button functionality
- [ ] Validate required field checks
- [ ] Test file upload (drag-and-drop)
- [ ] Test file upload (click to browse)
- [ ] Test file size validation (>50MB)
- [ ] Test file removal
- [ ] Test DOI input
- [ ] Test form submission
- [ ] Verify table updates after submission
- [ ] Test wizard reset on reopen

## Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- File API support for drag-and-drop
- FormData API for file upload

## Accessibility Features
- Semantic HTML structure
- Clear labels with required indicators
- Keyboard navigation support
- Focus states on interactive elements
- Error messages for validation
- Progress indicator for screen readers

---

**Status**: ✅ Frontend Implementation Complete
**Next**: Backend API integration needed
**Date**: 2026-05-31
