# Debug Guide for Unit Configuration System

## Issues Fixed

### 1. ✅ Empty State Message Centering
- Added `display:flex`, `flex-direction:column`, `align-items:center`, `justify-content:center` to center the icon and text
- Icon now has `display:block` to ensure proper centering
- Width set to `100%` for proper flex container behavior

### 2. ✅ `getSubjColor is not defined` Error
- Changed `getSubjColor(subj.code)` to `colorFor(subj.code, currentYear, currentSemester)`
- Uses existing `colorFor()` function from timetable rendering

### 3. ✅ Enhanced Debugging
- Added comprehensive console logging to trace execution
- Shows input field count, processing steps, and configuration data

---

## Debug Steps to Test

### Open Browser Console (F12)

1. **Navigate to Schedule page**
2. **Open console** (Press F12)
3. **Click "Set Units"** button

**Expected console output:**
```
(populateUnitConfigGrid should log subjects)
```

4. **Click "Auto-fill from Curriculum"** button

**Check:** All input fields should be populated with default values

5. **Click "Save Configuration"** button

**Expected console output:**
```
💾 Saving unit configuration...
Found 7 input fields
Processing: HIST/KAS 1 = 3 hours
Processing: ETHICS 1 = 3 hours
... (more subjects)
✅ Configuration data: { "HIST/KAS 1": { configured: 3, allocated: 0 }, ... }
🎨 Rendering draggable blocks...
Year/Semester: 1-1
Total subjects: 7
Subject units config: { ... }
Available subjects to render: 7
Creating block for: HIST/KAS 1 - Remaining: 3 - Color: #...
... (more blocks)
✅ Blocks rendered successfully!
✅ Unit configuration saved successfully!
```

---

## Troubleshooting

### Problem: "Found 0 input fields"

**Cause:** Form not visible or inputs not rendered

**Solution:**
1. Check if form is expanded after clicking "Set Units"
2. Inspect element `<div class="unit-config-grid">` - should contain inputs
3. Check for JavaScript errors blocking render

**Manual Test in Console:**
```javascript
document.querySelectorAll('.unit-input').length
// Should return > 0 if form is populated
```

### Problem: "Available subjects to render: 0"

**Cause:** No subjects with configured units > allocated units

**Solutions:**

**Check 1 - Configuration saved?**
```javascript
console.log(subjectUnits);
// Should show: { "HIST/KAS 1": { configured: 3, allocated: 0 }, ... }
```

**Check 2 - Subjects for current year/semester?**
```javascript
console.log(currentYear, currentSemester);
console.log(ALL_SUBJECTS[currentYear + '-' + currentSemester]);
// Should return array of subjects
```

**Check 3 - Filter logic working?**
```javascript
// Manually test filter
var key = currentYear + '-' + currentSemester;
var subjects = ALL_SUBJECTS[key] || [];
var available = subjects.filter(function(subj) {
    var unitData = subjectUnits[subj.code];
    if (!unitData || unitData.configured === 0) return false;
    return unitData.allocated < unitData.configured;
});
console.log('Filtered:', available);
```

### Problem: Blocks appear but not draggable

**Cause:** Event handlers not attached or `draggable="true"` missing

**Solution:**
1. Inspect block element - should have `draggable="true"` attribute
2. Check console for errors in `handleDragStart`

**Manual Test:**
```javascript
// Check if functions exist
typeof handleDragStart  // should be "function"
typeof handleDragEnd    // should be "function"
```

### Problem: Colors not showing

**Cause:** `colorFor()` function not returning valid color

**Solution:**
```javascript
// Test color function
colorFor('HIST/KAS 1', '1', '1')
// Should return hex color like "#fde8ea"
```

### Problem: Progress indicator not updating

**Cause:** `updateUnitProgress()` not being called or element missing

**Solution:**
```javascript
// Check if element exists
document.getElementById('unit-progress-indicator')
// Should return <span> element

// Manually trigger update
updateUnitProgress()
// Check if indicator text updates
```

---

## Common Issues

### Issue 1: Form expands but no subjects shown

**Likely Cause:** `ALL_SUBJECTS` not defined or empty for current year/semester

