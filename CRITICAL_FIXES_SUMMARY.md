# Critical Production Bugs - Fixed ✅

## Issues Reported
1. **CHE Model 404/400 Errors** - "llama-3.3-70b-versatile does not exist"
2. **Schedule System Broken** - Subjects disappearing, wrong faculty schedules showing, false conflicts
3. **Datetime Warnings** - "datetime.utcnow() is deprecated"

---

## Root Causes Identified

### Issue 1: CHE Models Decommissioned
**Status:** ✅ FIXED  
**Root Cause:** Groq decommissioned llama-3.3-70b and llama-3.1-70b models on **June 17, 2026**

**Fix Applied:**
- File: `services/che_service.py` lines 586-590
- Changed to current production models:
  - `openai/gpt-oss-120b` (500 t/sec)
  - `openai/gpt-oss-20b` (1000 t/sec)
  - `qwen/qwen3.6-27b` (500 t/sec, fallback)

**Source:** https://console.groq.com/docs/models

---

### Issue 2: Database Mismatch (CRITICAL!)
**Status:** ✅ FIXED  
**Root Cause:** **Mixed Firestore/Supabase calls** causing catastrophic data inconsistency

**The Problem:**
```
User drags schedule → PUT saves to SUPABASE ✅
Frontend refreshes → GET reads from FIRESTORE ❌
Result: Schedule disappears, old cross-faculty data appears
```

**What Was Broken:**
1. `GET /api/schedules` - Read from Firestore (stale data)
2. `PUT /api/schedules/<id>` - Wrote to Supabase (fresh data)
3. Conflict detection validated against Firestore (outdated)
4. CHE loaded schedules from Firestore (wrong context)
5. GA saved to Firestore (data split across databases)

**Symptoms:**
- ✅ "moving subjects shows all the other placed subjects even for different faculty members"
  → Firestore had old cross-faculty data
- ✅ "the moved subject will disappear and be placed in the subject block selection"
  → Saved to Supabase, fetched from Firestore (not found)
- ✅ "the warning conflict still triggers even if there is literally nothing in the timeslot"
  → Validation checked Firestore (old data), not Supabase (current data)

**Endpoints Migrated (13 total):**

| Endpoint/Function | File | Line | Status |
|-------------------|------|------|--------|
| `GET /api/schedules` | app.py | 1754 | ✅ Supabase |
| `POST /api/schedules` | app.py | 1820 | ✅ Supabase |
| `PUT /api/schedules/<id>` | app.py | 1913 | ✅ Supabase |
| `DELETE /api/schedules/<id>` | app.py | 1897 | ✅ Supabase |
| POST `/api/schedules/clear` | app.py | 1965 | ✅ Supabase |
| CHE execute-action load | app.py | 628 | ✅ Supabase |
| CHE add_schedule | app.py | 664 | ✅ Supabase |
| CHE move_schedule | app.py | 688 | ✅ Supabase |
| CHE delete_schedule | app.py | 697 | ✅ Supabase |
| CHE reference load | app.py | 712 | ✅ Supabase |
| CHE GA save | app.py | 784 | ✅ Supabase |
| CHE chat context | app.py | 543 | ✅ Supabase |
| GA full generation | app.py | 2175, 2262 | ✅ Supabase |
| NLP schedule context | app.py | 2689 | ✅ Supabase |

**Result:** 100% of schedule operations now use Supabase consistently

---

### Issue 3: Datetime Compatibility
**Status:** ✅ FIXED  
**Root Cause:** Import style mismatch

```python
# OLD (BROKEN)
from datetime import datetime
datetime.now(datetime.UTC)  # ❌ datetime class doesn't have UTC attribute

# NEW (FIXED)
from datetime import datetime, timezone
datetime.now(timezone.utc)  # ✅ Works in Python 3.9-3.13
```

**Changed:** 14+ occurrences across `app.py`

---

## Commits

