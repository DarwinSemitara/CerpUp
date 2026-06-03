# Faculty Bulk Delete & Professor Dropdown Fix

## Summary
Added checkbox selection and bulk delete functionality for faculty members, plus added debugging to help troubleshoot professor dropdown issues in the schedule.

## Changes Made

### 1. Faculty Section - Bulk Delete UI

**Added Delete Button** (`templates/partials/schedule.html`):
- Small trash bin icon button next to "Add Faculty"
- Hidden by default, shows only when faculty members are selected
- Red danger styling

**Added Checkboxes to Faculty Cards**:
- Checkbox in top-right corner of each faculty card
- Cards highlight with border when selected
- Click anywhere on card to toggle selection

### 2. Bulk Delete Modal

**New Confirmation Modal**:
```html
<div class="modal" id="bulk-delete-modal">
    - Shows count of selected faculty members
    - Warning: "This action cannot be undone"
    - Cancel / Delete buttons
</div>
```

### 3. JavaScript Functions (dashboard.js)

**New Functions Added**:

```javascript
// Track selected faculty
let selectedStaffIds = new Set();

// Toggle individual checkbox
function toggleStaffCheckbox(event, staffId)

// Toggle card selection on click
function toggleStaffSelection(event, staffId)

// Show/hide delete button based on selection
function updateBulkDeleteButton()

// Open confirmation modal
function confirmBulkDeleteStaff()

// Close confirmation modal
function closeBulkDeleteModal()

// Execute bulk deletion
async function executeBulkDelete()
```

### 4. Updated Styles

**CSS Added**:
```css
.staff-card.selected {
    border-color: #6b0f1a;
    box-shadow: 0 0 0 2px rgba(107, 15, 26, 0.1);
}

.staff-card-checkbox {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 20px;
    height: 20px;
    cursor: pointer;
    z-index: 10;
    accent-color: #6b0f1a;
}
```

### 5. Professor Dropdown Debugging

**Added Console Logs** to schedule JavaScript:
- Logs when staff data is loaded
- Shows count of faculty members
- Displays sample staff object
- Logs selected subject code
- Shows eligible professors count for each subject

## User Workflow

### Bulk Delete Faculty:

1. **Select Faculty Members**:
   - Click checkbox or anywhere on faculty card
   - Card highlights with red border
   - Delete button (trash icon) appears

2. **Click Delete Button**:
   - Confirmation modal opens
   - Shows count: "Delete X faculty member(s)?"
   - Warning about permanent deletion

3. **Confirm Deletion**:
   - Click "Delete" to proceed
   - All selected faculty removed
   - Success message shows
   - Checkboxes reset

4. **Cancel**:
   - Click "Cancel" or X to close
   - Selections remain
   - No deletion occurs

### Professor Dropdown Debugging:

**Open Browser Console** (F12) when adding a subject to see:

```
Staff data loaded: 3 faculty members
Sample staff: {id: "abc123", fullName: "Dr. Juan Cruz", subjects: [...], ...}
Selected subject code: HUME 100
Total staff: 3
Eligible staff for HUME 100: 1
```

**What to Check**:

1. **If "Total staff: 0"**:
   - No faculty added yet
   - Add faculty members first

2. **If "Eligible staff for [code]: 0"**:
   - No faculty assigned to teach that subject
   - Go to Faculty section
   - Click "Add Faculty"
   - Select the subject when assigning

3. **Check staff object structure**:
   ```json
   {
     "id": "staff-uuid",
     "fullName": "Dr. Juan Cruz",
     "subjects": [
       {"code": "HUME 100", "name": "Intro to Human Ecology", "year": "1"}
     ],
     "availability": ["Monday", "Tuesday"],
     "photo_url": "..."
   }
   ```

## Common Issues & Solutions

### Issue: "No professors available for this subject"

**Cause**: Faculty member hasn't been assigned to teach that subject

**Solution**:
1. Go to Faculty section (below schedule)
2. Check if faculty member exists
3. If yes, they need to be assigned that subject:
   - Currently, you'd need to delete and re-add them with the correct subject
   - OR implement edit faculty functionality

### Issue: Delete button doesn't appear

**Cause**: No faculty selected

**Solution**: Click on a faculty card to select it

### Issue: Can't unselect faculty

**Solution**: Click the card or checkbox again to toggle off

## Technical Details

### Staff Data Structure

**In Database** (`staff` collection):
```json
{
  "id": "staff-uuid",
  "memberId": "member-uuid",
  "fullName": "Dr. Maria Santos, PhD",
  "subjects": [
    {"code": "HUME 100", "name": "Introduction to Human Ecology", "year": "1"},
    {"code": "HUME 107", "name": "Principles of Human Development", "year": "1"}
  ],
  "availability": ["Monday", "Tuesday", "Wednesday"],
  "photo_url": "https://...",
  "created_at": "2025-01-01T00:00:00"
}
```

### Professor Filtering Logic

**Schedule JavaScript**:
```javascript
var eligibleStaff = staffData.filter(function (staff) {
    return staff.subjects && staff.subjects.some(function (s) {
        return s.code === selectedCode;
    });
});
```

**How it works**:
1. User selects a subject (e.g., "HUME 100")
2. System filters all staff
3. Checks if staff has `subjects` array
4. Checks if any subject's `code` matches selected code
5. Populates dropdown with matching faculty

### API Endpoint Used

**GET `/api/staff`**:
- Returns all faculty members
- Includes subjects, availability, photo
- Used by both Faculty section AND schedule

## Testing Checklist

- [x] Checkbox appears on each faculty card
- [x] Click card to toggle selection
- [x] Delete button shows when faculty selected
- [x] Delete button hides when none selected
- [x] Confirmation modal opens with correct count
- [x] Bulk deletion removes all selected faculty
- [x] Success message shows after deletion
- [ ] Console logs show staff data loading
- [ ] Console logs show subject filtering
- [ ] Professor dropdown populates with eligible faculty
- [ ] "No professors available" shows when none eligible

## Next Steps to Fix Professor Dropdown

1. **Open browser console** (F12)
2. **Go to Schedule page**
3. **Check console for**:
   - "Staff data loaded: X faculty members"
4. **Try adding a subject**:
   - Select a subject code
   - Check console logs
   - See if eligible staff is 0 or > 0
5. **If eligible staff is 0**:
   - Faculty needs to be assigned that subject
   - Either delete & re-add with correct subjects
   - OR we can implement edit faculty functionality

**Most likely issue**: The faculty member was added but wasn't assigned to teach the specific subject code you're trying to schedule.

**Solution**: When adding faculty, make sure to check the year level(s) and select the specific subjects they will teach. The subject codes must match exactly (e.g., "HUME 100", not "hume 100").
