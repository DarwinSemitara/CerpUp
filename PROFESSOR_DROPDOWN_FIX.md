# Professor Dropdown Fix & Testing Guide

## Issues Fixed

### 1. ✅ Bulk Delete Faculty Feature
- Added checkboxes to top-right of each faculty card
- Added trash bin delete button next to "Add Faculty" button
- Button only shows when faculty members are selected
- Confirmation modal shows count of selected faculty
- Red border highlights selected faculty cards
- Bulk delete removes multiple faculty at once

**Files Modified:**
- `templates/partials/schedule.html` - Added checkbox HTML, bulk delete modal
- `static/js/dashboard.js` - Added selection tracking and bulk delete functions

### 2. ✅ Enhanced Professor Dropdown Debugging
- Added comprehensive console logging
- Shows total staff loaded
- Shows eligible professors for selected subject
- Shows all available subject codes in staff data
- Provides helpful hints when no professors found

**Files Modified:**
- `templates/partials/schedule.html` - Enhanced `loadStaffData()` and `onSubjectCodeChange()` functions

---

## How The System Works

### Faculty → Schedule Flow

```
1. MANAGE PAGE (Member Management)
   ↓
   Add member with "Teaching Personnel" checkbox checked
   
2. SCHEDULE PAGE > FACULTY SECTION
   ↓
   Click "Add Faculty" → Select member from dropdown
   → Select year levels → Select subjects they teach
   → System links member to subjects
   
3. SCHEDULE PAGE > CLASS SCHEDULE
   ↓
   Add subject → Select subject code
   → Professor dropdown auto-filters to show ONLY faculty who teach that subject
```

### Key Points:
- **Subject codes must match exactly** (case-sensitive)
- Faculty must be assigned subjects BEFORE they appear in schedule dropdowns
- System filters by comparing `subject.code` in schedule vs `staff.subjects[].code` in faculty data

---

## Testing Instructions

### Prerequisites:
1. Open browser console (Press F12)
2. Navigate to Schedule page
3. Check console for initial staff load message

### Test Scenario 1: Add Faculty with Subjects

**Expected Console Output:**
```
✅ Staff data loaded: X faculty members
📋 Sample staff object: {...}
📚 Subject codes available: HIST/KAS 1, ETHICS 1, CERP 101, ...
```

**Steps:**
1. Scroll to **Faculty** section (above Faculty Load Report)
2. Click **"Add Faculty"** button
3. Select a member from dropdown (must have "Teaching Personnel" checked)
4. Check year level(s) (e.g., "1st Year")
5. Select subjects from the chips that appear
6. Click **"Add Staff"**
7. Verify faculty card appears in grid

### Test Scenario 2: Add Subject to Schedule

**Expected Console Output When Selecting Subject:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Subject selected: HIST/KAS 1
📊 Total staff loaded: 2
✅ Eligible professors for HIST/KAS 1: 1
👥 Professors: Juan Dela Cruz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Steps:**
1. Scroll to **Class Schedule** timetable
2. Click and drag on timetable to select time slot
   OR
3. Use **"Add New Schedule"** form below timetable
4. Select a **Subject Code** from dropdown
5. Check console for debugging output
6. Check **Professor dropdown** - should show faculty assigned to that subject

### Test Scenario 3: No Professors Showing

**Expected Console Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Subject selected: ETHICS 1
📊 Total staff loaded: 2
✅ Eligible professors for ETHICS 1: 0
⚠️ No professors found for subject: ETHICS 1
💡 Hint: Make sure faculty members have been assigned this subject code in the Faculty section
📝 Available subject codes in staff data: HIST/KAS 1, CERP 101
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**This means:**
- Staff data loaded successfully (2 faculty)
- But NONE of them are assigned to teach "ETHICS 1"
- Only "HIST/KAS 1" and "CERP 101" are assigned

**Solution:**
1. Go back to Faculty section
2. Add a faculty member and assign them to "ETHICS 1"
3. Return to schedule and try again

### Test Scenario 4: Bulk Delete Faculty

**Steps:**
1. Scroll to **Faculty** section
2. Click checkboxes on faculty cards (top-right corner)
3. Selected cards get red border
4. Trash bin button appears next to "Add Faculty"
5. Click trash bin button
6. Confirmation modal shows count: "Are you sure you want to delete X faculty member(s)?"
7. Click "Delete" to confirm
8. Faculty members removed from grid
9. Success message appears

