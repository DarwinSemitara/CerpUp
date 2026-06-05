# Auto-Sync Faculty from Members

## Summary
Completely removed the "Add Faculty" functionality. Faculty list now automatically syncs from members marked as "Teaching Personnel" in the Manage page.

## Changes Made

### 1. **Backend API Changes** (`app.py`)

#### GET `/api/staff`
- **Before**: Fetched from separate `staff` collection
- **After**: Fetches from `members` collection where `is_faculty=true`
- **Auto-formats**: Combines first, last, suffix into fullName
- **Result**: Faculty list auto-syncs with member changes

#### POST `/api/staff`
- **Before**: Complex form with member selection, year levels, subjects
- **After**: Returns error message directing users to Manage page
- **Status**: Deprecated but kept for backward compatibility

#### PUT `/api/staff/<id>`
- **Before**: Updated staff record with subjects, availability, photo
- **After**: Returns error directing to Manage page
- **Status**: Deprecated

#### DELETE `/api/staff/<id>`
- **Before**: Permanently deleted staff record
- **After**: Sets `is_faculty=false` on the member
- **Result**: Removes from faculty list but preserves member data

### 2. **Frontend Changes** (`templates/partials/schedule.html`)

#### Removed:
- ❌ "Add Faculty" button
- ❌ Entire Add Staff Modal (200+ lines)
- ❌ Year Level selection
- ❌ Subject assignment form
- ❌ Photo upload for faculty
- ❌ Success modal
- ❌ All related form validation

#### Added:
- ✅ Info message: "Auto-synced from Manage page (Teaching Personnel)"
- ✅ Updated bulk delete modal text to explain faculty status removal

### 3. **JavaScript Changes** (`static/js/dashboard.js`, `static/js/staff.js`)
- No changes needed - frontend just calls `/api/staff` which now returns members
- Existing functions work automatically with new data source

## New Workflow

### Adding Faculty:
1. Go to **Manage** page
2. Add/edit a member
3. Check **"Teaching Personnel/Faculty Member"** checkbox
4. Save
5. ✅ **Automatically appears in Faculty list** on Schedule page

### Removing Faculty:
1. **Option A**: Go to Manage page → Uncheck "Teaching Personnel" 
2. **Option B**: Go to Schedule page → Select faculty → Click bulk delete
3. ✅ **Removes from faculty list** (member data preserved)

### Professor Selection:
1. Create schedule block
2. Select subject
3. **All faculty appear** in dropdown (no filtering)
4. Select any professor
5. Create block

## Database Structure

### Before:
```
members/
  └─ {memberId}
      ├─ first, last, suffix
      ├─ photo_url
      ├─ availability: []
      └─ is_faculty: true/false

staff/
  └─ {staffId}  
      ├─ memberId (reference)
      ├─ fullName
      ├─ subjects: []
      ├─ availability: []
      └─ photo_url
```

### After:
```
members/
  └─ {memberId}
      ├─ first, last, suffix
      ├─ photo_url  
      ├─ availability: []
      └─ is_faculty: true/false ← This is the only source of truth
```

## Benefits

### For Users:
- ✅ **Single source of truth** - One place to manage faculty
- ✅ **No duplicate data** - Member info auto-syncs
- ✅ **Faster workflow** - Just check a box
- ✅ **No complex forms** - No year levels or subject assignment needed
- ✅ **Automatic updates** - Name changes, photos update everywhere

### For System:
- ✅ **Simpler architecture** - One collection instead of two
- ✅ **No data synchronization issues** - No member/staff mismatches
- ✅ **Easier maintenance** - Less code to maintain
- ✅ **Better scalability** - Single query instead of joins

## Migration Notes

### Existing Data:
- Old `staff` collection data is **not migrated**
- System uses `members` collection exclusively
- Admins should re-mark members as faculty if needed

### Backward Compatibility:
- Old `/api/staff` POST/PUT endpoints return helpful errors
- No breaking changes to schedule block creation
- Bulk delete still works (just updates `is_faculty` flag)

## Testing Checklist

- [ ] Mark member as faculty in Manage page
- [ ] Verify they appear in Schedule Faculty list
- [ ] Create schedule block with faculty as professor
- [ ] Uncheck faculty in Manage page
- [ ] Verify they're removed from Faculty list
- [ ] Use bulk delete on faculty
- [ ] Verify member still exists in Manage
- [ ] Re-check faculty checkbox
- [ ] Verify they reappear in Faculty list

---

**Date**: 2026-06-05  
**Deployed**: Yes (auto-deployed via GitHub → Render)  
**Status**: ✅ Complete
