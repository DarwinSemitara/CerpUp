# Quick Test - Copy & Paste Into Console

## Step 1: Check Current State

Paste this in browser console:

```javascript
console.clear();
console.log('═══════════════════════════════════════');
console.log('         CERP SCHEDULE DEBUG           ');
console.log('═══════════════════════════════════════');
console.log('');
console.log('📊 SCHEDULES:');
console.log('  Total in database:', schedules.length);
console.log('  Visible in timetable:', filtered.length);
console.log('  Difference:', schedules.length - filtered.length, '(hidden by filter)');
console.log('');
console.log('🎯 DRAG & DROP:');
console.log('  Schedule blocks:', document.querySelectorAll('.sched-block').length);
console.log('  Draggable blocks:', document.querySelectorAll('.sched-block[draggable="true"]').length);
console.log('  Staging blocks:', document.querySelectorAll('.draggable-subject').length);
console.log('  Trash area exists:', !!document.getElementById('trash-area'));
console.log('');
console.log('📚 UNIT TRACKING:');
console.log('  Unit config saved:', unitConfigSaved);
console.log('  Configured subjects:', Object.keys(subjectUnits).length);
if (Object.keys(subjectUnits).length > 0) {
    Object.keys(subjectUnits).forEach(code => {
        var u = subjectUnits[code];
        console.log('    ', code, ':', u.allocated, '/', u.configured, 'hours');
    });
}
console.log('');
console.log('🔧 CURRENT FILTERS:');
console.log('  School Year:', currentSchoolYear);
console.log('  Semester:', currentSemester);
console.log('  Section:', currentSection || 'All');
console.log('');
console.log('═══════════════════════════════════════');
```

## Step 2: Test Unit Tracking

If unit tracking shows 0 but you have schedules, paste this:

```javascript
console.log('🔍 DEBUGGING UNIT TRACKING:');
console.log('');
console.log('Configured subjects:', Object.keys(subjectUnits));
console.log('');
console.log('Checking each schedule:');
schedules.forEach((s, i) => {
    var matches = s.semester === currentSemester;
    var inConfig = !!subjectUnits[s.subjCode];
    var duration = (slotIdx(s.end) - slotIdx(s.start)) / 2;
    
    console.log(i + '.', s.subjCode, ':', {
        semester: s.semester,
        matches: matches,
        inConfig: inConfig,
        duration: duration + 'h',
        willCount: matches && inConfig
    });
});
console.log('');
console.log('Recalculating...');
calculateAllocatedUnits();
renderDraggableBlocks();
console.log('Done! Check staging area for updated hours.');
```

## Step 3: Test Drag to Trash

Paste this, then try dragging:

```javascript
console.log('🗑️ TESTING TRASH FUNCTIONALITY:');
console.log('');

// Check schedule blocks
var blocks = document.querySelectorAll('.sched-block');
console.log('Found', blocks.length, 'schedule blocks');

if (blocks.length > 0) {
    console.log('First block details:');
    var first = blocks[0];
    console.log('  ID:', first.dataset.id);
    console.log('  Draggable:', first.getAttribute('draggable'));
    console.log('  Has dragstart listener:', first.ondragstart !== null);
}

// Check trash area
var trash = document.getElementById('trash-area');
console.log('');
console.log('Trash area:', trash ? 'FOUND' : 'NOT FOUND');

console.log('');
console.log('👉 Now try dragging a schedule block to trash');
console.log('   Watch for these messages:');
console.log('   🗑️ Dragging schedule block to trash: [id]');
console.log('   🗑️ Dragover trash area, isDraggingBlock: true');
console.log('   ✅ Added drag-over class to trash area');
```

## Step 4: Manual Trash Test

If drag doesn't work, test trash area directly:

```javascript
// Simulate a drop on trash
console.log('🧪 MANUAL TRASH TEST:');
var trash = document.getElementById('trash-area');
var firstSchedule = schedules[0];

if (firstSchedule) {
    console.log('Testing deletion of:', firstSchedule.subjCode);
    console.log('Schedule ID:', firstSchedule.id);
    
    // This should work even if drag doesn't
    deleteScheduleById(firstSchedule.id);
} else {
    console.log('No schedules to test with');
}
```

## Step 5: Check Filter Issues

If schedules aren't showing:

```javascript
console.log('🔍 FILTER DEBUG:');
console.log('');
console.log('Current filter settings:');
console.log('  schoolYear:', currentSchoolYear);
console.log('  semester:', currentSemester);
console.log('  section:', currentSection);
console.log('');
console.log('Checking why schedules are filtered:');

schedules.forEach((s, i) => {
    var matchSchoolYear = s.schoolYear === currentSchoolYear || !s.schoolYear;
    var matchSemester = s.semester === currentSemester;
    var matchSection = !currentSection || s.section === currentSection;
    var passes = matchSchoolYear && matchSemester && matchSection;
    
    if (!passes) {
        console.log(i + '.', s.subjCode, 'HIDDEN because:');
        if (!matchSchoolYear) console.log('   ❌ schoolYear:', s.schoolYear, '≠', currentSchoolYear);
        if (!matchSemester) console.log('   ❌ semester:', s.semester, '≠', currentSemester);
        if (!matchSection) console.log('   ❌ section:', s.section, '≠', currentSection);
    }
});
```

## Expected Results

After running tests, you should see:

✅ **Schedules visible** in timetable
✅ **Unit tracking** shows correct hours
✅ **Draggable blocks** update remaining hours
✅ **Trash drag** shows console messages
✅ **Trash hover** turns red

## If Something Doesn't Work

1. **Copy the console output** from Step 1
2. **Try the specific test** for the broken feature
3. **Copy any error messages** (red text in console)
4. **Report back** with the output

---

**Quick Links:**
- Refresh page: Ctrl+F5 (Windows) / Cmd+Shift+R (Mac)
- Open console: F12
- Clear console: `console.clear()`
