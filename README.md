# DCERP - Department of Community and Environmental Resource Planning

> A comprehensive research management platform designed for academic institutions to streamline faculty operations, research tracking, and administrative workflows.

## Overview

DCERP is a full-stack web application that serves as a centralized platform for managing faculty research activities, academic schedules, publications, and extension programs. The system provides role-based interfaces for administrators and faculty members, enabling efficient collaboration and data management across the department.

## Architecture

### Technology Stack

- **Backend Framework**: Flask 2.3+ (Python)
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: JWT-based authentication with Supabase Auth
- **Cloud Storage**: Cloudinary for media assets
- **Frontend**: Server-side rendered templates with vanilla JavaScript
- **Deployment**: Render platform with automated CI/CD

### Key Components

- **Service Layer**: Modular services for database operations, file management, and external integrations
- **Template Engine**: Jinja2-based server-side rendering with dynamic content loading
- **API Layer**: RESTful endpoints for data operations and real-time updates
- **Scheduler Service**: Background task processing for automated operations

## Core Features

### Faculty Management
- Comprehensive member profiles with academic credentials
- Position tracking and organizational hierarchy
- Profile photo management with cloud storage
- Research interests and specialization tracking

### Research & Publications
- Research project lifecycle management
- Publication tracking with metadata (authors, citations, DOI)
- Public engagement and extension activity logging
- Collaboration tracking across projects

### Academic Scheduling
- Interactive class schedule builder with drag-and-drop interface
- Faculty Schedule Report (FSR) automated generation
- Co-teaching and team-teaching configuration with footnote management
- Subject block allocation and unit load tracking
- Semester-based schedule management with conflict detection

### Extension Programs
- TAP-HSP (Training Assistance Program - Human Resource Scholarship) project tracking
- Community extension activity management
- Event scheduling and participation logging

### News & Events
- Content management system for departmental announcements
- Event calendar with RSVP functionality
- Image gallery integration

### Administrative Dashboard
- Real-time analytics and reporting
- Member activity monitoring
- System-wide configuration management
- Bulk data operations and exports

### CHE (Chemical Engineering Helper)
- AI-powered conversational assistant
- Context-aware responses for departmental queries
- Natural language processing integration

## System Requirements

### Development Environment
- Python 3.9 or higher
- PostgreSQL-compatible database
- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+)

### Production Environment
- Cloud hosting platform (Render, Heroku, AWS)
- Supabase project with PostgreSQL database
- Cloudinary account for media storage
- Environment-specific configuration variables


## Setup Instructions

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd CERP2.0
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure all required variables.

**Critical configurations:**
- Firebase credentials
- Supabase URL and keys
- Cloudinary credentials
- **SMTP Email** (see EMAIL_SETUP_GUIDE.md)
- Groq API key (optional, for CHE AI)

### 3. Set Up Email Verification

📧 **Important!** Follow `EMAIL_SETUP_GUIDE.md` for detailed Gmail SMTP setup:

1. Enable 2FA on Gmail
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Update `.env`:
   ```env
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   ```

### 4. Initialize Database

```bash
python scripts/setup_supabase.py
```

### 5. Create Admin Account

```bash
python scripts/create_admin.py
```

### 6. Run Application

```bash
python app.py
```

Visit: http://localhost:5000

---

## Project Structure

```
CERP2.0/
├── app.py                          # Main Flask application
├── services/                       # Service layer
│   ├── supabase_service.py        # Database operations
│   ├── email_service.py           # Email verification (SMTP)
│   ├── cloudinary_service.py      # Media uploads
│   ├── fsr_generator.py           # FSR Excel generation
│   ├── che_service.py             # AI assistant
│   └── scheduler_service.py       # Background tasks
├── templates/                      # Jinja2 templates
├── static/                         # CSS, JS, images
├── scripts/                        # Setup & utility scripts
└── generated_fsr/                  # FSR exports
```

---

## Key Features

### 🔐 First-Time Login Flow
1. Admin creates faculty account with ID (XXXX-XX format)
2. Faculty receives verification email with 6-digit code
3. Faculty logs in → prompted to change password (optional)
4. Faculty verifies email with code from email
5. Dashboard access granted ✅

### 📊 Faculty Schedule Report (FSR)
- Automated Excel generation
- Co-teaching and team-teaching support
- Footnote management
- Semester-based filtering

### 🤖 CHE AI Assistant
- Powered by Groq API (Llama 3.3 70B)
- Department context awareness
- Conversation history

---

## Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session secret |
| `SUPABASE_URL` | Database endpoint |
| `SUPABASE_SERVICE_KEY` | Database admin key |
| `SMTP_USER` | Gmail for sending emails |
| `SMTP_PASSWORD` | Gmail App Password |
| `CLOUDINARY_CLOUD_NAME` | Media storage |
| `GROQ_API_KEY` | AI assistant |

---

## Security Features

✅ Email verification on first login  
✅ Optional password change flow  
✅ JWT authentication via Supabase  
✅ Gmail App Passwords (not main password)  
✅ Environment variables (not in git)  

---

## Troubleshooting

### 📧 Email not sending?
- Read `EMAIL_SETUP_GUIDE.md`
- Verify App Password setup
- Check terminal for dev mode codes

### 🗄️ Database errors?
- Check Supabase credentials
- Verify database tables initialized
- Check Supabase project status

### 📄 FSR generation issues?
- Install: `pip install openpyxl`
- Verify schedule data exists
- Check terminal logs

---

## License

[Your License Here]

## Support

For issues, open a GitHub issue or contact the development team.
