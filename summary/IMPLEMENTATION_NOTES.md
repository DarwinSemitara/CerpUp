# Class Schedule - Add Subject Feature Implementation

## Overview
Added an "Add Subject" section below the class schedule timetable that allows users to create unscheduled subject blocks and drag them into the timetable.

## Features Implemented

### 1. Add Subject Card
- **Location**: Below the timetable, above the Faculty Load Report
- **Components**:
  - Header with "Add Subject" title and "New Subject" button
  - Collapsible form (hidden by default)
  - Staging area for unscheduled subjects

### 2. Add Subject Form
- **Fields**:
  - Subject Code (e.g., ENRP 101)
  - Subject Name (e.g., Environmental Planning)
  - Professor (e.g., Dr. A. Santos)
  - Classroom (e.g., Room 201)
  - Units (number, 1-6)
  - Section (e.g., BSEP 2-A)
- **Actions**:
  - Cancel button (closes form)
  - "Add to Staging" button (creates unscheduled subject block)

### 3. Staging Area
- **Purpose**: Holds unscheduled subjects before they're placed in the timetable
- **Features**:
  - Displays subject blocks with color-coded backgrounds
  - Shows subject code, name, and professor
  - Delete button (X) on hover
  - Empty state message when no subjects

### 4. Drag-and-Drop Functionality
- **From Staging to Timetable**:
  - Click and drag any staging block
  - Visual ghost element follows cursor
  - Drop on any empty timetable cell
  - Default duration: 1.5 hours (3 time slots)
  - Automatically creates schedule entry via API
  - Removes subject from staging area after successful placement

### 5. Post-Drop Adjustments
- **After placing a subject**:
  - Drag the block to move it to a different day/time
  - Pull the bottom edge to resize (lengthen/shorten)
  - Click the X button to delete
  - All existing manual mode features work on dropped blocks

## Technical Details

### CSS Classes Added
- `.add-subject-card` - Main container
- `.add-subject-header` - Header with title and button
- `.add-subject-form` - Collapsible form container
- `.asf-grid` - 3-column grid layout for form fields
- `.asf-group` - Individual form field wrapper
- `.asf-actions` - Form action buttons container
- `.staging-area` - Staging area container
- `.staging-label` - Label for staging area
- `.staging-blocks` - Container for unscheduled subject blocks
- `.staging-block` - Individual unscheduled subject block
- `.stg-code`, `.stg-name`, `.stg-prof` - Subject block text elements
- `.stg-del` - Delete button for staging blocks

### JavaScript Functions Added
- `toggleAddSubjectForm()` - Shows/hides the add subject form
- `addUnscheduledSubject()` - Creates a new unscheduled subject block
- `renderStagingArea()` - Renders all unscheduled subjects in the staging area
- `removeUnscheduledSubject(id, e)` - Removes a subject from staging
- `attachStagingDragHandlers()` - Attaches drag event handlers to staging blocks
- `stagingMouseUpHandler(e)` - Handles drop events from staging blocks

### Data Structure
```javascript
unscheduledSubjects = [
  {
    id: 'unsched-{timestamp}-{random}',
    subjCode: 'ENRP 101',
    subjName: 'Environmental Planning',
    prof: 'Dr. A. Santos',
    room: 'Room 201',
    units: 3,
    section: 'BSEP 2-A'
  }
]
```

### API Integration
- Uses existing `/api/schedules` POST endpoint to create schedule entries
- Automatically removes subject from staging after successful API call
- Refreshes timetable, filters, and report after placement

## User Workflow

1. **Add a Subject**:
   - Click "New Subject" button
   - Fill in all required fields
   - Click "Add to Staging"
   - Subject block appears in staging area

2. **Place Subject in Timetable**:
   - Click and drag subject block from staging area
   - Hover over desired day/time slot
   - Release mouse to drop
   - Block is created with 1.5-hour default duration

3. **Adjust Placement**:
   - Drag block to move to different day/time
   - Pull bottom edge to resize duration
   - Click X to delete if needed

4. **Remove from Staging**:
   - Hover over staging block
   - Click X button to remove without placing

## Notes
- Only works in Manual mode (not AI Scheduler mode)
- Staging blocks persist until placed or manually removed
- Color-coding matches existing schedule block colors
- All form fields are required
- Default duration can be adjusted after placement