**Check:**
```javascript
console.log(ALL_SUBJECTS);
// Should show object with keys like '1-1', '1-2', '2-1', etc.

console.log(ALL_SUBJECTS['1-1']);
// Should show array of 7 subjects for 1st Year, 1st Semester
```

**Fix:** Ensure `ALL_SUBJECTS` is defined before unit configuration code

### Issue 2: Blocks rendered but invisible

**Likely Cause:** CSS not loaded or colors too light

**Check:**
1. Inspect block element
2. Check computed styles for `background-color`
3. Verify `.draggable-subject` CSS class applied

**Fix:**
- Check if `colorFor()` returns valid hex color
- Ensure CSS loaded properly
- Try hardcoded color for testing: `style="background-color: #ff0000;"`

### Issue 3: Can drag but drop doesn't work

**Likely Cause:** Timetable drop zones not enabled

**Check:**
```javascript
// Verify drop zones enabled
document.querySelectorAll('#sched-table tbody td:not(:first-child)').length
// Should return number of timetable cells (e.g., 120)
```

**Fix:** Ensure `enableTimetableDropZones()` called after `renderTimetable()`

---

## Manual Testing Commands

### 1. Manually Set Configuration

```javascript
// Bypass UI and set directly
subjectUnits = {
    'HIST/KAS 1': { configured: 3, allocated: 0 },
    'ETHICS 1': { configured: 3, allocated: 0 },
    'HFDS 101': { configured: 3, allocated: 0 }
};
unitConfigSaved = true;
renderDraggableBlocks();
```

### 2. Force Re-render

```javascript
renderDraggableBlocks();
```

### 3. Check Current State

```javascript
console.log('Configuration saved:', unitConfigSaved);
console.log('Subject units:', subjectUnits);
console.log('Current year/sem:', currentYear, currentSemester);
console.log('Available subjects:', ALL_SUBJECTS[currentYear + '-' + currentSemester]);
```

### 4. Test Color Function

```javascript
// Test multiple subjects
['HIST/KAS 1', 'ETHICS 1', 'HFDS 101'].forEach(code => {
    console.log(code, '→', colorFor(code, '1', '1'));
});
```

### 5. Verify Container

```javascript
var container = document.getElementById('staging-blocks');
console.log('Container found:', !!container);
console.log('Container HTML:', container.innerHTML);
```

---

## Expected Behavior After Fixes

### ✅ Empty State (Before Configuration)
- Icon and text centered horizontally and vertically
- Grey color (#9ca3af)
- Document icon visible and centered
- Text: "Set unit hours first to enable draggable subject blocks"

### ✅ Configuration Process
1. Click "Set Units" → Form expands
2. Click "Auto-fill" → All inputs populated with curriculum values
3. Click "Save" → Console shows logs, form closes, button changes to "Edit Units"
4. Draggable blocks appear with colors and remaining hours

### ✅ Draggable Blocks
- Each block shows subject code and remaining hours
- Blocks are colorful (not grey if they have remaining hours)
- Hover shows slight elevation
- Can grab and drag onto timetable
- Drop opens NBM modal with subject pre-filled

### ✅ Progress Indicator
- Shows: "X/Y subjects fully allocated • Z/W hours"
- Updates in real-time as blocks added
- Positioned in staging area header

---

## Quick Fix Checklist

If it's still not working after these changes:

- [ ] Hard refresh page (Ctrl+Shift+R)
- [ ] Clear browser cache
- [ ] Check for JavaScript errors in console
- [ ] Verify `ALL_SUBJECTS` defined (type in console)
- [ ] Verify `colorFor` function exists (type in console)
- [ ] Check current year/semester values
- [ ] Try manual configuration (see commands above)
- [ ] Check if form renders by inspecting `.unit-config-grid`
- [ ] Verify `.unit-input` elements exist after form opens

---

## Success Indicators

You'll know it's working when:
1. ✅ Empty state icon and text are centered
2. ✅ Console shows "Found X input fields" (where X > 0)
3. ✅ Console shows "Available subjects to render: X" (where X > 0)
4. ✅ Colorful blocks appear in staging area
5. ✅ No errors in console
6. ✅ Blocks are draggable (cursor changes)
7. ✅ Progress indicator shows in header

---

**Next Steps:**
1. Test with the enhanced debugging
2. Share console output if still not working
3. Take screenshot of what you see
4. Let me know which step fails

