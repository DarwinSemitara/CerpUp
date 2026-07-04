# Quick Fix & Test Guide

## Changes Applied

### 1. Fixed Subject Dropdown (Professor Issue)
**File:** `templates/partials/schedule.html`
**Function:** `onSubjectCodeChange()`
**Change:** Now uses flat `ALL_SUBJECTS` array instead of year-semester key

**Test:**
1. Click and drag in timetable to create a schedule
2. Select a subject from dropdown
3. Check if professors appear in dropdown
4. **If still empty:** Faculty data isn't loaded from Firebase

### 2. Added Extensive Logging
All drag operations now log to console:
- `🎯` = Staging block events
- `🗑️` = Trash area/schedule block events
- `⚠️` = Warnings/errors
- `✅` = Success messages

## Test Procedure

### Test 1: Check Console on Page Load

**Open browser console (F12), refresh page, look for:**
```
✅ Trash area found, initializing...
✅ Trash area initialized successfully
🎯 Enabling timetable drop zones for XX cells
✅ Timetable drop zones enabled
```

**If missing:** Copy error messages and report back

### Test 2: Test Staging Block Drag

1. Click "Set Units" button
2. Expand CERP, check a few courses
3. Click "Save Configuration"
4. You should see draggable blocks appear
5. **Try to drag one**
6. **Watch console for:**
   ```
   🎯 Started dragging staging block: CERP 101 isDraggingBlock: false
   ```

7. **If you DON'T see this:** The drag event isn't firing
8. **Drag over empty timetable cell**
9. **If cell doesn't turn pink:** Check console for:
   ```
   ⚠️ draggedSubject is null in handleCellDragOver
   ```

### Test 3: Quick Console Check

**Paste this in browser console:**
```javascript
console.log('=== QUICK DEBUG ===');
console.log('1. Trash area:', !!document.getElementById('trash-area'));
console.log('2. Draggable blocks:', document.querySelectorAll('.draggable-subject').length);
console.log('3. Schedule blocks:', document.querySelectorAll('.sched-block').length);
console.log('4. Timetable cells:', document.querySelectorAll('#sched-table tbody td:not(:first-child)').length);
console.log('5. Staff count:', typeof staffData !== 'undefined' ? staffData.length : 'Staff not loaded');
console.log('===================');
```

**Expected output:**
```
1. Trash area: true
2. Draggable blocks: [some number if you configured units]
3. Schedule blocks: [number of schedules you created]
4. Timetable cells: [should be > 500]
5. Staff count: [should be > 0 if you added faculty]
```

### Test 4: Manually Test Drag Event

**Paste in console:**
```javascript
// Add a test listener to see if dragstart fires AT ALL
document.querySelectorAll('.draggable-subject').forEach(block => {
  block.addEventListener('dragstart', function(e) {
    console.log('✨ TEST: Dragstart event FIRED on:', e.target.dataset.subjectCode);
  });
});
```

Then try dragging a block. If you see "✨ TEST: Dragstart event FIRED", the event system works but handleDragStart might have an issue.

### Test 5: Check Faculty Data

**Paste in console:**
```javascript
if (typeof staffData !== 'undefined') {
  console.log('Faculty loaded:', staffData.length, 'members');
  console.log('Sample:', staffData[0]);
} else {
  console.log('staffData is not defined');
  // Try loading it
  if (typeof loadStaffData === 'function') {
    loadStaffData().then(() => console.log('Loaded:', staffData.length));
  }
}
```

## Common Scenarios

### Scenario A: "Nothing happens when I drag"

**Possible causes:**
1. Drag event isn't firing → Check Test 4 above
2. handleDragStart has an error → Check console for JavaScript errors
3. Block isn't draggable → Check if blocks have `draggable="true"` attribute

**Verify in console:**
```javascript
document.querySelector('.draggable-subject').getAttribute('draggable')
// Should return "true"
```

### Scenario B: "Cell doesn't turn pink when I drag over it"

**Possible causes:**
1. draggedSubject is null → handleDragStart didn't set it
2. Event listeners aren't attached → enableTimetableDropZones wasn't called
3. Something is preventing dragover event

**Verify:**
```javascript
// Check if draggedSubject gets set
// Drag a block, then quickly type in console:
draggedSubject
// Should show {code: "...", name: "..."}
```

### Scenario C: "Trash doesn't turn red"

**Possible causes:**
1. Schedule blocks aren't draggable → makeScheduleBlocksDraggable not called
2. isDraggingBlock is false → Should be true for schedule blocks
3. Trash area event listeners not attached

**Verify:**
```javascript
// Check if schedule blocks are draggable
document.querySelector('.sched-block')?.getAttribute('draggable')
// Should return "true"

// Check isDraggingBlock while dragging schedule
// (drag schedule block, then quickly type:)
isDraggingBlock
// Should be true
```

### Scenario D: "No professors in dropdown"

**This is a Firebase data issue, not drag-drop**

**Verify:**
```javascript
staffData
// If empty array → faculty not added to Firebase
// If undefined → loadStaffData not called
```

**Quick fix - Add test data:**
```javascript
// Temporarily add test professor
staffData = [{fullName: 'Dr. Test Professor'}];
// Then select a subject in the modal
```

## What to Report

After running the tests above, please report:

1. **Console output from Test 3** (Quick Debug)
2. **Any red error messages** in console
3. **Results from Test 4** (Does drag event fire?)
4. **Value of staffData** (for professor issue)

This will help identify the exact problem!

---

## Most Likely Issues

Based on the symptoms:

1. **Can't place blocks:** 
   - Most likely: `draggedSubject` is null when dropping
   - Reason: `handleDragStart` isn't being called
   - Check: Run Test 4 to verify drag events fire

2. **No trash hover:**
   - Most likely: Schedule blocks aren't draggable
   - Reason: `makeScheduleBlocksDraggable` isn't being called
   - Check: Verify `renderTimetable()` calls `attachBlockHandlers()`

3. **No professors:**
   - Most likely: Firebase data empty
   - Reason: Faculty members not added yet
   - Check: Run Test 5 to verify staffData

