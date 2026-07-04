# Schedule System Redesign - Complete Implementation Guide

## Overview
This guide documents the complete redesign of the scheduling system to match UPLB's actual course offering structure where all courses are available every semester.

## Changes Made

### ✅ 1. Top Bar Redesign (COMPLETED)
**File:** `templates/partials/schedule.html` (lines ~1100-1142)

**Changes:**
- Replaced "Year" selector → "School Year" selector (SY 2024-2025, etc.)
- Kept "Semester" selector, added "Mid Year/Inter Semester" option
- Added "Section" selector (A-Z sections)
- Removed "Generate Report" button

**JavaScript Variables Updated:**
```javascript
var currentSchoolYear = '2024-2025';
var currentSemester = '1';
var currentSection = '';
```

### ✅ 2. Filter System Updates (COMPLETED)
**File:** `templates/partials/schedule.html`

**Changes:**
- Removed "All Days" filter option
- Changed "All Classrooms" → "All Rooms"
- Updated filter function: `onYearSemesterChange()` → `onFilterChange()`
- New filter logic: filters by schoolYear + semester + section

### ✅ 3. Subject Structure (COMPLETED)
**File:** `templates/partials/schedule.html` (lines ~3611)

**Before:** Object with year-semester keys
```javascript
var ALL_SUBJECTS = {
    '1-1': [...],
    '1-2': [...]
}
```

**After:** Flat array (all subjects always available)
```javascript
var ALL_SUBJECTS = [
    { code: 'CERP 101', name: '...', units: 3 },
    { code: 'CERP 122', name: '...', units: 3 },
    ...
]
```

**Total Subjects:** 32 courses (19 CERP, 12 HUME, 1 NSTP)

### ✅ 4. Section Dropdown (COMPLETED)
**File:** `templates/partials/schedule.html` (line ~1488)

**Changed:** Text input → Dropdown select
**Options:** A, B, C, D, E, F, G, H, S, T, U, V, W, X, Y, Z

### ✅ 5. Unit Configuration UI (COMPLETED)
**File:** `templates/partials/schedule.html` (lines ~1295-1362)

**New Design:**
- Course category accordion (CERP / HUME / NSTP)
- Checkbox list for each category
- Selected count badges
- Max 3 units per section (hardcoded)

**CSS Added:**
- `.course-category` - Container styling
- `.category-toggle-btn` - Accordion button
- `.course-list` - Checkbox list container
- `.course-checkbox-item` - Individual checkbox styling

### ✅ 6. Trash Area (COMPLETED)
**File:** `templates/partials/schedule.html` (after staging area)

**Features:**
- Located between unit config and timetable
- Dashed border, trash icon
- Drag-over visual feedback (red highlight)
- Drop to delete functionality

**CSS Added:**
- `.trash-area` - Container styling
- `.trash-area.drag-over` - Active state
- Visual feedback on hover

### ✅ 7. Backend Data Structure
**Changes Needed in API:**

**Schedule Model Fields:**
```python
{
    'schoolYear': '2024-2025',  # Changed from 'year': 1
    'semester': '1',             # Same
    'section': 'A',              # New field
    'subjCode': 'CERP 101',
    'subjName': '...',
    'prof': '...',
    'day': 'Monday',
    'startTime': '7:00',
    'endTime': '8:30',
    'room': 'CERP AVR',
    'units': 3
}
```

## Installation Steps

### Step 1: Verify HTML Changes
All HTML changes have been applied to `templates/partials/schedule.html`:
- ✅ New top bar selectors
- ✅ Updated filters
- ✅ New unit configuration UI
- ✅ Trash area HTML
- ✅ Section dropdown

### Step 2: Add JavaScript Functions
Open `templates/partials/schedule.html` and find the existing `toggleUnitConfig` function (around line 1852).

**Replace the entire function with the version in `schedule_completion.js`**

**Then add these new functions after it:**
1. `toggleCourseCategory(category)`
2. `populateCourseCheckboxes(category)`
3. `updateSelectedCount(category)`
4. `initTrashArea()`
5. `deleteScheduleById(id)`

**All functions are provided in:** `schedule_completion.js`

### Step 3: Update Backend API
**File:** `app.py`

