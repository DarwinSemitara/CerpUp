# 📧 Email Setup Guide - Gmail SMTP

This guide will help you set up Gmail to send verification emails from your CERP application.

---

## Prerequisites

- A Gmail account (darwinjeffsemitara@gmail.com or any Gmail)
- Google Account with 2-Factor Authentication enabled

---

## Step-by-Step Setup

### Step 1: Enable 2-Factor Authentication

1. Go to: **https://myaccount.google.com/security**
2. Scroll down to **"How you sign in to Google"**
3. Click **"2-Step Verification"**
4. Follow the prompts to enable it (usually via phone number)

### Step 2: Generate App Password

1. After enabling 2FA, go to: **https://myaccount.google.com/apppasswords**
   - Or Google: "google app passwords"
   
2. You may need to sign in again

3. In the **"Select app"** dropdown:
   - Choose **"Mail"**
   
4. In the **"Select device"** dropdown:
   - Choose **"Other (Custom name)"**
   - Type: **"CERP Application"**
   
5. Click **"Generate"**

6. Google will show you a **16-character password** (with spaces)
   - Example: `abcd efgh ijkl mnop`
   - Copy this password (you can remove spaces)

### Step 3: Update Your .env File

Open `c:\Users\PC\Documents\CERP2.0\.env` and update these lines:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=darwinjeffsemitara@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_NAME=CERP System
```

**Important:** 
- Replace `abcdefghijklmnop` with your actual 16-character app password
- Remove all spaces from the app password
- Use your Gmail address in `SMTP_USER`

### Step 4: Restart Your Application

```bash
python app.py
```

### Step 5: Test It!

1. As admin, create a new faculty account
2. Check your terminal - you'll see the verification code
3. Check the recipient's email - they should receive a beautiful verification email!

---

## Troubleshooting

### "SMTP authentication failed"
- Double-check your app password (no spaces, all lowercase)
- Make sure 2FA is enabled
- Try generating a new app password

### "SMTPException: Server not connected"
- Check your internet connection
- Verify `SMTP_HOST=smtp.gmail.com` and `SMTP_PORT=587`

### "Username and Password not accepted"
- You're using your regular Gmail password instead of the app password
- Generate a new app password from the link above

### Emails go to spam
- Normal for the first few emails
- Ask recipients to mark as "Not Spam"
- After a few emails, Gmail will trust your app

### "Less secure app access"
- This is outdated - ignore it
- App passwords work without enabling "less secure apps"

---

## Development Mode

If you don't configure SMTP (leave `SMTP_USER` and `SMTP_PASSWORD` empty), the system will:

✅ Print verification codes to the terminal (with big banner)
✅ Log all email details
✅ Still work perfectly for testing

This is great for development!

---

## Security Notes

✅ **App passwords are secure:**
   - They only work for the specific app
   - You can revoke them anytime
   - They don't expose your main Gmail password

✅ **Never commit .env to git:**
   - Already in `.gitignore`
   - Never share your app password

✅ **Rotating passwords:**
   - Revoke old app passwords: https://myaccount.google.com/apppasswords
   - Generate new ones as needed

---

## Rate Limits

Gmail SMTP has these limits:
- **500 emails per day** (free Gmail accounts)
- **2000 emails per day** (Google Workspace accounts)
- **100 emails per hour** (burst limit)

For CERP, this is more than enough! 🎉

---

## Alternative Email Providers

If you prefer not to use Gmail:

### Outlook/Hotmail
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-outlook-password
```

### SendGrid (Professional)
- Free tier: 100 emails/day
- Setup: https://sendgrid.com/
- Requires API key instead of SMTP

### AWS SES (Enterprise)
- Very cheap for high volume
- Requires AWS account setup

---

## Quick Reference

| Setting | Value |
|---------|-------|
| SMTP Host | smtp.gmail.com |
| SMTP Port | 587 |
| Security | STARTTLS |
| Auth | App Password (not regular password) |
| Rate Limit | 500/day (free), 2000/day (workspace) |

---

## Testing Commands

Test email sending manually (Python console):

```python
from services.email_service import send_verification_email

# Send test email
success, message = send_verification_email(
    email="test@example.com",
    name="Test User",
    code="123456"
)

print(f"Success: {success}")
print(f"Message: {message}")
```

---

🎉 **That's it! Your email system is ready to go!**

For questions, check the console logs or Flask terminal for detailed error messages.
