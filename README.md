# CERP 2.0 - Chemical Engineering Research Portal

A modern web application for managing research, publications, extensions, and schedules for the Chemical Engineering department.

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **File Storage**: Cloudinary
- **Frontend**: HTML, CSS, JavaScript

## Features

- 👥 Member management and profiles
- 📚 Research tracking and management
- 📰 News and events
- 🎓 Extension activities
- 📅 Class scheduling system
- 📊 TAP-HSP project tracking
- 🔐 Role-based access control (Admin/Member)

## Deployment on Render

### Prerequisites

1. A Supabase account with a project set up
2. A Cloudinary account for image uploads
3. A GitHub account

### Environment Variables Required

Add these environment variables in Render dashboard:

```
SECRET_KEY=<your-secret-key>
SUPABASE_URL=<your-supabase-project-url>
SUPABASE_ANON_KEY=<your-supabase-anon-key>
SUPABASE_SERVICE_KEY=<your-supabase-service-role-key>
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
```

### Deployment Steps

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` configuration

3. **Configure Environment Variables**:
   - In Render dashboard, go to your service → "Environment"
   - Add all required environment variables listed above
   - Click "Save Changes"

4. **Deploy**:
   - Render will automatically deploy using the configuration in `render.yaml`
   - Wait for the build and deployment to complete

### Database Setup

Make sure your Supabase database has these tables:
- `users` - Authentication and user management
- `members` - Faculty member profiles
- `research` - Research projects
- `extensions` - Extension activities
- `schedules` - Class schedules
- `news` - News and events
- `engagements` - Public engagement activities
- `tap_projects` - TAP-HSP projects

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd CERP2.0
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements-supabase.txt
   ```

4. **Create `.env` file**:
   ```
   SECRET_KEY=your-dev-secret-key
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-key
   CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
   CLOUDINARY_API_KEY=your-cloudinary-api-key
   CLOUDINARY_API_SECRET=your-cloudinary-api-secret
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   - Open browser to `http://localhost:5000`

### Default Credentials

After setting up, create an admin account using:
```bash
python scripts/create_supabase_user.py
```

## Project Structure

```
CERP2.0/
├── app.py                  # Main application (Supabase)
├── services/               # Service modules
│   ├── supabase_service.py
│   └── cloudinary_service.py
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
├── scripts/                # Utility scripts
├── archive_firebase/       # Old Firebase code (not used)
└── requirements-supabase.txt
```

## Support

For issues or questions, contact the development team.
