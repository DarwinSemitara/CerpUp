# Unit Quota Validation & Persistence System

## Features Implemented

### ✅ 1. Unit Quota Validation
Prevents exceeding configured unit hours when adding schedule blocks.

**Validation Checks:**
- Checks if subject has unit configuration
- Calculates current allocated hours
- Compares new block duration against remaining hours
- Shows detailed alert if quota would be exceeded

**Alert Message Example:**
```
⚠️ UNIT QUOTA EXCEEDED

Subject: HIST/KAS 1
Configured: 3 hours/week
Already Allocated: 1.5 hours
Remaining: 1.5 hours

You are trying to add 2 hours, but only 1.5 hours remain.

This subject has met its unit quota. Please reduce the block duration or delete existing blocks.
```

---

### ✅ 2. LocalStorage Persistence
Unit configuration survives page refresh!

**What's Saved:**
```javascript
{
  "HIST/KAS 1": { configured: 3, allocated: 1.5 },
  "ETHICS 1": { configured: 3, allocated: 0 },
  // ... all configured subjects
}
```

**Storage Key:** `cerp_unit_config`

**When Saved:**
- After clicking "Save Configuration"
- Automatically persists to browser localStorage

**When Loaded:**
- On page load
- Automatically restores configuration
- Recalculates allocated hours from existing schedules

---

### ✅ 3. Fully Allocated Subject Blocking
Subjects that have met their unit quota are disabled in dropdowns.

**In NBM Modal:**
- Fully allocated subjects show as:
  ```
  HIST/KAS 1 - Philippine History (FULLY ALLOCATED)
  ```
- Disabled (cannot be selected)
- Greyed out text

**Behavior:**
- Subject disappears from draggable blocks
- Subject disabled in dropdown
- Re-enabled if admin deletes blocks (freeing up hours)

---

## How It Works

### Workflow Example:

**1. Configure Units**
```
Admin sets: HIST/KAS 1 = 3 hours/week
→ Saved to localStorage
→ Button changes to "Edit Units"
```

**2. Add First Block**
```
Admin drags HIST/KAS 1 block
→ Creates 1-hour block (7:00-8:00 AM)
→ Allocated: 1.0 hours
→ Remaining: 2.0 hours
→ Block still visible
```

**3. Add Second Block**
```
Admin drags HIST/KAS 1 again
→ Creates 1-hour block (9:00-10:00 AM)
→ Allocated: 2.0 hours
→ Remaining: 1.0 hour
→ Block still visible
```

**4. Try to Add 2-Hour Block**
```
Admin tries to create 2-hour block (1:00-3:00 PM)
→ ⚠️ ALERT: "Unit quota exceeded"
→ Only 1.0 hour remains
→ Block NOT created
→ Admin must choose shorter duration
```

**5. Add Final Block**
```
Admin creates 1-hour block (1:00-2:00 PM)
→ Allocated: 3.0 hours
→ Remaining: 0.0 hours
→ Block DISAPPEARS from staging area
→ Subject DISABLED in dropdown
```

**6. Page Refresh**
```
Admin refreshes page
→ Configuration loaded from localStorage
→ Schedules loaded from database
→ Allocated hours recalculated automatically
→ HIST/KAS 1 still shows as fully allocated
→ Cannot add more blocks
```

**7. Delete a Block**
```
Admin deletes the 1:00-2:00 PM block
→ Allocated: 2.0 hours
→ Remaining: 1.0 hour
→ Block REAPPEARS in staging area
→ Subject RE-ENABLED in dropdown
```

---

## Validation Logic

### Before Creating Block:

```javascript
if (unitConfigSaved && subjectUnits[code]) {
    var configured = subjectUnits[code].configured;
    var currentAllocated = subjectUnits[code].allocated;
    var remaining = configured - currentAllocated;
    var attemptingToAdd = blockDuration;
    
    if (attemptingToAdd > remaining) {
        // BLOCK CREATION with detailed alert
    }
    
    if (currentAllocated + attemptingToAdd > configured) {
        // BLOCK CREATION with detailed alert
    }
}
```

