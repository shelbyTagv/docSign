# 🎯 DocSign - YOUR EXACT NEXT STEPS TO GET LIVE URLs

**Everything is ready. Here's exactly what you need to do (no guessing).**

---

## **⚡ THE FAST PATH (30-45 minutes)**

### **STEP 1️⃣: RUN ONE COMMAND** (2 minutes)

Open terminal and run:

```bash
cd ~/Desktop/docSignGithub
chmod +x gather_tokens.sh deploy_auto.py deploy_now.sh
./gather_tokens.sh
```

**What you'll do:**
1. Answer prompts to paste 5 API tokens (copy/paste from browser tabs)
2. Enter your Gmail email
3. Everything saves to `~/.docsign_deploy_creds`

**You'll get from this:**
- ✅ GitHub token pasted
- ✅ Vercel token pasted
- ✅ Render token pasted
- ✅ Railway token pasted
- ✅ Gmail app password pasted
- ✅ Automatic security keys generated

### **STEP 2️⃣: RUN DEPLOYMENT** (15-20 minutes)

```bash
source ~/.docsign_deploy_creds
python3 deploy_auto.py
```

**What happens automatically:**
- ✅ Code pushed to GitHub
- ✅ Configurations generated
- ✅ Railway project created
- ✅ Render service configs prepared
- ✅ Vercel frontend deployed (if CLI installed)
- ✅ File `DEPLOYMENT_URLS_LIVE.md` created

**At end, you'll see:**
```
✅ DEPLOYMENT COMPLETE
See DEPLOYMENT_URLS_LIVE.md for URLs
```

### **STEP 3️⃣: MANUAL PLATFORM SETUP** (15-20 minutes)

Now you do the easy clicks on 3 platforms (script gives you exactly what to paste):

#### **🟦 Railway (5 minutes) - Database**

1. Go to: https://railway.app/dashboard
2. Find your "DocSign" project (script created it)
3. Click "Create New" → "PostgreSQL"
4. Wait for it to initialize
5. Copy the connection details shown in Railway
6. **Keep this tab open - you'll need it for Render**

#### **🔴 Render (12 minutes) - Backend Services**

For EACH of these 3 services:

**SERVICE 1: Auth Service**
1. Go to: https://render.com/dashboard
2. Click "New+" → "Web Service"
3. Select your GitHub repo: `shelbyTagv/docSign`
4. **Name:** `docsign-auth-service`
5. **Environment:** Python 3
6. **Branch:** main
7. **Build Command:** (copy from terminal output below)
8. **Start Command:** (copy from terminal output below)
9. **Add Environment Variables:** (copy from terminal output below)
10. Click "Create Web Service"
11. **SAVE THE URL** - it will show `https://docsign-auth-service.onrender.com`

**Get build/start commands from:**
```bash
# Run this in terminal:
echo "=== AUTH SERVICE ===" && \
echo "Build: pip install -r auth-service/requirements.txt" && \
echo "Start: cd auth-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 app.main:app"
```

Copy these values into Render.

**SERVICE 2 & 3: Repeat for document-service and notification-service**

Use these commands:
```bash
# Document Service
echo "=== DOCUMENT SERVICE ===" && \
echo "Build: pip install -r document-service/requirements.txt" && \
echo "Start: cd document-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002 app.main:app"

# Notification Service
echo "=== NOTIFICATION SERVICE ===" && \
echo "Build: pip install -r notification-service/requirements.txt" && \
echo "Start: cd notification-service && gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8003 app.main:app"
```

**Environment Variables for ALL Render Services:**

```
PYTHONUNBUFFERED=true
DB_TYPE=postgresql
DB_HOST={from Railway connection}
DB_PORT={from Railway connection}
DB_NAME={from Railway connection}
DB_USER={from Railway connection}
DB_PASSWORD={from Railway connection}
FERNET_KEY={from ~/.docsign_deploy_creds}
INTERNAL_API_KEY={from ~/.docsign_deploy_creds}
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
```

**For Notification Service ONLY, add:**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER={your Gmail}
SMTP_PASS={Gmail app password}
SMTP_FROM=DocSign Platform <noreply@yourdomain.com>
```

#### **🔵 Vercel (5 minutes) - Frontend**

1. Go to: https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Click "Import Git Repository"
4. Search: `shelbyTagv/docSign`
5. Select it
6. **Framework Preset:** React
7. **Root Directory:** `./frontend`
8. Click "Deploy"
9. **SAVE THE URL** - it will show something like `https://docsign-abc123.vercel.app`

### **STEP 4️⃣: TEST & VERIFY** (5 minutes)

Once all 3 platforms show "Deployment Successful":

