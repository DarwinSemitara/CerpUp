# Schedule Drag-Drop Critical Fixes

## Issues Fixed (Commit 277d0ca)

### 1. ✅ Cross-Faculty Schedule Flash
**Problem:** When moving a schedule block, ALL faculty schedules appeared briefly before disappearing

**Root Cause:**
```javascript
// OLD CODE (BROKEN)
filtered = schedules.slice();  // Copies ALL schedules
applyFilters();                // Filters later
renderTimetable();             // Renders ALL before filter completes → FLASH!
```

**Fix:** Removed premature `filtered = schedules.slice()` and let `applyFilters()` set it correctly
```javascript
// NEW CODE (FIXED)
// Don't set filtered yet - let applyFilters do it
applyFilters();  // This sets filtered array correctly
renderTimetable(); // Now renders only filtered schedules
```

**File:** `templates/partials/schedule.html` line 3289

---

### 2. ✅ Schedules Disappearing Completely
**Problem:** After moving a schedule, it sometimes vanished entirely (not in timetable, not in subject blocks)

**Root Cause:** Race condition caused by unnecessary database reload
```javascript
// OLD CODE (BROKEN)
schedules[idx].day = newDay;    // Optimistic update
schedules[idx].start = newStart;
// ... render ...
await loadSchedules();          // Reloads ALL schedules from DB
// If DB hasn't updated yet → schedule lost!
```

**Fix:** Removed unnecessary `loadSchedules()` call - optimistic update is sufficient
```javascript
// NEW CODE (FIXED)
schedules[idx].day = newDay;    // Optimistic update
schedules[idx].start = newStart;
// ... render ...
// Success - just refresh UI, no DB reload needed
refreshFilterOptions();
renderReport();
```

**File:** `templates/partials/schedule.html` line 5196

---

### 3. ✅ False Conflict Detection
**Problem:** Moving a schedule to an empty slot triggered "Time conflict detected" even though no schedules existed for that faculty on that day

**Root Cause:** Conflict detection checked ALL semesters/years, not just the current one
```javascript
// OLD CODE (BROKEN)
schedules.forEach(function (s) {
    if (s.prof !== prof) return;  // Filter by professor
    if (s.day !== day) return;    // Filter by day
    // Missing: Filter by semester and year!
    // Checks against schedules from ALL semesters → false conflicts
});
```

**Fix:** Added semester and school year filtering
```javascript
// NEW CODE (FIXED)
schedules.forEach(function (s) {
    if (s.prof !== prof) return;
    if (s.day !== day) return;
    if (s.schoolYear !== currentSchoolYear) return;  // NEW!
    if (s.semester !== currentSemester) return;      // NEW!
    // Now only checks relevant schedules
});
```

**File:** `templates/partials/schedule.html` line 3350

---

### 4. ✅ Schedule Not Found Error
**Problem:** If schedule ID not found in array during drag, silently failed

**Fix:** Added safety check with explicit error handling
```javascript
// NEW CODE
var idx = schedules.findIndex(function (s) { return s.id === dragId; });
if (idx < 0) {
    console.error('❌ Schedule not found in array:', dragId);
    showToast('Error: Schedule not found. Reloading...', 'error');
    await loadSchedules();
    // Clean up and exit
    return;
}
```

**File:** `templates/partials/schedule.html` line 5157

---

### 5. ✅ Network Timeout Errors
**Problem:** Intermittent `[WinError 10035] A non-blocking socket operation could not be completed` errors

**Fix:** Added retry logic with exponential backoff
```python
# NEW CODE
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        result = supabase.table('schedules').select('*').execute()
        # Success
        return jsonify(entries)
    except Exception as e:
        retry_count += 1
        if retry_count < max_retries:
            time.sleep(0.5 * retry_count)  # 0.5s, 1s, 1.5s
            continue
        else:
            return jsonify({'error': str(e)}), 500
```

**File:** `app.py` line 1754

---

## Testing Checklist

### Before Testing
1. **Restart Flask server** - Critical for changes to take effect
   ```powershell
   # Stop current server (Ctrl+C)
   python app.py
   ```

2. **Hard refresh browser** - Clear cached JavaScript
   ```
   Ctrl + Shift + R (Windows/Linux)
   Cmd + Shift + R (Mac)
   ```

### Test Scenarios

