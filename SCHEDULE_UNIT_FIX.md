# Schedule Unit Management Fix

## Changes Implemented (Commit: a83aa4d)

### 1. **Right-Click Remove for Unplaced Subjects**

**Feature:** Right-clicking an unplaced subject block in the staging area now shows a confirmation modal.

**How it works:**
- Right-click any subject block in the "Subject Block Config" staging area
- A modal appears asking "Are you sure you want to remove [SUBJECT]?"
- Clicking "Remove" deletes the configured subject from the database
- The subject becomes available again in Course Config
- The staging area refreshes automatically

**Files Modified:**
- `templates/partials/schedule.html`:
  - Added `.remove-subject-*` CSS classes for modal styling
  - Added `#remove-subject-modal` HTML structure
  - Added `contextmenu` event listener to draggable subjects in `renderDraggableBlocks()`
  - Added `showRemoveSubjectModal()`, `closeRemoveSubjectModal()`, and `confirmRemoveSubject()` functions

- `app.py`:
  - Added `/api/configured-subjects/remove` POST endpoint
  - Deletes by `faculty_id`, `subject_code`, `school_year`, and `semester`

### 2. **Dynamic Unit Input Maximum**

**Feature:** Unit input fields in Course Config now respect remaining capacity across all faculty.

**How it works:**
- When a subject has already been partially allocated (e.g., Faculty A has 1.5 units of CERP 122)
- Faculty B's Course Config shows CERP 122 with a max of 1.5 units (3 - 1.5 = 1.5 remaining)
- The input field's `max` attribute is dynamically set: `Math.min(3, 3 - globalAllocated)`
- Admins cannot exceed the 3-unit total limit per subject

**Files Modified:**
- `templates/partials/schedule.html`:
  - Updated `populateCourseCheckboxes()` function
  - Added dynamic `max` calculation: `var remaining = 3 - globalAllocated`
  - Set `unitInput.max = Math.min(3, remaining).toString()`
  - Added tooltip showing remaining units
  - Enhanced `unitInput.onchange` to enforce the dynamic max

### 3. **Session Debugging for Tab-Switch Logout (Previous Commit: e4722b5)**

**Note:** This was part of debugging the logout issue, not the schedule features.

**Files Modified:**
- `app.py`:
  - Added extensive logging to `@app.before_request`, `login_required`, login endpoint
  - Fixed admin login to return proper user data in `/api/current-member`
  - Added hardcoded admin user handling to prevent 404 errors

## Testing Checklist

### Right-Click Remove
- [ ] Right-click a subject block in staging area
- [ ] Confirm modal appears with subject name
- [ ] Click "Cancel" - modal closes, subject remains
- [ ] Right-click again, click "Remove" - subject disappears
- [ ] Open Course Config - removed subject is now available (not greyed out)
- [ ] Configure the same subject again - it appears in staging

### Dynamic Unit Maximum
- [ ] Configure CERP 122 with 1.5 units for Faculty A
- [ ] Save configuration (subject appears in staging)
- [ ] Switch to Faculty B
- [ ] Open Course Config, find CERP 122
- [ ] Check unit input shows max 1.5 (not 3)
- [ ] Try entering 2.5 - should auto-correct to 1.5
- [ ] Try entering 1.0 - should be accepted
- [ ] Tooltip should show "max 1.5 units remaining"

### Integration Test
- [ ] Faculty A: Configure CERP 122 with 1.5 units
- [ ] Faculty B: Configure CERP 122 with 1.5 units (total = 3)
- [ ] Faculty C: CERP 122 should be greyed out in Course Config
- [ ] Faculty A: Right-click CERP 122 in staging, remove it
- [ ] Faculty C: CERP 122 should now be available with max 1.5 units

## Known Behavior

1. **Partially Allocated Subjects Show Solid Border**
   - Subjects with 0 allocation: dashed border (incomplete class)
   - Subjects with partial allocation: solid border (normal appearance)

2. **Unit Input Validation**
   - Minimum: 0.5 units
   - Maximum: 3 units (or remaining capacity if less)
   - Intervals: 0.5 (enforced by rounding)

3. **Global Allocation Calculation**
   - Counts units from placed schedules (on timetable)
   - Counts units from configured subjects (staging area)
   - Updates dynamically when subjects are added/removed

## API Endpoints

### New Endpoint
```
POST /api/configured-subjects/remove
Body: {
  "faculty_id": "string",
  "subject_code": "string",
  "school_year": "string",
  "semester": "string"
}
Response: { "status": "ok" }
```

### Existing Endpoints (Used)
- `GET /api/configured-subjects?school_year=...&semester=...` - Load all configured subjects
- `POST /api/configured-subjects` - Save configured subject
- `DELETE /api/configured-subjects/<entry_id>` - Delete by ID (not used by new feature)

## Future Enhancements

1. **Undo Remove**: Add ability to undo subject removal within same session
2. **Bulk Remove**: Select multiple subjects and remove at once
3. **Allocation History**: Show who configured what and when
4. **Conflict Prevention**: Warn when removing a subject that's already placed on timetable