**Add/Update these routes:**

```python
# Update POST /api/schedules
@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    data = request.json
    schedule = {
        'id': str(uuid.uuid4()),
        'schoolYear': data.get('schoolYear'),  # Changed
        'semester': data.get('semester'),
        'section': data.get('section'),        # New
        'subjCode': data.get('subjCode'),
        'subjName': data.get('subjName'),
        'prof': data.get('prof'),
        'day': data.get('day'),
        'startTime': data.get('start'),
        'endTime': data.get('end'),
        'room': data.get('room'),
        'units': data.get('units', 3)
    }
    # Save to database
    db.collection('schedules').document(schedule['id']).set(schedule)
    return jsonify({'id': schedule['id'], 'entry': schedule})
```

### Step 4: Test the System

**Test Checklist:**

1. **Unit Configuration**
   - [ ] Click "Set Units" button
   - [ ] Expand CERP courses (dropdown opens)
   - [ ] Check 3-4 CERP courses
   - [ ] Check count updates "(3 selected)"
   - [ ] Expand HUME courses
   - [ ] Check 2 HUME courses  
   - [ ] Click "Save Configuration"
   - [ ] Verify draggable blocks appear

2. **Schedule Creation**
   - [ ] Drag a block to timetable
   - [ ] Fill in professor, room, section
   - [ ] Section should be dropdown (not text input)
   - [ ] Room should be dropdown (not text input)
   - [ ] Create schedule
   - [ ] Verify it appears in timetable

3. **Trash Functionality**
   - [ ] Drag existing block from timetable
   - [ ] Hover over trash area (should turn red)
   - [ ] Drop on trash area
   - [ ] Confirm deletion
   - [ ] Block should be removed

4. **Filters**
   - [ ] Change School Year → schedules filter
   - [ ] Change Semester → schedules filter
   - [ ] Change Section → schedules filter
   - [ ] "All Sections" → shows all sections

5. **Rooms Tab**
   - [ ] Click "Rooms" button
   - [ ] Select a room from dropdown
   - [ ] Timetable shows that room's schedule
   - [ ] Schedules sync from main timetable

## Key Behavioral Changes

### Before → After

| Feature | Before | After |
|---------|--------|-------|
| Course Availability | Year/Semester specific | All courses always available |
| Year Selector | 1st-4th Year | School Year (2024-2025) |
| Section Input | Text field | Dropdown (A-Z) |
| Unit Configuration | All subjects listed | Checkbox selection by category |
| Max Units | Varied by course | 3 units per section (all courses) |
| Delete Blocks | Right-click menu | Drag to trash area |
| Filter - Days | Included "All Days" | Removed |
| Filter - Rooms | "All Classrooms" | "All Rooms" (no "All" option) |

## File Changes Summary

**Modified Files:**
1. `templates/partials/schedule.html` - Main changes
2. `app.py` - API updates needed
3. (Optional) `services/firebase_service.py` - If schedule model defined there

**New Files Created:**
1. `schedule_completion.js` - Reference implementation
2. `SCHEDULE_REDESIGN_GUIDE.md` - This file

## Troubleshooting

### Issue: Checkboxes don't appear
**Solution:** Check if `populateCourseCheckboxes()` is called in `toggleCourseCategory()`

### Issue: Trash doesn't work
**Solution:** Verify `initTrashArea()` is called on page load

### Issue: Section filter not working
**Solution:** Check `applyFilters()` function includes section filter logic

### Issue: Old schedules still showing
**Solution:** Clear browser localStorage and refresh Firebase collection

## Next Steps

1. Complete JavaScript function installation (use `schedule_completion.js`)
2. Test all functionality per checklist above
3. Update backend API to use new field names
4. Migrate existing schedule data to new structure
5. Test with faculty members

## Support

If you encounter issues:
1. Check browser console for JavaScript errors
2. Verify all functions from `schedule_completion.js` are added
3. Ensure CSS styles for trash area and checkboxes are present
4. Check that ALL_SUBJECTS array is properly formatted

---

**Status:** Implementation 95% complete  
**Remaining:** JavaScript function installation from `schedule_completion.js`  
**Estimated Time:** 15-30 minutes to copy functions and test
