# Quick Reference Card

## 🚀 Admin Dashboard - Quick Reference

---

## URLs

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/dashboard/` | Charts and analytics |
| Manage | `/manage/` | Members management ⭐ |
| Research | `/research/` | Research projects |
| Schedule | `/schedule/class/` | Class scheduling |
| Data | `/data/` | Data management |
| Other | `/other/` | Other features |

---

## File Locations

### Templates
```
templates/
├── admin_base.html          # Base template
└── pages/
    ├── dashboard.html       # Dashboard
    ├── manage.html          # Manage ⭐
    ├── research.html        # Research
    └── schedule.html        # Schedule
```

### Static Files
```
static/
├── css/
│   └── admin.css            # Shared styles
└── js/
    ├── admin.js             # Shared JS
    ├── dashboard.js         # Dashboard
    └── manage.js            # Manage ⭐
```

---

## Common CSS Classes

### Buttons
```html
<button class="btn-primary">Primary</button>
<button class="btn-secondary">Secondary</button>
<button class="btn-danger">Danger</button>
```

### Cards
```html
<div class="card">
    <div class="card-header">
        <h2 class="card-title">Title</h2>
    </div>
    <div class="card-body">
        Content
    </div>
</div>
```

### Forms
```html
<div class="form-group">
    <label class="form-label">Label</label>
    <input type="text" class="form-input">
</div>
```

### Tables
```html
<table class="data-table">
    <thead>
        <tr><th>Header</th></tr>
    </thead>
    <tbody>
        <tr><td>Data</td></tr>
    </tbody>
</table>
```

---

## Common JavaScript Functions

### Navigation
```javascript
loadPartial(url, title, element)
toggleSubNav(subNavId, button, isSubItem)
```

### Modals
```javascript
openLogoutModal()
closeLogoutModal()
confirmLogout()
```

### Utilities
```javascript
formatDate(isoString)
formatTime(timeString)
```

---

## API Endpoints

### Members
```
GET    /api/members              # Get all
POST   /api/members              # Add new
DELETE /api/members/<id>         # Delete
POST   /api/members/<id>/create-account  # Create account
```

### Schedules
```
GET    /api/schedules            # Get all
POST   /api/schedules            # Add new
DELETE /api/schedules/<id>       # Delete
POST   /api/schedules/clear      # Clear all
POST   /api/schedules/generate   # Generate with GA
```

### Chat
```
POST   /api/chat/process         # Process NLP message
```

---

## Creating a New Page

### 1. Create Template
```html
<!-- templates/pages/my-page.html -->
{% extends "admin_base.html" %}

{% block content %}
<div class="card">
    <div class="card-header">
        <h2 class="card-title">My Page</h2>
    </div>
    <div class="card-body">
        Content here
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="/static/js/my-page.js"></script>
{% endblock %}
```

### 2. Add Route
```python
# app.py
@app.route('/my-page/')
@login_required
def my_page():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/my-page.html',
                         email=email,
                         initial=initial,
                         page_title='My Page',
                         active_page='my_page')
```

### 3. Add to Sidebar
```html
<!-- admin_base.html -->
<a href="/my-page/" class="nav-item {% if active_page == 'my_page' %}active{% endif %}">
    <svg>...</svg>
    My Page
</a>
```

---

## Troubleshooting

### Page Not Loading
- Check route exists in `app.py`
- Check template file exists
- Check for syntax errors

### Styles Not Applying
- Check `admin.css` is loaded
- Clear browser cache
- Check for CSS conflicts

### JavaScript Not Working
- Check `admin.js` is loaded
- Check browser console for errors
- Check page-specific JS is included

### Navigation Not Highlighting
- Check `active_page` is set in route
- Check sidebar link has correct condition

---

## Key Changes

| Before | After |
|--------|-------|
| Instructions | Manage ⭐ |
| Members on Dashboard | Members on Manage |
| Single file (1900 lines) | Multiple files |
| URL always `/dashboard/` | Proper URLs |
| Refresh → Dashboard | Refresh → Current page |

---

## Sidebar Structure

```
Dashboard
Research
Extensions
  ├─ Public Engagements
  └─ TAP-HSP
      ├─ Capacity Development
      ├─ Model Community
      └─ Praxis
Schedule
  ├─ Class Schedule
  └─ News and Events
Data
Manage ⭐
Other
Logout
```

---

## Dashboard Content

- Publications Line Chart (orange/yellow)
- TAP-HSP Pie Chart
- Welcome Message

---

## Manage Content

- Members Table
- Search & Filter
- Add Member Modal
- Create Account Modal
- Delete Member Modal

---

## Template Variables

```python
email        # User email
initial      # User initial
page_title   # Page title
active_page  # Active page identifier
```

---

## Chart Colors

```css
Orange:       #fb923c
Yellow-Orange: #fbbf24
Yellow:       #fde047
```

---

## Useful Commands

### Start Server
```bash
python app.py
```

### Check Syntax
```bash
python -m py_compile app.py
```

### Clear Cache
```bash
# Windows
del /s /q __pycache__
```

---

## Documentation Files

- `RESTRUCTURE_COMPLETE.md` - Complete overview
- `MIGRATION_GUIDE.md` - Usage guide
- `STRUCTURE_DIAGRAM.md` - Visual diagrams
- `REFACTOR_SUMMARY.md` - Summary
- `IMPLEMENTATION_CHECKLIST.md` - Checklist
- `QUICK_REFERENCE.md` - This file

---

## Status

✅ **Complete and Ready to Use**

- All files created
- All routes updated
- All functionality tested
- Documentation complete

---

## Support

Need help? Check:
1. `MIGRATION_GUIDE.md` for detailed usage
2. `STRUCTURE_DIAGRAM.md` for visual reference
3. Existing page files for examples

---

**Version**: 2.0  
**Last Updated**: May 9, 2026  
**Status**: Production Ready ✅
