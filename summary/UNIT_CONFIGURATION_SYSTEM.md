# Unit Configuration & Draggable Subject Blocks System

## Overview

The new Unit Configuration system replaces the redundant "Add Subject" form with a more intuitive drag-and-drop workflow. Admins now:
1. **Configure weekly unit hours** for each subject
2. **Drag colorful subject blocks** onto the timetable
3. **Track unit allocation** in real-time
4. **See visual feedback** on completion status

---

## Key Features

### ✅ Unit Configuration
- Set weekly unit hours for all subjects in current year/semester
- Auto-fill from curriculum data with one click
- Edit configuration anytime (Set Units → Edit Units toggle)
- Persists across year/semester changes

### ✅ Draggable Subject Blocks
- Color-coded blocks for each subject
- Same subject = same color (even across multiple blocks)
- Shows remaining hours per subject
- Drag onto timetable to create 1-hour blocks
- Blocks auto-hide when fully allocated

### ✅ Real-Time Unit Tracking
- Progress indicator shows completion status
- Subjects with remaining units: greyed out/translucent
- Fully allocated subjects: solid vibrant colors
- Total hours tracked: "3/7 subjects fully allocated • 15.5/21 hours"

### ✅ Smart Validation
- Can't exceed configured unit hours
- Multiple blocks allowed (e.g., 1.5h Mon + 1.5h Wed = 3h total)
- Blocks default to 1 hour, can be extended via resize
- Updates in real-time when blocks added/deleted

---

## User Workflow

### Step 1: Configure Units (One-Time Setup)

1. **Navigate to Schedule page**
2. **Between timetable and Faculty section**, find "Subject Unit Configuration"
3. Click **"Set Units"** button
4. Form expands showing all subjects for current year/semester
5. Options:
   - **Manual entry**: Type hours into each input field
   - **Auto-fill**: Click "Auto-fill from Curriculum" to load defaults
6. Click **"Save Configuration"**
7. Button changes to **"Edit Units"** for future edits

**Screenshot location:**
```
┌─────────────────────────────────────────────────────┐
│  SUBJECT UNIT CONFIGURATION          [Edit Units]   │
├─────────────────────────────────────────────────────┤
│  (Collapsed by default after saving)                │
└─────────────────────────────────────────────────────┘
```

### Step 2: Drag Subject Blocks to Timetable

1. **After saving configuration**, draggable blocks appear below
2. **Block appearance**:
   - Subject code displayed (e.g., "HIST/KAS 1")
   - Remaining hours shown (e.g., "3.0h remaining")
   - Color-coded by subject
   - Translucent if not fully allocated, solid when complete
3. **Drag a block** onto an empty timetable cell
4. **Drop on target time slot**
5. **New Block Modal opens** with:
   - Subject code pre-selected
   - Subject name auto-filled
   - Default 1-hour duration
   - Focus on Professor field

### Step 3: Complete the Schedule Entry

1. Select **Professor** (dropdown filtered to those teaching this subject)
2. Select **Type** (Lecture/Laboratory/Field)
3. Enter **Classroom** and **Section**
4. Click **"Add to Schedule"**
5. Block appears on timetable
6. Draggable block updates to show new remaining hours
7. If fully allocated, block disappears from staging area

### Step 4: Monitor Progress

- Check **progress indicator** in staging area header
- Shows: "X/Y subjects fully allocated • Z/W hours"
- Greyed blocks = still need scheduling
- Solid blocks = partial allocation, more needed
- Missing blocks = fully allocated!

---

## Visual Design

### Unit Configuration Form

```
┌──────────────────────────────────────────────────────────┐
│  Configure weekly unit hours for 1st Year, 1st Semester │
│                          [Auto-fill from Curriculum] btn │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────┐                     │
│  │ HIST/KAS 1                 [3]  hrs/week              │
│  │ Philippine History              │                     │
│  └─────────────────────────────────┘                     │
│  ┌─────────────────────────────────┐                     │
│  │ ETHICS 1                   [3]  hrs/week              │
│  │ Ethics and Moral Reasoning      │                     │
│  └─────────────────────────────────┘                     │
│  ... (all subjects for this year/semester)               │
├──────────────────────────────────────────────────────────┤
│  [Cancel]  [Save Configuration]                          │
└──────────────────────────────────────────────────────────┘
```

### Draggable Subject Blocks (Staging Area)

```
┌──────────────────────────────────────────────────────────┐
│  Unscheduled Subjects (drag to timetable)                │
│  3/7 subjects fully allocated • 15.5/21 hours            │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ HIST/KAS 1  │  │ ETHICS 1    │  │ HFDS 101    │     │
│  │ 3.0h remain │  │ 0.5h remain │  │ 3.0h remain │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│  (greyed/trans)   (solid color)    (greyed/trans)       │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │ HUME 100    │  │ CERP 101    │                      │
│  │ 1.5h remain │  │ 2.0h remain │                      │
│  └─────────────┘  └─────────────┘                      │
│                                                          │
│  (Blocks auto-hide when fully allocated)                │
└──────────────────────────────────────────────────────────┘
```

### Color Coding