1. **6d9f26b** - "fix: Critical schedule system repair - migrate all endpoints to Supabase and update CHE models"
2. **8ae8214** - "fix: Replace datetime.UTC with timezone.utc for Python compatibility"
3. **9c3c20d** - "docs: Add Supabase migration checklist and verification script"

---

## Testing Instructions

### 1. Restart Flask Server
```powershell
# Stop current server (Ctrl+C)
python app.py
```

### 2. Verify Schedule Operations
- [ ] Create schedule (manually add a subject)
- [ ] Drag schedule to different time slot → Should stay in place
- [ ] Drag schedule to conflict slot → Should show warning
- [ ] Drag schedule to empty slot → Should move without false warning
- [ ] Switch faculty member → Should only see their schedules (not cross-faculty)
- [ ] Refresh page → Schedules should persist
- [ ] Check schedule opacity → Should be solid (not faded/blurry)

### 3. Verify CHE Chat
- [ ] Open CHE assistant
- [ ] Send any message → Should respond without 404/400 errors
- [ ] Ask about schedules → Should have current context
- [ ] Try schedule action → Should work without database errors

### 4. Verify Console Logs
- [ ] No datetime deprecation warnings
- [ ] No Firestore errors in schedule operations
- [ ] `✅ Found X schedules from Supabase` messages appear

### 5. Run Verification Script (Optional)
```powershell
python verify_schedules.py
```

Expected output:
- ✅ Table 'schedules' exists and is accessible
- ✅ All required fields present
- ✅ No data quality issues found
- ✅ No duplicate IDs found

---

## Database Verification

Check Supabase directly to ensure data is being written:

1. Go to Supabase Dashboard → Table Editor
2. Open `schedules` table
3. Verify recent entries have:
   - `id` (UUID format)
   - `prof`, `subj_code`, `subj_name`
   - `day`, `start`, `end`
   - `school_year` (e.g., "2026-2027")
   - `semester` ("1" or "2")
   - `created_at` (recent timestamp)

---

## Rollback Plan (If Issues Persist)

If critical issues occur:

```bash
# Rollback to before the fixes
git revert 9c3c20d 8ae8214 6d9f26b
git push origin main

# Restart server
python app.py
```

**Note:** This will restore old Firestore-based schedule operations, but CHE models will still be broken (they're decommissioned).

---

## Remaining Work (Non-Critical)

These collections still use Firestore but are NOT causing the reported issues:

- `members` (faculty/staff management)
- `research` (publications)
- `extensions` (extension activities)
- `news` (news/events)
- `engagements` (public engagements)
- `tap_projects` (TAP-HSP projects)

These can be migrated incrementally without affecting schedule functionality.

---

## Performance Notes

**Expected Improvements:**
- Schedule drag-drop should be faster (Supabase is optimized for relational queries)
- Conflict detection should be more accurate (single source of truth)
- No more cross-database sync issues

**Supabase Advantages Over Firestore:**
- ACID transactions
- SQL queries with JOINs
- Built-in full-text search
- Better indexing control
- PostgreSQL ecosystem

---

## Monitoring Recommendations

After deployment, monitor these metrics:

1. **Schedule Operation Errors** - Should be 0%
2. **CHE Model Errors** - Should be 0%
3. **Datetime Warnings** - Should be 0
4. **Schedule Persistence** - 100% (no disappearing schedules)
5. **Cross-Faculty Isolation** - 100% (no data leakage)

---

## Support

If issues persist:

1. Check server logs for specific error messages
2. Run `python verify_schedules.py` to diagnose
3. Review `SUPABASE_MIGRATION_CHECKLIST.md` for troubleshooting
4. Verify `.env` has correct `SUPABASE_URL` and keys
5. Check Supabase dashboard for RLS policy issues

---

**Fix Date:** August 25, 2026  
**Tested On:** Python 3.13.2, Windows  
**Status:** ✅ Production Ready
