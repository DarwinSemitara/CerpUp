# Faculty Checkbox Update - Complete

## Summary
Updated the member management system to use a separate "Teaching Personnel/Faculty" checkbox instead of having "Faculty" as a type option. This allows chairpersons, representatives, and admin staff to also be marked as teaching personnel.

## Changes Made

### 1. Manage Page - Add Member Modal (`templates/pages/manage.html`)

#### Removed "Faculty" from Type dropdown:
**Before:**
```html
<select name="type" class="form-select" required>
    <option value="chairperson">Chairperson</option>
    <option value="faculty">Faculty</option>
    <option value="reps">Representatives</option>
    <option value="admin_staff">Admin Staff</option>
</select>
```

**After:**
```html
<select name="type" class="form-select" required>
    <option value="chairperson">Chairperson</option>
    <option value="reps">Representatives</option>
    <option value="admin_staff">Admin Staff</option>
</select>
```

#### Added Teaching Personnel Checkbox:
```html
<div class="form-group modal-grid-full">
    <label class="availability-checkbox" style="cursor:pointer;">
        <input type="checkbox" name="is_faculty" id="is-faculty-checkbox" value="true">
        <span style="font-weight:600;">Teaching Personnel/Faculty Member</span>
    </label>
    <p style="font-size:0.75rem;color:#6b7280;">
        Check this if the member is a teaching personnel. They will be available for assignment in the Faculty section.
    </p>
</div>
```

### 2. Manage Page - Members Table

#### Added Faculty Column:
Shows a green checkmark badge if member is teaching personnel, otherwise shows "—"

```html
<th>Faculty</th>
```

#### Updated Filter Toolbar:
- Removed "Faculty" from type filter dropdown
- Added "Teaching Personnel Only" checkbox filter

### 3. Backend Changes (`app.py`)

#### Updated POST `/api/members`:
```python
member = {
    # ... other fields ...
    'type': request.form.get('type', 'admin_staff'),
    'is_faculty': request.form.get('is_faculty', 'false').lower() == 'true',
    # ... other fields ...
}
```

#### Updated GET `/api/members`:
```python
faculty_only = request.args.get('faculty', None)

if faculty_only and faculty_only.lower() == 'true':
    # Filter by is_faculty = true
    docs = db.collection('members').where(
        'is_faculty', '==', True).order_by('created_at').stream()
```

#### Updated POST `/api/staff`:
Changed validation from:
```python
if member_data.get('type') != 'faculty':
    return jsonify({'error': 'Selected member is not a faculty member'}), 400
```

To:
```python
if not member_data.get('is_faculty', False):
    return jsonify({'error': 'Selected member is not marked as teaching personnel'}), 400
```

### 4. JavaScript Updates

#### `manage.js`:
- Updated `applyMemberFilter()` to check `is_faculty` checkbox
- Updated `renderMembers()` to show faculty badge in table
- Updated `submitAddMember()` to send `is_faculty` checkbox value

#### `dashboard.js`:
- Updated `loadFacultyMembers()` to fetch `/api/members?faculty=true`

## New Workflow

### Adding a Teaching Personnel Member:

1. **Go to Manage page** → Click "Add Member"
2. **Fill out form**:
   - Personal info (name, email, etc.)
   - Upload photo
   - Select availability days
   - **Select Type**: Chairperson, Representatives, or Admin Staff
   - **✓ Check "Teaching Personnel/Faculty Member"** ← New checkbox
3. **Save** → Member is created with `is_faculty = true`
4. **Member appears in table** with green checkmark in Faculty column

### Filtering Teaching Personnel:

- **By Type**: Use dropdown (Chairperson, Reps, Admin Staff)
- **By Faculty Status**: Check "Teaching Personnel Only" checkbox
- **Combined**: Can filter by both type AND faculty status
  - Example: Show only Chairpersons who are teaching personnel

### Assigning Faculty in Dashboard:

1. **Go to Dashboard** → Click "Add Faculty"
2. **Dropdown shows** all members where `is_faculty = true`
   - Includes chairpersons, reps, and admin staff if marked as teaching personnel
3. **Select member** → Auto-fills name, photo, availability
4. **Assign** year levels and subjects
5. **Submit** → Faculty record created

## Database Schema

### Members Collection:
```json
{
  "id": "member-uuid",
  "first": "Juan",
  "last": "Dela Cruz",
  "type": "chairperson",  // or "reps" or "admin_staff"
  "is_faculty": true,     // ← New field
  "photo_url": "https://...",
  "availability": ["Monday", "Tuesday"],
  ...
}
```

### Example Scenarios:

#### Scenario 1: Chairperson who teaches
```json
{
  "first": "Dr. Maria",
  "last": "Santos",
  "type": "chairperson",
  "is_faculty": true,  // ✓ Checked
  ...
}
```
→ Can be assigned as faculty in Dashboard

#### Scenario 2: Admin staff who doesn't teach
```json
{
  "first": "John",
  "last": "Reyes",
  "type": "admin_staff",
  "is_faculty": false,  // ✗ Not checked
  ...
}
```
→ Will NOT appear in faculty dropdown in Dashboard

#### Scenario 3: Representative who teaches
```json
{
  "first": "Ana",
  "last": "Cruz",
  "type": "reps",
  "is_faculty": true,  // ✓ Checked
  ...
}
```
→ Can be assigned as faculty in Dashboard

## Benefits

✅ **More flexible** - Any member type can be teaching personnel  
✅ **Clear distinction** - Type (role) vs Teaching status (is_faculty)  
✅ **Better data model** - Represents reality (chairpersons often teach)  
✅ **Easy filtering** - Can filter by type AND faculty status  
✅ **Visual indicator** - Green badge shows teaching personnel at a glance  

## UI/UX Improvements

### Manage Page Table:
- **Faculty Column**: Shows ✓ Yes badge (green) or "—"
- **Filter Checkbox**: "Teaching Personnel Only" for quick filtering
- **Clear labeling**: "Teaching Personnel/Faculty Member" explains purpose

### Dashboard Add Faculty:
- **Dropdown shows**: "Dr. Maria Santos, PhD (Chairperson)" format
- **Auto-fill**: Name, photo, availability from member record
- **Validation**: Only shows members with `is_faculty = true`

## Migration Notes

If you have existing data with `type='faculty'`:

### Option 1: Manual Update
1. Go to each member with `type='faculty'`
2. Change type to appropriate role (Chairperson, Reps, Admin Staff)
3. Check the "Teaching Personnel" checkbox
4. Save

### Option 2: Database Migration Script
Create a script to:
```python
# Pseudocode
for member in members.where('type', '==', 'faculty'):
    member.update({
        'type': 'admin_staff',  # or determine from other data
        'is_faculty': True
    })
```

## Testing Checklist

- [x] "Faculty" removed from type dropdown
- [x] "Teaching Personnel" checkbox added to form
- [x] Checkbox value saved to database as `is_faculty`
- [x] Faculty column shows in members table
- [x] Green badge displays for teaching personnel
- [x] "Teaching Personnel Only" filter works
- [x] Combined filters (type + faculty) work correctly
- [x] Dashboard dropdown shows only `is_faculty = true` members
- [x] Can assign chairperson as faculty
- [x] Can assign representative as faculty
- [x] Can assign admin staff as faculty
- [x] Non-teaching personnel don't appear in faculty dropdown
- [ ] Existing faculty data migrated (if applicable)

## Future Enhancements

1. **Bulk edit**: Select multiple members and mark as teaching personnel
2. **Import/Export**: CSV import with is_faculty column
3. **Analytics**: Show breakdown of teaching personnel by type
4. **Schedule integration**: Validate availability against assigned subjects
5. **Load balancing**: Show teaching load per faculty member