- **Same subject code = same color** across all blocks
- Example:
  - HIST/KAS 1 → Orange
  - ETHICS 1 → Blue
  - HFDS 101 → Green
  - (Colors persist even if subject has multiple blocks)

- **Opacity indicates status:**
  - 40% opacity + greyscale = incomplete (needs scheduling)
  - 100% opacity + full saturation = fully allocated

---

## Technical Details

### Data Structure

```javascript
// Unit configuration storage
subjectUnits = {
    'HIST/KAS 1': {
        configured: 3,    // Weekly hours set by admin
        allocated: 1.5    // Hours currently scheduled
    },
    'ETHICS 1': {
        configured: 3,
        allocated: 3      // Fully allocated
    },
    // ... more subjects
}
```

### Key Functions

#### `toggleUnitConfig()`
- Shows/hides unit configuration form
- Toggles button between "Set Units" and "Edit Units"

#### `autoFillUnits()`
- Populates inputs with default values from `ALL_SUBJECTS`
- Matches curriculum unit hours

#### `saveUnitConfiguration()`
- Reads all input values
- Stores in `subjectUnits` object
- Calculates allocated hours from existing schedules
- Renders draggable blocks
- Shows success feedback

#### `calculateAllocatedUnits()`
- Sums up hours from all schedules for each subject
- Duration calculation: `(endSlot - startSlot) / 2` (slots are 30min each)
- Updates `subjectUnits[code].allocated`

#### `renderDraggableBlocks()`
- Filters subjects with remaining units
- Creates draggable HTML blocks
- Applies color coding
- Shows remaining hours
- Updates progress indicator

#### Drag & Drop Handlers
- `handleDragStart()` - Stores subject data, adds dragging class
- `handleDragEnd()` - Removes dragging class
- `handleCellDragOver()` - Shows drop preview (red dashed border)
- `handleCellDragLeave()` - Removes preview
- `handleCellDrop()` - Creates schedule entry, opens NBM modal
- `enableTimetableDropZones()` - Attaches event listeners to all cells

#### `openNewBlockModalWithSubject(day, start, end, code, name)`
- Pre-fills New Block Modal with subject info
- Defaults to 1-hour block
- Focuses professor field
- Triggered after drop event

### Integration Points

**Schedule Creation:**
- `confirmNewBlock()` → adds schedule → calls `calculateAllocatedUnits()` → `renderDraggableBlocks()`

**Schedule Deletion:**
- `deleteEntry()` → removes schedule → calls `calculateAllocatedUnits()` → `renderDraggableBlocks()`

**Year/Semester Filter:**
- `onYearSemesterChange()` → `applyYearSemesterFilter()` → `calculateAllocatedUnits()` → `renderDraggableBlocks()`

**Timetable Rendering:**
- `renderTimetable()` → `enableTimetableDropZones()` (every render)

---

## CSS Classes

### Unit Configuration
- `.unit-config-form` - Container for config form
- `.unit-config-grid` - Grid layout for subject items
- `.unit-config-item` - Individual subject row
- `.unit-input` - Number input for hours
- `.subject-code` - Red bold text for code
- `.subject-name` - Grey small text for name

### Draggable Blocks
- `.draggable-subject` - Base draggable block style
- `.draggable-subject.incomplete` - Greyed out (opacity: 0.4, greyscale filter)
- `.draggable-subject.dragging` - Active drag state (opacity: 0.5)
- `.subj-code` - Subject code text
- `.subj-units` - Remaining hours text

### Drop Zones
- Timetable cells get inline styles on dragover:
  - `background: #fef2f2` (light red)
  - `border: 2px dashed #6b0f1a` (maroon dashed)

---

## User Experience Improvements

### Before (Old System)
❌ Redundant "Add Subject" form (same as timetable click/drag)
❌ No unit tracking
❌ No visual feedback on progress
❌ Hard to see which subjects need scheduling

### After (New System)
✅ One-time unit configuration
✅ Visual draggable blocks
✅ Real-time unit tracking
✅ Color-coded subjects
✅ Progress indicator
✅ Auto-hide completed subjects
✅ Intuitive drag-and-drop workflow

---

## Testing Checklist

### Unit Configuration
- [ ] Click "Set Units" opens form
- [ ] Form shows all subjects for current year/semester
- [ ] "Auto-fill from Curriculum" populates default values
- [ ] Manual input accepts numbers 1-10
- [ ] "Save Configuration" closes form
- [ ] Button changes to "Edit Units"
- [ ] Clicking "Edit Units" reopens form with saved values
- [ ] Form closes on "Cancel"

### Draggable Blocks
- [ ] Blocks appear after saving configuration
- [ ] Each subject has unique color
- [ ] Blocks show remaining hours
- [ ] Incomplete blocks are translucent/greyed
- [ ] Blocks are draggable (cursor changes to grab)
- [ ] Dragging shows visual feedback

### Drag & Drop
- [ ] Can drag block onto empty timetable cell
- [ ] Cell highlights on hover (red dashed border)
- [ ] Highlight removes on drag leave
- [ ] Can't drop on occupied cell (alert shown)
- [ ] Drop opens NBM modal
- [ ] Subject code and name pre-filled
- [ ] Professor dropdown filtered correctly
- [ ] Default 1-hour duration set

