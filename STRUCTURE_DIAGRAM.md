# Admin Dashboard Structure Diagram

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CERP Admin Dashboard                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────────────────────────────────────────┐
│              │                                                  │
│   SIDEBAR    │              MAIN CONTENT AREA                   │
│              │                                                  │
│  Dashboard   │  ┌────────────────────────────────────────────┐ │
│  Research    │  │                                            │ │
│  Extensions  │  │         Page Content Loads Here            │ │
│    ├─ Pub Eng│  │                                            │ │
│    └─ TAP-HSP│  │    (Dashboard, Manage, Research, etc.)     │ │
│  Schedule    │  │                                            │ │
│    ├─ Class  │  │                                            │ │
│    └─ Events │  │                                            │ │
│  Data        │  └────────────────────────────────────────────┘ │
│  Manage ⭐   │                                                  │
│  Other       │                                                  │
│  Logout      │                                                  │
│              │                                                  │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## File Structure Tree

```
CERP2.0/
│
├── app.py                          # Flask routes
│
├── templates/
│   ├── admin_base.html             # 🏗️ Base template (sidebar + header)
│   │
│   ├── pages/                      # 📄 Full page templates
│   │   ├── dashboard.html          # Dashboard with charts
│   │   ├── manage.html             # Members management ⭐
│   │   ├── research.html           # Research page
│   │   ├── schedule.html           # Schedule wrapper
│   │   └── placeholder.html        # Generic placeholder
│   │
│   └── partials/                   # 🧩 Reusable components
│       ├── schedule.html           # Schedule content
│       ├── research.html           # Research content
│       ├── pub_eng.html            # Public Engagements
│       ├── tap_hsp.html            # TAP-HSP
│       └── placeholder.html        # Placeholder
│
├── static/
│   ├── css/
│   │   └── admin.css               # 🎨 Shared styles
│   │
│   ├── js/
│   │   ├── admin.js                # 🔧 Shared JavaScript
│   │   ├── dashboard.js            # 📊 Dashboard charts
│   │   └── manage.js               # 👥 Members CRUD
│   │
│   └── images/                     # 🖼️ Static images
│
└── services/
    ├── firebase_service.py         # Firebase integration
    ├── cloudinary_service.py       # Image uploads
    ├── nlp_service.py              # AI chatbot
    └── scheduler_service.py        # Genetic algorithm
```

---

## Page Flow Diagram

```
┌─────────────┐
│   Login     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      Dashboard                               │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Publications Chart   │  │  TAP-HSP Chart       │        │
│  │ (Line Graph)         │  │  (Pie Chart)         │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                              │
│  ┌────────────────────────────────────────────────┐        │
│  │         Welcome Message                         │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
       │
       ├──────────────────────────────────────────────┐
       │                                               │
       ▼                                               ▼
┌─────────────┐                              ┌─────────────────┐
│  Research   │                              │    Manage ⭐    │
│             │                              │                 │
│  Research   │                              │  ┌───────────┐  │
│  Projects   │                              │  │  Members  │  │
│  List       │                              │  │   Table   │  │
│             │                              │  └───────────┘  │
└─────────────┘                              │                 │
       │                                     │  [Add Member]   │
       │                                     │  [Search]       │
       ▼                                     │  [Filter]       │
┌─────────────┐                              └─────────────────┘
│  Schedule   │                                      │
│             │                                      │
│  ┌────────┐ │                                      ▼
│  │ Manual │ │                              ┌──────────────┐
│  │  Mode  │ │                              │ Add Member   │
│  └────────┘ │                              │    Modal     │
│             │                              └──────────────┘
│  ┌────────┐ │                                      │
│  │   AI   │ │                                      ▼
│  │  Mode  │ │                              ┌──────────────┐
│  └────────┘ │                              │Create Account│
│             │                              │    Modal     │
└─────────────┘                              └──────────────┘
```

---

## Data Flow Diagram

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │
       │ HTTP Request
       ▼
┌──────────────────────────────────────────┐
│            Flask (app.py)                 │
│                                           │
│  Routes:                                  │
│  • /dashboard/     → dashboard.html       │
│  • /manage/        → manage.html ⭐       │
│  • /research/      → research.html        │
│  • /schedule/class/→ schedule.html        │
│                                           │
│  API Routes:                              │
│  • /api/members    → CRUD operations      │
│  • /api/schedules  → Schedule management  │
│  • /api/chat       → NLP processing       │
└──────┬───────────────────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Firebase   │  │ Cloudinary  │  │     NLP     │
│  (Database) │  │  (Images)   │  │  (Chatbot)  │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## Template Inheritance Diagram