#### Test 1: Cross-Faculty Flash
**Steps:**
1. Go to Schedule page
2. Select Faculty A from dropdown
3. Drag a schedule block to a different time slot
4. **Watch carefully** during the drag

**Expected:** Only Faculty A's schedules visible throughout
**Previous Bug:** Brief flash of ALL faculty schedules

**Status:** ⬜ Pass / ⬜ Fail

---

#### Test 2: Schedule Persistence
**Steps:**
1. Select a faculty member
2. Drag a schedule block to a new time slot
3. Wait 2 seconds
4. Check if schedule is still in the new position
5. Refresh the page (F5)
6. Check if schedule persisted

**Expected:** Schedule stays in new position after drag AND after page refresh
**Previous Bug:** Schedule disappeared completely

**Status:** ⬜ Pass / ⬜ Fail

---

#### Test 3: Conflict Detection - Same Faculty
**Steps:**
1. Select Faculty A
2. Place two schedules on the same day
3. Try to drag one schedule to overlap the other's time

**Expected:** "Time conflict detected" warning appears
**Previous Bug:** Should work (this was correct)

**Status:** ⬜ Pass / ⬜ Fail

---

#### Test 4: No False Conflicts - Empty Slot
**Steps:**
1. Select Faculty A
2. Ensure Monday 8:00-9:00 is completely empty for this faculty
3. Drag a schedule block to Monday 8:00-9:00

**Expected:** Schedule moves successfully WITHOUT conflict warning
**Previous Bug:** False "Time conflict detected" even though slot was empty

**Status:** ⬜ Pass / ⬜ Fail

---

#### Test 5: No False Conflicts - Different Semester
**Steps:**
1. Ensure Faculty A has schedules in Semester 1 (2026-2027)
2. Switch to Semester 2 (2026-2027) filter
3. Place a new schedule in the same time slot that was used in Semester 1

**Expected:** No conflict warning (different semesters don't conflict)
**Previous Bug:** False conflict because it checked ALL semesters

**Status:** ⬜ Pass / ⬜ Fail

---

#### Test 6: Network Resilience
**Steps:**
1. Open browser DevTools → Network tab
2. Throttle network to "Slow 3G"
3. Try moving several schedules quickly

**Expected:** Operations complete successfully (may take longer)
**Previous Bug:** Random failures with "non-blocking socket" errors

**Status:** ⬜ Pass / ⬜ Fail

---

## Troubleshooting

### Issue: Still seeing cross-faculty flash
**Cause:** Browser cached old JavaScript  
**Fix:** Hard refresh (Ctrl+Shift+R), check browser console for errors

### Issue: Schedules still disappearing
**Check console for errors:**
```javascript
❌ Schedule not found in array: <uuid>
```
If this appears, the schedule ID is being lost during drag. Check:
1. Is the schedule ID valid in the initial render?
2. Is `dragId` being set correctly on mousedown?

### Issue: Still getting false conflicts
**Check console logs:**
```javascript
console.log('Checking conflict:', {
    prof: s.prof,
    day: s.day,
    schoolYear: s.schoolYear,
    semester: s.semester,
    currentYear: currentSchoolYear,
    currentSem: currentSemester
});
```
Should filter out schedules from different years/semesters

### Issue: Network errors persist
**Check backend logs:** Should see retry attempts
```
Get schedules retry 1/3: [error]
Get schedules retry 2/3: [error]
```
If all 3 retries fail, check:
1. Supabase connection stable?
2. Connection pool exhausted?
3. Rate limiting?

---

## Performance Improvements

**Before fixes:**
- Every drag caused full database reload (expensive)
- Rendered ALL schedules before filtering (laggy)
- No retry on network errors (unreliable)

**After fixes:**
- No database reload after successful drag (fast)
- Only renders filtered schedules (smooth)
- 3 retries with backoff (reliable)

**Expected improvements:**
- Drag-drop feels instant (no reload delay)
- No visual glitches (no flash)
- More reliable on slow networks

---

## Rollback Plan

If issues persist:
```bash
git revert 277d0ca
git push origin main
```

Then restart Flask server.

**Note:** This will restore old behavior with all the bugs.

---

**Fixed Date:** August 26, 2026  
**Commit:** 277d0ca  
**Files Changed:** 2 (app.py, templates/partials/schedule.html)  
**Lines Changed:** +94 -58
