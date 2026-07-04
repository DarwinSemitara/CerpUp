# CERP UPLB Department System — Development Guideline

## Project Overview

This system is intended for department-level use within the College of Human Ecology (CHE) / CERP at UPLB.

Primary features:

* Research and report uploads
* Automatic report generation

  * PDF export
  * Formatted Excel export
* Scheduling system using a Genetic Algorithm
* Department-level data management
* Online deployment for demonstrations and future institutional use

The current goal is:

* Build a working prototype/MVP
* Demonstrate functionality to panelists and clients
* Keep the system scalable enough for future expansion

---

# Final Chosen Tech Stack

## Backend Framework

### Flask

Reason:

* Lightweight and fast to develop
* Easier for rapid prototyping
* Excellent Python ecosystem for:

  * PDF generation
  * Excel generation
  * Genetic algorithms
* Simpler than Django for current project scope

Recommended libraries:

* Flask
* Flask-CORS
* python-dotenv
* gunicorn

---

## Database / Backend Services

### Firebase

Services to use:

* Firestore Database
* Firebase Authentication (optional)
* Firebase Storage

Reason:

* Easier setup for prototype deployment
* No inactivity pause issues like Supabase free tier
* Fast cloud setup
* Good enough for department-level scale
* Works well with Flask

Firebase will store:

* User data
* Research metadata
* Scheduling data
* Generated report references
* Uploaded files

---

## Hosting

### Render

Reason:

* Easy GitHub deployment
* No credit card required
* Good for thesis/demo deployment
* Reliable enough for prototype stage

Known limitation:

* Free tier sleeps after inactivity
* First request may take 30–60 seconds

Mitigation:

* Open the app before demonstrations
* Keep the app active during presentations

Possible future upgrade:

* Northflank
* Paid Render plan
* Railway

---

## Version Control

### GitHub

Purpose:

* Source control
* Deployment integration with Render
* Collaboration
* Backup

Important:
Never upload:

* .env files
* Firebase service account credentials
* Secret keys

---

# Recommended System Architecture

## Suggested Folder Structure

```text
/project_root
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
│
├── /routes
│   ├── auth_routes.py
│   ├── report_routes.py
│   ├── upload_routes.py
│   ├── scheduling_routes.py
│
├── /services
│   ├── firebase_service.py
│   ├── pdf_service.py
│   ├── excel_service.py
│   ├── scheduler_service.py
│
├── /algorithms
│   ├── genetic_algorithm.py
│
├── /templates
│   ├── report_template.html
│
├── /static
│
├── /uploads
│
├── /generated_reports
│
└── /utils
```

---

# Core Features Breakdown

## 1. Research Upload Module

Features:

* Upload research files
* Store metadata
* Categorize reports
* Save author information
* Store upload timestamps

Possible fields:

* Title
* Authors
* Department
* Category
* Date
* File URL
* Keywords

---

## 2. Report Generation Module

### PDF Generation

Recommended tools:

* WeasyPrint
* ReportLab

Recommended approach:

* Use HTML templates
* Convert HTML → PDF

Reason:

* Easier formatting
* Easier maintenance
* Better visual consistency

---

### Excel Generation

Recommended library:

* openpyxl

Recommended approach:

* Create a fixed Excel template
* Automatically fill template fields

Reason:

* Consistent formatting
* Easier maintenance
* Faster development

Important:
Lock the report format early.
Changing report formats later can become difficult.

---

## 3. Scheduling System

### Genetic Algorithm

Recommended libraries:

* numpy
* pandas
* deap (optional)

Possible scheduling constraints:

* Faculty availability
* Room availability
* Time conflicts
* Subject allocation
* Preferred schedules

Suggested approach:

* Separate algorithm logic from Flask routes
* Keep scheduling code modular

Example:

```text
/algorithms/genetic_algorithm.py
```

---

# Firebase Data Structure Recommendations

Keep the structure clean and organized.

Suggested collections:

```text
users
researches
reports
schedules
uploads
```

Avoid:

* Deeply nested collections
* Random inconsistent document structures
* Excessive data duplication

Reason:

* Easier maintenance
* Easier migration later
* Cleaner report generation

---

# Environment Variables

Store sensitive data in:

```text
.env
```

Example:

```env
FIREBASE_API_KEY=your_key
FIREBASE_PROJECT_ID=your_project_id
SECRET_KEY=your_secret_key
```

Never upload .env to GitHub.

Add to .gitignore:

```text
.env
```

---

# Deployment Notes

## Render Deployment Steps

1. Push project to GitHub
2. Connect GitHub repository to Render
3. Set:

   * Build command
   * Start command
4. Add environment variables
5. Deploy

Suggested start command:

```bash
gunicorn app:app
```

---

# Recommended Development Phases

## Phase 1 — Core Prototype

Focus only on:

* Upload system
* Firebase integration
* Basic authentication
* PDF generation
* Excel generation
* Initial scheduling logic

Goal:
Working demonstration.

---

## Phase 2 — UI Improvements

Improve:

* Dashboard
* Navigation
* User experience
* Responsiveness

---

## Phase 3 — Scheduling Enhancements

Improve:

* Genetic algorithm optimization
* Constraint handling
* Conflict detection
* Schedule visualization

---

## Phase 4 — Future Institutional Improvements

Potential upgrades:

* Django migration
* PostgreSQL/Supabase migration
* Better hosting
* User roles
* Analytics
* Audit logs

---

# Development Priorities

The most important parts of this system are:

1. Reliable report generation
2. Clean data flow
3. Functional scheduling system
4. Usable interface
5. Stable demonstrations

The hosting platform is not the most important part right now.

---

# Important Reminders

## Keep the project manageable

Do not overengineer.

Focus on:

* Functionality
* Reliability
* Simplicity

---

## Build modularly

Separate:

* Routes
* Services
* Algorithms
* Report generation

This makes future migration easier.

---

## Maintain clean templates

For:

* PDFs
* Excel files

This will save significant development time later.

---

# Final Stack Summary

## Current Prototype Stack

* Flask
* Firebase
* Render
* GitHub
* Python libraries for PDF/Excel generation
* Python-based Genetic Algorithm

This stack is:

* Practical
* Fast to develop
* Appropriate for department-level deployment
* Suitable for thesis/demo presentation
* Expandable in the future

---

# Long-Term Migration Possibility

If the system becomes officially adopted institution-wide:

Possible future upgrades:

* Flask → Django
* Firebase → PostgreSQL/Supabase
* Render → Northflank/Paid Hosting

Current architecture should be kept modular to make future migration easier.