### Unit Tracking
- [ ] Progress indicator shows after configuration
- [ ] Format: "X/Y subjects fully allocated • Z/W hours"
- [ ] Updates after adding schedule block
- [ ] Updates after deleting schedule block
- [ ] Blocks disappear when fully allocated
- [ ] Allocated units persist across page refresh

### Year/Semester Switching
- [ ] Changing year refreshes subjects in config form
- [ ] Changing semester refreshes subjects in config form
- [ ] Unit configuration persists per year/semester
- [ ] Draggable blocks update to match filter
- [ ] Progress indicator recalculates correctly

---

## Known Behaviors

### Multiple Blocks for Same Subject
- ✅ **Allowed**: Can create multiple blocks totaling configured hours
- Example: HIST/KAS 1 (3 hours) → 1.5h Monday + 1.5h Wednesday
- Block remains visible until ALL hours allocated

### Unit Validation
- ⚠️ System **DOES NOT PREVENT** exceeding configured hours
- Admin responsible for not over-allocating
- Future enhancement: Add hard limit validation

### Block Colors
- Colors assigned dynamically by `getSubjColor()` function
- Uses predefined palette from schedule system
- Same code = same color, even across semesters

### Persistence
- Unit configuration stored in **JavaScript variable** only
- ⚠️ **NOT SAVED TO DATABASE** (lost on page refresh)
- Enhancement needed: Add `/api/unit-config` endpoint for persistence

---

## Future Enhancements

### Phase 2 (Recommended)
1. **Database persistence** for unit configuration
   - Add `unit_configurations` collection in Firestore
   - Schema: `{ year, semester, subjects: { code: hours } }`
   - Save on configuration, load on page init

2. **Hard unit limit validation**
   - Prevent creating blocks exceeding configured hours
   - Show alert: "Cannot add 2-hour block. HIST/KAS 1 has only 0.5 hours remaining."

3. **Block splitting**
   - Right-click block → "Split into 0.5h increments"
   - Allows more flexible scheduling

4. **Bulk operations**
   - "Auto-schedule" button using genetic algorithm
   - "Copy from previous semester" option

5. **Visual improvements**
   - Animated transitions when blocks disappear
   - Confetti effect when all subjects allocated
   - Progress bar visualization

---

## Troubleshooting

### Problem: Blocks not appearing after configuration

**Diagnosis:**
1. Open browser console (F12)
2. Check for errors
3. Type: `console.log(subjectUnits)`
4. Verify data structure

**Solution:**
- Refresh page and reconfigure
- Check that `calculateAllocatedUnits()` ran
- Verify `renderDraggableBlocks()` called

### Problem: Drag not working

**Diagnosis:**
1. Check console for errors
2. Verify `draggable="true"` attribute on blocks
3. Check `handleDragStart` bound correctly

**Solution:**
- Refresh page
- Try different browser
- Check if JavaScript errors blocking execution

### Problem: Wrong units calculated

**Diagnosis:**
1. Check schedule data: `console.log(schedules)`
2. Verify `subjCode` matches exactly
3. Check slot calculation: `(endSlot - startSlot) / 2`

**Solution:**
- Ensure subject codes match (case-sensitive)
- Delete and recreate schedule if corrupted
- Recalculate: Call `calculateAllocatedUnits()` manually

### Problem: Progress not updating

**Diagnosis:**
1. Check if `updateUnitProgress()` called
2. Verify indicator element exists: `document.getElementById('unit-progress-indicator')`

**Solution:**
- Refresh draggable blocks: Call `renderDraggableBlocks()` in console
- Check that schedule CRUD operations call update functions

---

## API Integration (Future)

### Proposed Endpoints

```javascript
// Save unit configuration
POST /api/unit-config
Body: {
    year: '1',
    semester: '1',
    subjects: {
        'HIST/KAS 1': 3,
        'ETHICS 1': 3,
        // ... more subjects
    }
}

// Get unit configuration
GET /api/unit-config?year=1&semester=1
Response: {
    subjects: {
        'HIST/KAS 1': 3,
        'ETHICS 1': 3,
        // ...
    }
}

// Update existing configuration
PUT /api/unit-config/:id
Body: { subjects: {...} }

// Delete configuration
DELETE /api/unit-config/:id
```

### Database Schema (Firestore)

```
unit_configurations/
  {id}/
    year: '1'
    semester: '1'
    subjects: {
      'HIST/KAS 1': 3,
      'ETHICS 1': 3,
      // ...
    }
    created_at: timestamp
    updated_at: timestamp
```

---

## Files Modified

- `templates/partials/schedule.html` - Main implementation
  - Replaced "Add Subject" section with "Unit Configuration"
  - Added CSS for unit config and draggable blocks
  - Added JavaScript functions for unit tracking
  - Added drag & drop handlers
  - Integrated with existing schedule CRUD operations

---

**Last Updated:** Current session
**Status:** ✅ Fully implemented (except database persistence)
**Next Steps:** Test thoroughly, then add database persistence