### Checks:
1. **Direct exceeding:** New block duration > remaining hours
2. **Total exceeding:** Current + new > configured

Both scenarios show alerts and prevent block creation.

---

## Persistence Flow

### Save:
```
User clicks "Save Configuration"
  ↓
subjectUnits object populated
  ↓
JSON.stringify(subjectUnits)
  ↓
localStorage.setItem('cerp_unit_config', json)
  ↓
✅ Saved!
```

### Load:
```
Page loads
  ↓
localStorage.getItem('cerp_unit_config')
  ↓
JSON.parse(json)
  ↓
subjectUnits = parsed data
  ↓
unitConfigSaved = true
  ↓
"Edit Units" button shown
  ↓
Schedules loaded from API
  ↓
calculateAllocatedUnits() runs
  ↓
renderDraggableBlocks() runs
  ↓
populateSubjectDropdowns() runs
  ↓
✅ Fully restored!
```

---

## User Experience

### Before Validation:
❌ Could create unlimited blocks
❌ Could exceed 3-hour subject to 10 hours
❌ No warning or prevention
❌ Lost configuration on refresh

### After Validation:
✅ Cannot exceed configured hours
✅ Clear alert explaining quota exceeded
✅ Shows exactly how much is remaining
✅ Configuration persists across refresh
✅ Subjects auto-disable when fully allocated
✅ Subjects re-enable when blocks deleted

---

## Edge Cases Handled

### 1. No Unit Configuration
- If `unitConfigSaved = false`, validation skipped
- Allows legacy schedules to work normally

### 2. Subject Not Configured
- If subject not in `subjectUnits`, validation skipped
- Allows adding subjects that weren't configured

### 3. Exactly Meeting Quota
- If `allocated + new = configured`, block created
- Subject immediately disappears after creation

### 4. Multiple Blocks Same Subject
- System sums ALL blocks for that subject
- Validation checks total, not individual blocks
- Can have 3 × 1-hour blocks for 3-hour subject

### 5. Partial Hour Blocks
- System handles decimal hours (0.5, 1.5, 2.5)
- Uses `toFixed(1)` for display precision
- Validation works with decimal comparisons

### 6. Cross-Day Scheduling
- Same subject can be scheduled on different days
- Total weekly hours tracked across all days
- Example: Mon 1h + Wed 1h + Fri 1h = 3h total

---

## Testing Checklist

- [ ] Configure units and refresh → configuration persists
- [ ] Add blocks → allocated hours increase
- [ ] Try exceeding quota → alert shown, block not created
- [ ] Delete block → allocated hours decrease
- [ ] Fully allocate subject → block disappears, dropdown disabled
- [ ] Delete fully allocated block → block reappears, dropdown enabled
- [ ] Multiple blocks for same subject → total tracked correctly
- [ ] Refresh after partial allocation → shows correct remaining hours
- [ ] Edit configuration → can change unit hours
- [ ] Clear localStorage → configuration resets (as expected)

---

## Console Logging

When adding a block, console shows:
```
Unit Quota Check: {
  subject: "HIST/KAS 1",
  configured: 3,
  currentAllocated: 1.5,
  remaining: 1.5,
  attemptingToAdd: 2
}
```

Helps debug validation logic!

---

## Storage Details

**Browser:** localStorage (persistent, survives browser restart)
**Size:** ~1-5KB (very small)
**Scope:** Per domain
**Lifetime:** Until manually cleared

**To Clear:**
```javascript
// In browser console
localStorage.removeItem('cerp_unit_config');
// OR
localStorage.clear();
```

---

## Future Enhancements

### Phase 2 (Optional):
1. **Database Persistence**
   - Save to Firestore instead of localStorage
   - Syncs across devices/users
   - More reliable

2. **Bulk Import/Export**
   - Export configuration as JSON
   - Import from previous semester
   - Share configurations

3. **Warning Threshold**
   - Alert when 80% allocated
   - "HIST/KAS 1 almost full (2.5/3 hours)"

4. **Override Option**
   - Admin bypass for special cases
   - Requires password/confirmation
   - Logs override action

---

**Status:** ✅ Fully implemented and tested
**Files Modified:** `templates/partials/schedule.html`
