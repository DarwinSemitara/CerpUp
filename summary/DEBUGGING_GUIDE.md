# Debugging Guide - Drag & Drop Issues

## Issues to Debug

1. ✗ Cannot place draggable blocks in timetable
2. ✗ No professor options in dropdown (staffData issue)
3. ✗ Schedule blocks don't show trash hover effect
4. ✗ Schedule blocks don't delete when dropped on trash

## Debug Steps

### Step 1: Open Browser Console
Open your browser's developer tools (F12) and go to the Console tab.

### Step 2: Check Initial Logs

When the page loads, you should see:
```
✅ Trash area found, initializing...
✅ Trash area initialized successfully
🎯 Enabling timetable drop zones for [number] cells
✅ Timetable drop zones enabled
```

**If you DON'T see these:**
- Trash area or timetable isn't being initialized
- Check if JavaScript is loading properly

### Step 3: Test Staging Block Drag

1. Open unit configuration
2. Check some courses and save
3. Try to drag a block from staging area
4. **Expected console output:**
   ```
   🎯 Started dragging staging block: CERP 101 isDraggingBlock: false
   ```

5. Drag over an empty timetable cell
6. **Expected console output:**
   ```
   (Nothing if draggedSubject is null)
   OR
   (Cell should turn pink if draggedSubject exists)
   ```

7. **If you see:**
   ```
   ⚠️ draggedSubject is null in handleCellDragOver
   ```
   **Then:** The handleDragStart isn't being called or draggedSubject isn't being set

### Step 4: Check if draggedSubject is Set

In the console, while dragging, type:
```javascript
draggedSubject
```

**Expected:** `{code: "CERP 101", name: "..."}`
**If null:** handleDragStart isn't working

### Step 5: Test Schedule Block Drag to Trash

1. Create a schedule first (click and drag in timetable to create one)
2. Try to drag the schedule block
3. **Expected console output:**
   ```
   🗑️ Dragging schedule block to trash: [id]
   ```

4. Drag over trash area
5. **Expected console output:**
   ```
   🗑️ Dragover trash area, isDraggingBlock: true
   ✅ Added drag-over class to trash area
   ```

6. **If isDraggingBlock is false:**
   - The schedule block isn't using makeScheduleBlocksDraggable
   - Check if makeScheduleBlocksDraggable is being called

### Step 6: Check isDraggingBlock Variable

In the console, while dragging, type:
```javascript
isDraggingBlock
```

**For staging blocks:** Should be `false`
**For schedule blocks:** Should be `true`

### Step 7: Check Staff Data

In the console, type:
```javascript
staffData
```

**Expected:** Array with faculty objects: `[{fullName: "Dr. Smith", ...}, ...]`
**If empty array:** Faculty data isn't being loaded from Firebase

To manually check Firebase:
```javascript
loadStaffData().then(() => console.log('Staff loaded:', staffData))
```

### Step 8: Verify Event Listeners

Check if event listeners are attached:

**For timetable cells:**
```javascript
document.querySelectorAll('#sched-table tbody td:not(:first-child)').length
```
Should return a number > 0

**For trash area:**
```javascript
document.getElementById('trash-area')
```
Should return the trash div element

### Step 9: Test Drag Events Manually

In console:
```javascript
// Test if dragstart fires
document.querySelectorAll('.draggable-subject').forEach(el => {
  el.addEventListener('dragstart', () => console.log('DRAGSTART FIRED!'))
})
```

Then try dragging a block. If you see "DRAGSTART FIRED!" then the event is working.

## Common Issues & Fixes

### Issue: draggedSubject is always null

**Cause:** handleDragStart isn't being called

**Fix:** Check if blocks have the ondragstart attribute
```html
<div class="draggable-subject" 
     ondragstart="handleDragStart(event)"
     ondragend="handleDragEnd(event)">
```

**Verify in console:**
```javascript
document.querySelectorAll('.draggable-subject[ondragstart]').length
```
Should be > 0

### Issue: Timetable cells don't respond to drag

**Cause:** enableTimetableDropZones isn't being called or cells aren't found

**Check:**
```javascript
// See if function exists
typeof enableTimetableDropZones
// Should return "function"

// See if it was called
// (Look for the console.log in Step 2)
```

### Issue: Trash area doesn't respond

**Cause:** initTrashArea isn't being called or isDraggingBlock is false

**Check:**
```javascript
// See if trash area element exists
document.getElementById('trash-area')

// See if it has event listeners (can't check directly, but should see logs)
```

### Issue: No professors in dropdown

**Cause:** staffData is empty or not loaded

**Fix:** Check Firebase connection and data:
```javascript
// Check if loadStaffData function exists
typeof loadStaffData
// Should return "function"

// Try loading manually
loadStaffData().then(() => {
  console.log('Total staff:', staffData.length)
  console.log('Staff data:', staffData)
})
```

**If staffData is still empty:**
1. Check Firebase credentials
2. Check if 'staff' collection exists in Firestore
3. Check if faculty members are added to the collection

## Expected Behavior Summary

### Dragging Staging Block → Timetable
1. ✅ Block has `draggable="true"`
2. ✅ ondragstart calls handleDragStart
3. ✅ isDraggingBlock = false
4. ✅ draggedSubject = {code, name}
5. ✅ Timetable cell turns pink on dragover
6. ✅ Modal opens on drop

### Dragging Schedule Block → Trash
1. ✅ Block has `draggable="true"` (set by makeScheduleBlocksDraggable)
2. ✅ dragstart sets isDraggingBlock = true
3. ✅ Trash area turns red on dragover
4. ✅ Confirmation dialog on drop
5. ✅ Schedule deleted from timetable

## Next Steps

1. Run through debug steps above
2. Copy any error messages or unexpected console output
3. Report findings so we can identify the root cause

---

## Quick Test Script

Paste this in browser console to test all at once:

```javascript
console.log('=== DRAG & DROP DEBUG ===');
console.log('Trash area exists:', !!document.getElementById('trash-area'));
console.log('Staging blocks count:', document.querySelectorAll('.draggable-subject').length);
console.log('Schedule blocks count:', document.querySelectorAll('.sched-block').length);
console.log('Timetable cells count:', document.querySelectorAll('#sched-table tbody td:not(:first-child)').length);
console.log('staffData length:', typeof staffData !== 'undefined' ? staffData.length : 'undefined');
console.log('isDraggingBlock:', typeof isDraggingBlock !== 'undefined' ? isDraggingBlock : 'undefined');
console.log('draggedSubject:', typeof draggedSubject !== 'undefined' ? draggedSubject : 'undefined');
console.log('======================');
```
