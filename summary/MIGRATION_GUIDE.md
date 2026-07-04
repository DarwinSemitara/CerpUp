# Migration Guide - Admin Dashboard Restructure

## Quick Start

The admin dashboard has been restructured. Here's what you need to know:

---

## What Changed?

### 1. **Sidebar Navigation**
- **"Instructions"** → **"Manage"**
- Manage page now contains Members management

### 2. **File Structure**
- Old: Everything in `admin.html` (1900+ lines)
- New: Separate files for each page

### 3. **URLs**
- URLs now properly reflect the current page
- Refreshing works correctly
- No more redirecting to dashboard

---

## New File Locations

### Templates
```
templates/
├── admin_base.html              # Base template (sidebar + header)
├── pages/
│   ├── dashboard.html           # Dashboard (charts only)
│   ├── manage.html              # Members management
│   ├── research.html            # Research page
│   ├── schedule.html            # Schedule wrapper
│   └── placeholder.html         # Placeholder for other pages
└── partials/
    └── schedule.html            # Schedule content (unchanged)
```

### Static Files
```
static/
├── css/
│   └── admin.css                # Shared styles
└── js/
    ├── admin.js                 # Shared JavaScript
    ├── dashboard.js             # Dashboard charts
    └── manage.js                # Members CRUD
```

---

## How to Use

### Adding a New Page

1. **Create the template** in `templates/pages/`:
```html
{% extends "admin_base.html" %}

{% block content %}
<div class="card">
    <div class="card-header">
        <h2 class="card-title">My New Page</h2>
    </div>
    <div class="card-body">
        <!-- Your content here -->
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="/static/js/my-page.js"></script>
{% endblock %}
```

2. **Add the route** in `app.py`:
```python
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

3. **Add to sidebar** in `admin_base.html`:
```html
<a href="/my-page/" class="nav-item {% if active_page == 'my_page' %}active{% endif %}">
    <svg>...</svg>
    My Page
</a>
```

---

## Common Tasks

### Accessing Members Management
- Navigate to **Manage** in the sidebar
- Or go directly to `/manage/`

### Viewing Dashboard Charts
- Navigate to **Dashboard** in the sidebar
- Or go directly to `/dashboard/`

### Managing Class Schedule
- Navigate to **Schedule → Class Schedule**
- Or go directly to `/schedule/class/`

---

## Styling

### Using Shared Styles
All pages automatically have access to styles in `/static/css/admin.css`:

```html
<!-- These classes are available everywhere -->
<button class="btn-primary">Primary Button</button>
<button class="btn-secondary">Secondary Button</button>
<button class="btn-danger">Danger Button</button>

<div class="card">
    <div class="card-header">
        <h2 class="card-title">Card Title</h2>
    </div>
    <div class="card-body">
        Card content
    </div>
</div>

<table class="data-table">
    <!-- Table content -->
</table>
```

### Adding Page-Specific Styles
Add a `<style>` block in your page template:

```html
{% block content %}
<style>
    .my-custom-class {
        color: red;
    }
</style>

<div class="my-custom-class">Content</div>
{% endblock %}
```

---

## JavaScript

### Using Shared Functions
All pages have access to functions in `/static/js/admin.js`:

```javascript
// Navigation
loadPartial(url, title, element)
toggleSubNav(subNavId, button, isSubItem)

// Logout
openLogoutModal()
closeLogoutModal()
confirmLogout()

// Utilities
formatDate(isoString)
formatTime(timeString)
```

### Adding Page-Specific JavaScript
Create a new JS file in `/static/js/` and include it:

```html
{% block scripts %}
<script src="/static/js/my-page.js"></script>
{% endblock %}
```

---

## API Endpoints

All API endpoints remain unchanged:

### Members
- `GET /api/members` - Get all members
- `POST /api/members` - Add member
- `DELETE /api/members/<id>` - Delete member
- `POST /api/members/<id>/create-account` - Create account

### Schedules
- `GET /api/schedules` - Get all schedules
- `POST /api/schedules` - Add schedule
- `DELETE /api/schedules/<id>` - Delete schedule
- `POST /api/schedules/clear` - Clear all
- `POST /api/schedules/generate` - Generate with GA

### Chat
- `POST /api/chat/process` - Process NLP message

---

## Troubleshooting

### Page Not Loading
1. Check the route exists in `app.py`
2. Check the template file exists in `templates/pages/`
3. Check for syntax errors in the template

### Styles Not Applying
1. Check `/static/css/admin.css` is loaded
2. Clear browser cache
3. Check for CSS conflicts

### JavaScript Not Working
1. Check `/static/js/admin.js` is loaded
2. Check browser console for errors
3. Ensure page-specific JS is included in `{% block scripts %}`

### Navigation Not Highlighting
1. Check `active_page` is set correctly in route
2. Check sidebar link has correct `{% if active_page == '...' %}`

---

## Best Practices

### 1. **Use the Base Template**
Always extend `admin_base.html` for consistency:
```html
{% extends "admin_base.html" %}
```

### 2. **Set Page Variables**
Always pass these variables from your route:
```python
return render_template('pages/my-page.html',
                     email=email,
                     initial=initial,
                     page_title='My Page',
                     active_page='my_page')
```

### 3. **Use Shared Styles**
Use classes from `admin.css` instead of inline styles:
```html
<!-- Good -->
<button class="btn-primary">Click Me</button>

<!-- Avoid -->
<button style="padding:8px;background:#6b0f1a;">Click Me</button>
```

### 4. **Keep JavaScript Modular**
Create separate JS files for each page instead of inline scripts:
```html
<!-- Good -->
{% block scripts %}
<script src="/static/js/my-page.js"></script>
{% endblock %}

<!-- Avoid -->
{% block scripts %}
<script>
    // Hundreds of lines of code here...
</script>
{% endblock %}
```

### 5. **Use Semantic HTML**
Use proper HTML5 elements:
```html
<header>, <nav>, <main>, <section>, <article>, <aside>, <footer>
```

---

## Need Help?

Check these files for examples:
- `templates/pages/dashboard.html` - Charts and data visualization
- `templates/pages/manage.html` - Tables, modals, forms
- `templates/pages/schedule.html` - Including partials
- `static/js/dashboard.js` - Chart.js integration
- `static/js/manage.js` - CRUD operations

---

## Summary

✅ **Sidebar**: "Instructions" → "Manage"  
✅ **Members**: Moved to Manage page  
✅ **Files**: Separated into individual pages  
✅ **URLs**: Properly reflect current page  
✅ **Refresh**: Works correctly on all pages  
✅ **Styles**: Centralized in admin.css  
✅ **Scripts**: Modular and organized  

The restructure is complete and ready to use!
