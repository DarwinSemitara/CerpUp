# CERP 2.0 - Technology Stack & Resources

## Backend Technologies

### Core Framework
- **Flask 3.0.0** - Python web framework for building the application
- **Python 3.11.9** - Programming language runtime
- **Gunicorn 21.2.0** - WSGI HTTP Server for production deployment

### Database & Authentication
- **Supabase 2.7.4** - Backend-as-a-Service (BaaS) for:
  - PostgreSQL database hosting
  - User authentication & authorization
  - Real-time subscriptions
  - Row-level security
- **Supabase Python Client** - Official Python SDK for Supabase integration

### APIs & External Services
- **Cloudinary 1.40.0** - Cloud-based image storage and transformation
  - Member photo uploads
  - Image optimization and delivery
- **Groq API 0.11.0** - AI/LLM service for CHE Assistant
  - Model: Llama 3.3 70B
  - Natural language processing for CERP queries
- **Resend API** - Email delivery service (via requests library)
- **httpx 0.27.0** - Modern HTTP client for async operations

### Security & Authentication
- **PyJWT 2.8.0** - JSON Web Token encoding/decoding
- **Flask-CORS 4.0.0** - Cross-Origin Resource Sharing support
- **python-dotenv 1.0.0** - Environment variable management

### Data Processing
- **openpyxl 3.1.5** - Excel file generation for Faculty Service Records (FSR)
- **requests ≥2.31.0** - HTTP library for API integrations

---

## Frontend Technologies

### Core Libraries
- **HTML5** - Markup structure
- **CSS3** - Styling and animations
- **JavaScript (ES6+)** - Client-side interactivity

### UI Framework & Styling
- **Tailwind CSS** (via CDN) - Utility-first CSS framework
- **Google Fonts - Inter** - Typography (weights: 300, 400, 500, 600, 700)

### Data Visualization
- **Chart.js 4.4.0** - JavaScript charting library for:
  - Publications line charts
  - TAP-HSP progress pie charts
  - Research/Extension statistics
  - Year-over-year comparisons

### Frontend SDK
- **Supabase JavaScript SDK 2.x** (via CDN) - Client-side authentication and database queries



## Development Tools & Platforms

### Version Control
- **Git** - Source control management
- **GitHub** - Repository hosting (implied from `.git` directory)

### IDE/Editor
- **Visual Studio Code** - Development environment (`.vscode` configuration present)


### Deployment Platform
- **Render.com** - Cloud platform for web service hosting
  - Region: Oregon
  - Plan: Free tier
  - Auto-deployment from Git

**Technologies**:
- Flask (BSD License)
- Supabase (Apache License 2.0)
- Chart.js (MIT License)
- Cloudinary (Commercial Service)
- Groq (Commercial API Service)
- All other open-source dependencies as per their respective licenses

---

**Last Updated**: January 2025  
**Version**: 2.0  
**Python Version**: 3.11.9  
**Flask Version**: 3.0.0
