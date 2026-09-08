# Schedule Management Improvements

## Overview
Enhanced schedule management system with unit allocation controls, visual feedback, and unsaved changes protection.

## Changes Implemented

### 1. Unit Input Validation (Max 3 Units, 0.5 Intervals)

**Location**: `templates/partials/schedule.html` - Course Configuration Section

**Changes**:
- Modified unit input fields in course configuration to enforce:
  - **Minimum**: 0.5 units
  - **Maximum**: 3 units
  - **Step**: 0.5 intervals (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
- Automatic validation and rounding on input change
- Dynamic max value adjustment based on remaining capacity

**Code**:
```javascript
unitInput.min = '0.5';
unitInput.max = '3';
unitInput.step = '0.5';
unitInput.onchange = function () {
    var val = parseFloat(this.value);
    var maxAllowed = parseFloat(this.max);
    
    if (isNaN(val) || val < 0.5) {
        this.value = 0.5;
    } else if (val > maxAllowed) {
        this.value = maxAllowed;
    } else {
        // Round to nearest 0.5
        this.value = (Math.round(val * 2) / 2).toFixed(1);
    }
};
```

### 2. Global Allocation Tracking & Subject Greying

**Location**: `templates/partials/schedule.html` - `calculateGlobalAllocation()` and `populateCourseCheckboxes()`

**Features**:
- **Global Allocation Tracking**: Calculates total units allocated for each subject across ALL faculty members in current semester/year
- **Visual Feedback**: Subjects that reach 3 units total are:
  - Greyed out (opacity 0.4)
  - Checkbox disabled
  - Label shows allocation status
  - Unit input disabled with grey background
- **Dynamic Labels**:
  - Fully allocated: "CERP 101 - Subject Name (Fully Allocated: 3.0/3 units)"
  - Partially allocated: "CERP 101 - Subject Name (1.5/3 units assigned)"
  - Not allocated: "CERP 101 - Subject Name"

**Code**:
```javascript
function calculateGlobalAllocation(subjCode) {
    var totalAllocated = 0;
    
    schedules.forEach(function (sch) {
        var matchesSemester = ((sch.school_year || sch.schoolYear) === currentSchoolYear) 
                              && sch.semester === currentSemester;
        
        if (matchesSemester && sch.subjCode === subjCode) {
            var startIdx = slotIdx(sch.start);
            var endIdx = slotIdx(sch.end);
            if (startIdx >= 0 && endIdx > startIdx) {
                var duration = (endIdx - startIdx) / 2;
                totalAllocated += duration;
            }
        }
    });
    
    return totalAllocated;
}
```

**Example**:
- If Faculty A teaches HUME 100 for 1.5 units
- And Faculty B teaches HUME 100 for 1.5 units
- Total = 3.0 units → HUME 100 becomes disabled and greyed out for all other faculty

### 3. Unsaved Changes Tracking System

**Location**: `templates/partials/schedule.html` - Multiple sections

**Components**:

#### A. State Variables
```javascript
var unsavedScheduleIds = []; // Track schedule IDs not confirmed with "Save Schedule"
var hasUnsavedChanges = false; // Flag for unsaved changes
```

#### B. Change Tracking
Integrated into:
- **Adding schedules** (`confirmNewBlock`): New schedules added to `unsavedScheduleIds`
- **Moving schedules** (drag-drop): Modified schedules tracked as unsaved
- **Deleting schedules**: Removes from unsaved list, updates flag

#### C. Save Confirmation
- When "Save Schedule" button is clicked (`toggleScheduleLock`), the system:
  - Clears `unsavedScheduleIds` array
  - Sets `hasUnsavedChanges = false`
  - Locks the schedule for viewing (Edit mode)

### 4. Navigation Protection

**Location**: `templates/partials/schedule.html` - Event Handlers

**Features**:

#### A. Browser Navigation Warning
```javascript
window.addEventListener('beforeunload', function (e) {
    if (hasUnsavedChanges && unsavedScheduleIds.length > 0) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes to the schedule. If you leave, these changes will be lost.';
        return e.returnValue;
    }
});
```

**Triggers on**:
- Closing tab/window
- Refreshing page (F5)
- Navigating back/forward
- Typing new URL

#### B. Internal Navigation Interception
```javascript
document.addEventListener('click', async function (e) {
    var target = e.target.closest('a[href]');
    if (target && hasUnsavedChanges && unsavedScheduleIds.length > 0) {
        var href = target.getAttribute('href');
        if (href && !href.startsWith('#') && !href.startsWith('http')) {
            e.preventDefault();
            
            if (confirm('You have unsaved changes to the schedule. If you leave, these changes will be lost.\n\nDo you want to leave without saving?')) {
                await cleanupUnsavedSchedules();
                window.location.href = href;
            }
        }
    }
});
```

**Triggers on**:
- Clicking sidebar navigation links
- Clicking internal page links
- Any internal navigation attempt

#### C. Automatic Cleanup
```javascript
window.addEventListener('unload', function () {
    if (hasUnsavedChanges && unsavedScheduleIds.length > 0) {
        // Synchronous cleanup during page unload
        unsavedScheduleIds.forEach(function (id) {
            try {
                var xhr = new XMLHttpRequest();
                xhr.open('DELETE', '/api/schedules/' + id, false);
                xhr.send();
            } catch (err) {
                console.error('Failed to cleanup:', err);
            }
        });
    }
});
```

**Purpose**: Removes unsaved schedule entries from database if user leaves without saving

## User Workflow

### Normal Save Workflow
1. Admin clicks "Course" button
2. Selects subjects with unit values (max 3 units per subject)
3. Clicks "Save" to create draggable blocks
4. Drags subjects to timetable → **Schedules saved to DB but marked as unsaved**
5. Clicks "Save Schedule" button → **All unsaved schedules confirmed, tracking cleared**
6. Schedule locked for viewing (Edit mode)

### Unsaved Changes Workflow
1. Admin places schedules on timetable
2. **Does NOT click "Save Schedule"**
3. Attempts to navigate away (sidebar link, close tab, etc.)
4. **Browser shows warning**: "You have unsaved changes to the schedule. If you leave, these changes will be lost."
5. User choices:
   - **Cancel/Stay**: Returns to schedule page, can click "Save Schedule"
   - **Leave**: Unsaved schedules automatically deleted from database

### Fully Allocated Subject Workflow
1. Faculty A configures CERP 101 with 1.5 units
2. Faculty B configures CERP 101 with 1.5 units
3. Total = 3.0 units
4. When Faculty C opens Course Config:
   - CERP 101 checkbox is **disabled**
   - Label shows: "CERP 101 - Course Name **(Fully Allocated: 3.0/3 units)**"
   - Greyed out (can't be selected)
5. Faculty C must choose different subjects or wait for others to reduce allocation

## Technical Details

### Database Operations
- **Add**: POST `/api/schedules` - Creates entry immediately, tracked as unsaved
- **Update**: PUT `/api/schedules/{id}` - Updates entry immediately, tracked as unsaved
- **Delete**: DELETE `/api/schedules/{id}` - Removes entry immediately, removes from unsaved list
- **Cleanup**: DELETE `/api/schedules/{id}` - Automatic cleanup on navigation without save

### Persistence Strategy
**Current behavior**: Schedules are saved to database immediately when placed (for conflict detection and validation), but are tracked as "unsaved" until admin clicks "Save Schedule" button.

**Rationale**:
- Allows real-time conflict detection across faculty
- Enables unit quota validation
- Prevents data loss from browser crashes
- Provides flexibility to discard changes by navigating away
- Maintains consistency with multi-user environment

### State Management
```javascript
// Unsaved changes cleared when:
toggleScheduleLock() // "Save Schedule" clicked
    ↓
unsavedScheduleIds = []
hasUnsavedChanges = false
scheduleLockedState = true

// Unsaved changes tracked when:
confirmNewBlock() // New schedule added
attachMoveHandlers() // Schedule moved
    ↓
unsavedScheduleIds.push(id)
hasUnsavedChanges = true
```

## Testing Checklist

- [x] Unit input validates max 3, min 0.5, step 0.5
- [x] Unit input rounds to nearest 0.5 automatically
- [x] Subject greying works when total allocation reaches 3 units
- [x] Subject checkbox disables when fully allocated
- [x] Subject label shows allocation status correctly
- [x] Placing schedule on timetable tracks as unsaved
- [x] Moving schedule on timetable tracks as unsaved
- [x] Deleting schedule removes from unsaved list
- [x] "Save Schedule" button clears unsaved changes flag
- [x] Browser navigation shows warning dialog with unsaved changes
- [x] Internal navigation (sidebar links) shows confirmation with unsaved changes
- [x] Leaving without saving deletes unsaved schedules from database
- [x] Saving clears warning and allows navigation

## Browser Compatibility

- **beforeunload**: Supported in all modern browsers (Chrome, Firefox, Edge, Safari)
- **unload**: Supported in all browsers, but synchronous XHR required for cleanup
- **XMLHttpRequest (synchronous)**: Deprecated but still supported during unload event
- **Alternative**: Using `fetch` with `keepalive: true` for single request, but not reliable for multiple deletions

## Future Improvements

1. **Visual Indicator**: Add badge/icon showing unsaved changes count
2. **Auto-save**: Optional periodic auto-save with manual override
3. **Undo/Redo**: Track change history for rollback
4. **Collaborative Editing**: Real-time updates when other admins make changes
5. **Offline Support**: Service worker for offline schedule editing
6. **Audit Trail**: Log all schedule changes with timestamps and user info

## Files Modified

- `templates/partials/schedule.html` - Main schedule management interface

## Date
December 2026 (Session: September 6, 2026 - Future-dated commit)