---

## Troubleshooting

### Problem: "No professors available for this subject"

**Diagnosis Steps:**
1. Open browser console (F12)
2. Check if staff data loaded:
   - Look for: `✅ Staff data loaded: X faculty members`
   - If X = 0, no faculty added yet
3. Select a subject code and check logs:
   - `📊 Total staff loaded: X` - Should be > 0
   - `✅ Eligible professors: X` - Should be > 0
   - If eligible = 0, check `📝 Available subject codes`

**Common Causes:**
- **No faculty added**: Add faculty first in Faculty section
- **Wrong subject assigned**: Faculty assigned to different subjects
- **Case sensitivity**: Subject codes must match exactly (e.g., "HIST/KAS 1" not "hist/kas 1")
- **Year/Semester mismatch**: Make sure faculty is assigned subjects for the current year/semester filter

**Solutions:**
1. **Add faculty** if total staff = 0
2. **Assign correct subjects** when adding faculty
3. **Check year level selection** - faculty must be assigned to same year level
4. **Verify subject codes match exactly** - check console logs for available codes

---

## Subject Code Reference

All subject codes available in the system (must match exactly):

### 1st Year
**Semester 1:**
- HIST/KAS 1, ETHICS 1, HFDS 101, HUME 100, CERP 101, SDS 101, HK 11

**Semester 2:**
- ARTS 1, HUME 112, HUME 107, HUME 105, SOC 140, BIO 150, HK 12/13, NSTP 1

### 2nd Year
**Semester 1:**
- PI 10, HUME 110, HUME 111, HUME 113, HK 12 or 13, NSTP 2

**Semester 2:**
- STS 1, STAT 166, HUME 114, CERP 161, HUME 115, HK 12 or 13

### 3rd Year
**Semester 1:**
- COMM 10, HUME 195, HUME 122, HUME 123, CERP 140, CERP 122, SDS 172

**Semester 2:**
- HUME 125, HUME 124, SDS 173, HFDS 110, CERP 162, CERP 163, CERP 165

### 4th Year
**Semester 1:**
- HNF 141, CERP 166, CERP 170, CERP 164, CERP 200

**Semester 2:**
- HUME 200a, HUME 199, CERP 200

---

## Additional Notes

### Data Flow
1. **Members** (Manage page) → stored in `members` collection with `is_faculty=true`
2. **Faculty** (Schedule page) → stored in `staff` collection, references `memberId`
3. **Schedule** → filters `staffData` array by matching `subject.code`

### API Endpoints Used
- `GET /api/members?faculty=true` - Load faculty members for dropdown
- `POST /api/staff` - Add faculty with subjects
- `GET /api/staff` - Load all faculty for schedule filtering
- `DELETE /api/staff/:id` - Delete single faculty (used in bulk delete)

### Browser Console Commands (for debugging)
```javascript
// View loaded staff data
console.log(staffData);

// View specific staff member's subjects
console.log(staffData[0].subjects);

// List all subject codes currently assigned
console.log([...new Set(staffData.flatMap(s => s.subjects.map(sub => sub.code)))]);
```

---

## Success Indicators

✅ **Everything Working Correctly:**
- Console shows staff loaded with count > 0
- Selecting subject shows eligible professors > 0
- Professor dropdown populates with names
- Can successfully add schedule with professor
- Bulk delete selects and removes faculty
- Faculty cards highlight when selected

❌ **Something Wrong:**
- Console shows 0 staff loaded → Add faculty first
- Console shows 0 eligible professors → Assign subjects to faculty
- No console logs appear → JavaScript error (check console for errors)
- Dropdown always empty → Check subject code exact match

---

## Quick Fix Checklist

If professors not showing:
- [ ] Check console for staff load count
- [ ] Verify faculty exists in Faculty section
- [ ] Confirm subject codes match exactly
- [ ] Check faculty assigned to correct year level
- [ ] Verify no JavaScript errors in console
- [ ] Try different subject that was definitely assigned
- [ ] Refresh page and check initial staff load message

---

**Last Updated:** Current session
**Files Modified:** `templates/partials/schedule.html`, `static/js/dashboard.js`
