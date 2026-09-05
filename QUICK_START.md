# 🚀 CERP Quick Start Guide

## Current Setup Status

✅ **Email System**: Reverted to Gmail SMTP  
✅ **Project Cleaned**: All test files removed  
✅ **Verification Flow**: Working with email codes  

---

## For Development (Right Now)

### Option 1: Use Without Real Emails (Easiest)

Just run the app - verification codes appear in terminal!

```bash
python app.py
```

When creating accounts:
1. Check Flask terminal for verification code banner
2. Copy the 6-digit code
3. Enter it in the verification modal

**No email setup needed!** Perfect for testing.

---

### Option 2: Set Up Real Gmail Emails (15 minutes)

Follow **`EMAIL_SETUP_GUIDE.md`** for complete instructions.

**Quick version:**

1. **Enable 2FA on Gmail:**
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Get App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" → "Other" → Type "CERP"
   - Copy the 16-character password

3. **Update `.env`:**
   ```env
   SMTP_USER=darwinjeffsemitara@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   ```
   (Replace with your actual 16-char password, no spaces)

4. **Restart Flask:**
   ```bash
   python app.py
   ```

Now emails will actually send! 📧

---

## Files Removed (Cleanup)

Deleted all test/debug files:
- ❌ `FIX_LOGIN_ISSUE.md`
- ❌ `GA_Guide.md`
- ❌ `RESEND_SETUP.md`
- ❌ `DISABLE_EMAIL_CONFIRMATION.md`
- ❌ `TEST_VERIFICATION.md`
- ❌ `SUPABASE_EMAIL_SETTINGS.md`
- ❌ `SECURITY_ANALYSIS.md`
- ❌ `VERIFICATION_WORKING.md`
- ❌ `add_first_login_column.sql`
- ❌ `add_system_conversation_columns.sql`
- ❌ `create_calendar_and_todo_tables.sql`
- ❌ `check_duplicates.py`
- ❌ `fix_duplicates.py`
- ❌ `check_fsr_structure.py`
- ❌ `DEEP_DEBUG_INSTRUCTIONS.txt`

**Only production-ready files remain!** ✨

---

## Project Files (Current)

```
CERP2.0/
├── 📄 Core Application
│   ├── app.py                      # Main Flask app
│   ├── requirements.txt            # Dependencies
│   └── runtime.txt                 # Python version
│
├── 📁 Services
│   ├── email_service.py            # Gmail SMTP (NEW!)
│   ├── supabase_service.py         # Database
│   ├── cloudinary_service.py       # Media uploads
│   ├── fsr_generator.py            # Excel reports
│   ├── che_service.py              # AI assistant
│   └── scheduler_service.py        # Background tasks
│
├── 📁 Frontend
│   ├── templates/                  # HTML templates
│   └── static/                     # CSS, JS, images
│
├── 📁 Scripts
│   ├── setup_supabase.py           # Database init
│   ├── create_admin.py             # Admin account
│   └── backup_data.py              # Data backup
│
├── 📁 Configuration
│   ├── .env                        # Your secrets (not in git)
│   ├── .env.example                # Template
│   └── render.yaml                 # Deployment config
│
└── 📚 Documentation
    ├── README.md                   # Full docs
    ├── EMAIL_SETUP_GUIDE.md        # Gmail setup
    └── QUICK_START.md              # This file!
```

---

## Testing the Verification Flow

### 1. Start Flask
```bash
python app.py
```

### 2. Login as Admin
- Use your admin credentials
- Go to "Manage" page

### 3. Create Faculty Account
- Click member → "Create Account"
- Enter email and ID (e.g., `0123-01`)
- **Check terminal** for verification code banner

### 4. Login as Faculty
- Use ID as username (e.g., `0123-01`)
- Password change modal appears
- Skip or change password

### 5. Verify Email
- Verification modal blocks dashboard
- Enter 6-digit code from terminal (or email if SMTP configured)
- Click "Verify Code"

### 6. Access Dashboard ✅
- Background unblurs
- Full dashboard access granted!

---

## Environment Variables

Required in `.env`:

```env
# Flask
SECRET_KEY=your-secret-key

# Firebase (for auth)
FIREBASE_API_KEY=...
FIREBASE_PROJECT_ID=...
# (see .env.example for all)

# Supabase (database)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Cloudinary (media)
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# SMTP Email (optional for dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=CERP System

# Groq AI (optional)
GROQ_API_KEY=gsk_...
```

---

## Common Issues

### 🔴 "Verification code not found"
- Code expired (15 minutes)
- Click "Resend Code" to get a new one

### 🔴 "SMTP authentication failed"
- Using regular Gmail password instead of App Password
- Generate App Password: https://myaccount.google.com/apppasswords

### 🔴 Popup not showing
- Check browser console (F12)
- Verify `first_login=true` in database:
  ```sql
  UPDATE users SET first_login = true WHERE email = 'test@example.com';
  ```

### 🔴 Email not received
- Check spam folder
- Verify SMTP credentials in `.env`
- Check terminal - code is always printed there!

---

## Next Steps

1. ✅ **Test verification flow** (use terminal codes)
2. ✅ **Set up Gmail SMTP** (follow EMAIL_SETUP_GUIDE.md)
3. ✅ **Create faculty accounts** for your team
4. ✅ **Configure deployment** (Render, AWS, etc.)

---

## Need Help?

- **Email setup**: Read `EMAIL_SETUP_GUIDE.md`
- **Full documentation**: Read `README.md`
- **API details**: Check inline comments in `app.py`
- **Service info**: Look at `services/*.py` files

---

🎉 **Everything is clean and ready to go!**

Your CERP system is production-ready with:
- ✅ Working email verification
- ✅ Clean codebase (no test files)
- ✅ Gmail SMTP integration
- ✅ Development mode fallback
- ✅ Comprehensive documentation

Happy coding! 🚀
