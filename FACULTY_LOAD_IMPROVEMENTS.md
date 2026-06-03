# Faculty Load Report Improvements

## Summary of Changes

### 1. ✅ Auto-Calculate Units Based on Duration
**Rule**: 1 unit = 1 hour

**Implementation**:
- Units are now automatically calculated based on block duration
- Each time slot = 0.5 hours (30 minutes)
- Formula: `units = (number of slots × 0.5)`
- Rounded to 1 decimal place for precision

**Applies to**:
- ✅ Creating new blocks (drag on timetable)
- ✅ Adding from staging area
- ✅ Resizing existing blocks
- ✅ Moving blocks (preserves duration)

**Examples**:
- 1 hour block (2 slots) = 1.0 units
- 1.5 hour block (3 slots) = 1.5 units
- 2 hour block (4 slots) = 2.0 units
- 3 hour block (6 slots) = 3.0 units

### 2. ✅ Group Schedules by Professor
**Behavior**: Schedules with the same professor are grouped together

**Display Format**:
```
# | Professor      | Subject         | Day & Time        | Units | Room    | Section | Actions
1 | Dr. Santos     | ENRP 101 - ...  | Monday, 8:00 AM   | 1.5   | Room 201| BSEP 2-A| Delete
  |                | ENRP 102 - ...  | Tuesday, 10:00 AM | 2.0   | Room 202| BSEP 2-B| Delete
  | Total Units for Dr. Santos:                         | 3.5   |         |         |
2 | Dr. Cruz       | ENRP 103 - ...  | Wednesday, 1:00 PM| 1.0   | Room 203| BSEP 3-A| Delete
  | Total Units for Dr. Cruz:                           | 1.0   |         |         |
```

**Features**:
- Professor name appears once (with rowspan)
- All schedules for that professor listed below
- Total units row at the end of each professor's section
- Total highlighted in maroon color
- Sorted alphabetically by professor name

### 3. ✅ Removed Manual Units Input
**Before**: Users had to manually enter units
**After**: Units calculated automatically

**UI Changes**:
- Removed "Units" field from "New Schedule Block" modal
- Removed "Units" field from "Add Subject" form
- Added informational note: "Units will be automatically calculated based on block duration (1 unit = 1 hour)"

## Technical Implementation

### Auto-Calculate Units Function
```javascript
function calculateUnits(startSlot, endSlot) {
    var duration = endSlot - startSlot;
    var hours = duration * 0.5; // Each slot is 0.5 hours
    return Math.round(hours * 10) / 10; // Round to 1 decimal
}
```

### Resize Handler Update
When user resizes a block:
1. Calculate new duration in slots
2. Convert to hours (slots × 0.5)
3. Update units automatically
4. Save to database

### Faculty Load Report Grouping
```javascript
// Group by professor
var profMap = {};
filtered.forEach(function(s) {
    if (!profMap[s.prof]) {
        profMap[s.prof] = [];
    }
    profMap[s.prof].push(s);
});

// Calculate total units per professor
schedules.forEach(function(s) {
    var hours = (slotIdx(s.end) - slotIdx(s.start)) * 0.5;
    totalUnits += hours;
});
```

## User Experience

### Creating a Block
1. **Drag on timetable** to create block
2. **Fill in details** (no units field)
3. **Block is created** with auto-calculated units based on drawn size
4. **Resize block** → Units update automatically

### Faculty Load Report
1. **Schedules grouped** by professor
2. **Each professor's section** shows all their classes
3. **Total units** displayed at bottom of each section
4. **Real-time updates** when blocks are resized or moved

### Resizing Blocks
1. **Pull bottom edge** to resize
2. **Units recalculate** automatically
3. **Faculty load report** updates immediately
4. **No manual input** needed

## Benefits

### For Users
- ✅ No manual unit calculation needed
- ✅ Consistent unit values (no human error)
- ✅ Easy to see total load per professor
- ✅ Automatic updates when schedules change

### For Administrators
- ✅ Accurate faculty load tracking
- ✅ Easy to identify overloaded professors
- ✅ Quick overview of teaching assignments
- ✅ Grouped view reduces clutter

## Examples

### Scenario 1: Creating a 2-hour Class
1. Drag from 8:00 AM to 10:00 AM (4 slots)
2. Fill in subject details
3. Units automatically set to 2.0

### Scenario 2: Resizing a Block
1. Block is 1.5 hours (1.5 units)
2. Resize to 3 hours
3. Units automatically update to 3.0
4. Faculty load report updates immediately

### Scenario 3: Professor with Multiple Classes
**Dr. Santos teaches**:
- ENRP 101: Monday 8:00-9:30 (1.5 units)
- ENRP 102: Tuesday 10:00-12:00 (2.0 units)
- ENRP 103: Friday 1:00-2:00 (1.0 units)

**Faculty Load Report shows**:
- All 3 classes grouped under Dr. Santos
- Total: 4.5 units

## Database Schema
Units are stored as decimal values in the database:
- Type: `float` or `decimal(3,1)`
- Range: 0.5 to 12.0 (typical academic range)
- Precision: 1 decimal place