```bash
# Test your backend services
curl https://docsign-auth-service.onrender.com/health
curl https://docsign-document-service.onrender.com/health
curl https://docsign-notification-service.onrender.com/health

# All should return: {"status":"ok"}
```

Visit your Vercel URL in browser. You should see:
- ✅ Login page loads
- ✅ Can create account
- ✅ Can log in
- ✅ Can see dashboard

---

## **📍 YOUR LIVE URLS (After Above Steps)**

Once complete, you'll have:

```
FRONTEND
  URL: https://docsign-abc123.vercel.app
  
BACKEND SERVICES
  Auth:         https://docsign-auth-service.onrender.com
  Documents:    https://docsign-document-service.onrender.com
  Notifications: https://docsign-notification-service.onrender.com
  
DATABASE
  PostgreSQL on Railway (accessible only from Render)
```

---

## **🔑 GET YOUR 5 TOKENS IN 10 MINUTES**

### Token #1: GitHub Personal Access Token
1. Go: https://github.com/settings/tokens
2. Click: "Generate new token (classic)"
3. Name: `docsign-deploy`
4. Check: `repo` and `workflow`
5. Generate & Copy

### Token #2: Vercel API Token
1. Go: https://vercel.com/account/tokens
2. Click: "Create"
3. Name: `docsign-deploy`
4. Scope: `Full Account`
5. Copy

### Token #3: Render API Key
1. Go: https://dashboard.render.com/account/api-tokens
2. Click: "Create New API Key"
3. Copy

### Token #4: Railway API Token
1. Go: https://railway.app/account/tokens
2. Click: "Create New"
3. Copy

### Token #5: Gmail App Password
1. Go: https://myaccount.google.com/security
2. Enable 2-Step Verification if not done
3. Go: https://myaccount.google.com/apppasswords
4. Select: "Mail" and "Custom device"
5. Copy

---

## **❓ FAQ - QUICK ANSWERS**

**Q: Will this really take 30-45 minutes?**
A: Yes. 10 min gathering tokens + 10 min running script + 15 min manual clicks = 35 min

**Q: Do I need to code anything?**
A: No. Everything is already written. Just run scripts and paste configs.

**Q: Will it really be on the internet?**
A: 100% yes. Real live URLs at real domains.

**Q: How much will it cost?**
A: $0-5/month. Free tier on Vercel & Render, $5/month on Railway (after free credit)

**Q: What if I get stuck?**
A: Check `DEPLOYMENT_URLS_LIVE.md` for troubleshooting

**Q: Can I redeploy/update later?**
A: Yes. Just push to GitHub and all platforms auto-update

---

## **✅ CHECKLIST - START HERE**

Before you begin:

- [ ] GitHub account exists and repo is pushed
- [ ] Gmail account exists with 2FA enabled
- [ ] You have terminal/bash open
- [ ] You're in `~/Desktop/docSignGithub` directory
- [ ] Internet connection is stable

**If yes, you're ready!**

---

## **🚀 RUN THESE COMMANDS NOW**

Copy/paste these exactly:

```bash
# Navigate to project
cd ~/Desktop/docSignGithub

# Make scripts executable
chmod +x gather_tokens.sh deploy_auto.py deploy_now.sh

# Gather your credentials (you'll paste 5 tokens)
./gather_tokens.sh

# Load credentials
source ~/.docsign_deploy_creds

# Run deployment
python3 deploy_auto.py

# See your configuration
cat DEPLOYMENT_URLS_LIVE.md
```

---

## **📞 REFERENCE**

If you forget where to go:

| What | Where | Time |
|------|-------|------|
| Get GitHub token | https://github.com/settings/tokens | 1 min |
| Get Vercel token | https://vercel.com/account/tokens | 1 min |
| Get Render key | https://dashboard.render.com/account/api-tokens | 1 min |
| Get Railway token | https://railway.app/account/tokens | 1 min |
| Get Gmail password | https://myaccount.google.com/apppasswords | 1 min |
| Deploy to Railway | https://railway.app/dashboard | 5 min |
| Deploy to Render | https://render.com/dashboard | 12 min |
| Deploy to Vercel | https://vercel.com/dashboard | 5 min |

---

## **🎉 WHEN YOU'RE DONE**

You'll have:
- ✅ Live frontend URL (Vercel)
- ✅ Live API services (Render)
- ✅ Live database (Railway)
- ✅ Automated email notifications
- ✅ Full document signing system
- ✅ All accessible on the internet

**Congratulations! Your app is live!** 🎊

---

**Start now:**
```bash
cd ~/Desktop/docSignGithub && ./gather_tokens.sh
```
