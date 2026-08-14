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