```
┌────────────────────────────────────────────────────────┐
│              admin_base.html                           │
│  ┌──────────────────────────────────────────────────┐ │
│  │  <head>                                          │ │
│  │    • Chart.js                                    │ │
│  │    • Google Fonts                                │ │
│  │    • admin.css                                   │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Sidebar                                         │ │
│  │    • Navigation links                            │ │
│  │    • Active page highlighting                    │ │
│  │    • Collapsible sub-menus                       │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Header                                          │ │
│  │    • Page title                                  │ │
│  │    • User info                                   │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  {% block content %}                             │ │
│  │    ← Page content goes here                      │ │
│  │  {% endblock %}                                  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Logout Modal                                    │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  <scripts>                                       │ │
│  │    • admin.js                                    │ │
│  │    • {% block scripts %}                         │ │
│  │      ← Page-specific scripts                     │ │
│  │    • {% endblock %}                              │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         │               │               │              │
         ▼               ▼               ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ dashboard   │  │   manage    │  │  research   │  │  schedule   │
│   .html     │  │   .html ⭐  │  │   .html     │  │   .html     │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Manage Page (manage.html)                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Toolbar                                               │ │
│  │  [Filter: All Types ▼] [Search: _________] [🔍]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Members Table                                         │ │
│  │  ┌──────┬──────┬────────┬──────────┬──────┬─────────┐ │ │
│  │  │Photo │ Name │ Email  │ Position │ Type │ Actions │ │ │
│  │  ├──────┼──────┼────────┼──────────┼──────┼─────────┤ │ │
│  │  │  👤  │ John │ j@...  │ Prof     │ Fac  │ [C] [D] │ │ │
│  │  │  👤  │ Jane │ ja@... │ Assoc    │ Fac  │ [C] [D] │ │ │
│  │  └──────┴──────┴────────┴──────────┴──────┴─────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pagination                                            │ │
│  │  [<] [1] [2] [3] [>]                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  [+ Add Member]                                              │
└─────────────────────────────────────────────────────────────┘
         │
         │ Click "Add Member"
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Add Member Modal                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Photo Upload                                          │ │
│  │  [📷 Click to upload]                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ First Name       │  │ Last Name        │                │
│  │ [___________]    │  │ [___________]    │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Email            │  │ Position         │                │
│  │ [___________]    │  │ [___________]    │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Availability                                          │ │
│  │  [Mon] [Tue] [Wed] [Thu] [Fri] [Sat]                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  [Cancel]  [Add Member]                                      │
└─────────────────────────────────────────────────────────────┘
         │
         │ Submit
         ▼
┌─────────────────────────────────────────────────────────────┐
│              manage.js                                       │
│  • submitAddMember()                                         │
│  • POST /api/members                                         │
│  • Upload photo to Cloudinary                                │
│  • Save to Firebase                                          │
│  • Reload members table                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Changes Summary

### Before (admin.html)
```
admin.html (1900+ lines)
├── Sidebar
├── Dashboard
│   ├── Charts
│   └── Members Table ❌
├── All other pages embedded
└── All JavaScript inline
```

### After (Restructured)
```
admin_base.html (200 lines)
├── Sidebar
├── Header
└── Content block

pages/
├── dashboard.html (Charts only)
├── manage.html (Members Table) ⭐
├── research.html
└── schedule.html

static/
├── css/admin.css (Shared styles)
└── js/
    ├── admin.js (Shared)
    ├── dashboard.js (Charts)
    └── manage.js (Members) ⭐
```

---

## Navigation Flow

```
User clicks "Manage" in sidebar
         │
         ▼
Browser navigates to /manage/
         │
         ▼
Flask route: section_manage()
         │
         ▼
Renders: pages/manage.html
         │
         ├─ Extends: admin_base.html
         ├─ Includes: manage.js
         └─ Active page: 'manage'
         │
         ▼
Browser displays Manage page
         │
         ├─ Sidebar highlights "Manage"
         ├─ URL shows /manage/
         ├─ Members table loads
         └─ Refresh works correctly ✅
```

---

## Legend

- ⭐ = New/Changed
- 🏗️ = Base/Foundation
- 📄 = Full page template
- 🧩 = Reusable component
- 🎨 = Styles
- 🔧 = JavaScript
- 📊 = Charts/Data
- 👥 = Members/Users
- 🖼️ = Images
- ❌ = Removed/Moved

---

This structure provides:
✅ Better organization
✅ Easier maintenance
✅ Proper URL navigation
✅ Modular components
✅ Scalable architecture
