# 🚀 Deployment Checklist

## Before You Start

### Information You Need:

1. **Firebase Credentials (Service Account JSON)**
   - Location: Firebase Console → Settings → Service Accounts
   - Action: Download JSON file
   - Format: Minify to single line for Render

2. **Environment Variables from .env:**
   - Firebase API Key
   - Firebase Auth Domain
   - Firebase Project ID
   - Firebase Storage Bucket
   - Firebase Messaging Sender ID
   - Firebase App ID
   - Firebase Measurement ID
   - Cloudinary Cloud Name
   - Cloudinary API Key
   - Cloudinary API Secret

---

## Step-by-Step Deployment

### ☐ Step 1: Prepare Firebase Credentials

```bash
# In your project directory
cd c:\Users\PC\Documents\CERP2.0

# Minify firebase-credentials.json
python -c "import json; print(json.dumps(json.load(open('firebase-credentials.json'))))"

# Copy the output - you'll need it for Render!
```

**Save this minified JSON somewhere safe!**

---

### ☐ Step 2: Push to GitHub

```bash
# Initialize git (if first time)
git init
git branch -M main
git remote add origin https://github.com/DarwinSemitara/CerpUp.git

# Add all files
git add .

# Commit
git commit -m "Initial deployment"

# Push to GitHub
git push -u origin main
```

**✅ Check GitHub to verify files are uploaded**

---

### ☐ Step 3: Create Render Account

1. Go to: https://render.com/
2. Sign up with GitHub (recommended)
3. Authorize Render to access your repositories

---

### ☐ Step 4: Create Web Service on Render

1. Click **"New +"** → **"Web Service"**
2. Select **CerpUp** repository
3. Configure:
   - Name: `cerpup`
   - Region: Choose your region
   - Branch: `main`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Instance Type: **Free**

4. Click **"Create Web Service"** (don't deploy yet!)

---

### ☐ Step 5: Add Environment Variables

In Render dashboard, go to **Environment** tab:

#### Add These Variables (one by one):

```
SECRET_KEY = (Auto-generated - keep it)
FIREBASE_API_KEY = AIzaSyBSo793HWIo5mmoBIxvZcFiBk7SbX4XW0A
FIREBASE_AUTH_DOMAIN = cerpup.firebaseapp.com
FIREBASE_PROJECT_ID = cerpup
FIREBASE_STORAGE_BUCKET = cerpup.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID = 457498513053
FIREBASE_APP_ID = 1:457498513053:web:cb7949f3b7bf50c2530e74
FIREBASE_MEASUREMENT_ID = G-RW39NJTS9K
FIREBASE_CREDENTIALS_JSON = {paste your minified JSON here}
CLOUDINARY_CLOUD_NAME = dwswsq1ul
CLOUDINARY_API_KEY = 657265448167474
CLOUDINARY_API_SECRET = 16yX6Y9v1RT3NP21ptEuzV1G8-w
```

**⚠️ IMPORTANT:** 
- `FIREBASE_CREDENTIALS_JSON` must be the MINIFIED JSON (single line, no spaces)
- Double-check all values are correct
- No quotes needed around values

Click **"Save Changes"** after adding all variables

---

### ☐ Step 6: Deploy!

1. Render will automatically start deploying
2. Watch the **Logs** tab for progress
3. Wait 2-5 minutes
4. Look for: `✅ Build successful` and `✅ Deploy live`

---

### ☐ Step 7: Test Your Deployment

1. **Copy your Render URL** (e.g., `https://cerpup.onrender.com`)
2. **Open in browser**
3. **Test these features:**
   - [ ] Landing page loads
   - [ ] Login works
   - [ ] Admin dashboard accessible
   - [ ] Can add schedule blocks
   - [ ] Unit configuration saves
   - [ ] Images upload (Cloudinary)
   - [ ] Data persists (Firestore)

---

### ☐ Step 8: Setup Auto-Deploy

**Already Done!** 🎉

Render automatically watches your GitHub repo. Every time you push:

```bash
git add .
git commit -m "New feature"
git push
```

Render will automatically rebuild and redeploy!

---

## Troubleshooting

### ❌ Build Failed

**Check Render logs for:**
- Missing dependencies → Update `requirements.txt`
- Syntax errors → Fix locally and push again
- Environment variable issues → Verify in Render dashboard

### ❌ Deploy Live but Site Not Loading

**Check:**
1. Render logs for Python errors
2. Environment variables are all set
3. `FIREBASE_CREDENTIALS_JSON` is valid JSON (test locally)
4. Cloudinary credentials are correct

### ❌ Database Not Working

**Check:**
- Firebase credentials are correct
- Firestore is enabled in Firebase Console
- Service account has proper permissions

### ❌ Images Not Uploading

**Check:**
- Cloudinary credentials are correct
- Cloudinary account is active
- API limits not exceeded

---

## Quick Commands

### Deploy Changes:
```bash
git add .
git commit -m "Describe changes"
git push
```

### View Logs:
```bash
# Go to Render Dashboard → Logs tab
# Or use Render CLI (optional)
```

### Rollback:
```bash
# In Render Dashboard:
# Events tab → Previous deploy → "Redeploy"
```

---

## Success Checklist

After deployment, you should have:

- [ ] GitHub repository with all code
- [ ] Render service running
- [ ] All environment variables set
- [ ] Website accessible via Render URL
- [ ] Login/auth working
- [ ] Database operations working
- [ ] Image uploads working
- [ ] Auto-deploy configured
- [ ] No errors in Render logs

---

## Post-Deployment

### Monitor Your App:
- Check Render dashboard daily
- Review logs for errors
- Monitor free tier usage (750 hours/month)

### Update Your App:
1. Make changes locally
2. Test with `flask run`
3. Commit: `git commit -m "..."`
4. Push: `git push`
5. Wait for Render to redeploy
6. Test live site

### Backup Strategy:
- Firebase data auto-backed up
- Cloudinary images stored in cloud
- Git history for code
- Export Firestore data periodically

---

## Need Help?

- Read: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
- Render Docs: https://render.com/docs
- Render Support: https://community.render.com/

---

**🎉 You're ready to deploy!**

Start with Step 1 and work through each checkbox. Take your time and double-check environment variables!
