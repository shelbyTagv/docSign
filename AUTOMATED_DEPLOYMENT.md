# 🚀 DocSign - Complete Automated Deployment Guide

**You asked for everything automated. Here's how to get live URLs in the next 30-45 minutes.**

---

## **📋 What You Need (Before Starting)**

✅ GitHub repository: https://github.com/shelbyTagv/docSign.git  
✅ Gmail account with app password  
✅ That's it! (We'll get free tier accounts)

---

## **⚡ FASTEST PATH: 3 Commands to Deploy**

### **Step 1: Gather Your Credentials (5 minutes)**

```bash
cd ~/Desktop/docSignGithub
chmod +x gather_tokens.sh
./gather_tokens.sh
```

This will ask you for:
- **GitHub Personal Access Token** - [Generate here](https://github.com/settings/tokens)
- **Vercel API Token** - [Generate here](https://vercel.com/account/tokens)
- **Render API Key** - [Generate here](https://dashboard.render.com/account/api-tokens)
- **Railway API Token** - [Generate here](https://railway.app/account/tokens)
- **Gmail Email & App Password** - [Generate here](https://myaccount.google.com/apppasswords)

**Saves everything securely to:** `~/.docsign_deploy_creds`

### **Step 2: Run Complete Deployment (25-35 minutes)**

```bash
source ~/.docsign_deploy_creds
python3 deploy_auto.py
```

Or with error handling:
```bash
./deploy_complete.sh
```

### **Step 3: Get Your Live URLs** ✨

The script creates `DEPLOYMENT_URLS_LIVE.md` with:
```
Frontend:         https://your-vercel-domain.vercel.app
Auth Service:     https://docsign-auth-service.onrender.com
Document Service: https://docsign-document-service.onrender.com
Notification:     https://docsign-notification-service.onrender.com
```

---

## **🎯 What Happens Automatically**

### ✅ Fully Automated:
- Code committed & pushed to GitHub
- Environment variables configured
- Health checks generated
- Credentials validated
- Deployment URLs documented

### ⏳ Semi-Automated (Minimal clicks):
- **Railway PostgreSQL** - API creates project, you click "Provision PostgreSQL"
- **Render Services** - Configuration prepared, you click "New Web Service" 3x
- **Vercel Frontend** - Auto-deploys if you use Vercel CLI

### 📖 Manual Steps Required:

#### Railway (2 minutes):
1. Go to https://railway.app
2. Click your new "DocSign" project
3. Click "Create New" → "PostgreSQL"
4. Copy connection details
5. Paste into Render service configs

#### Render (10-15 minutes):
1. Go to https://render.com
2. Click "New+" → "Web Service"
3. For each service (auth, document, notification):
   - Connect your GitHub repo
   - Paste provided build/start commands
   - Add environment variables
   - Deploy

**Script provides all configs and commands - just copy/paste!**

#### Vercel (5 minutes):
1. Go to https://vercel.com
2. Click "Add New" → "Project"
3. Import GitHub repo
4. Select Framework: React
5. Set Root: `./frontend`
6. Deploy

**Or let Python script do it automatically with Vercel CLI:**
```bash
npm install -g vercel
source ~/.docsign_deploy_creds
python3 deploy_auto.py
```

---

## **📊 Timeline**

```
gather_tokens.sh          →   5 min  (You enter credentials)
                               ↓
deploy_auto.py            →  15 min  (Code pushed, configs created)
                               ↓
Manual Railway setup       →   3 min  (Click 2 buttons)
                               ↓
Manual Render setup        →  10 min  (Create 3 services)
                               ↓
Manual Vercel setup        →   5 min  (Import repo, deploy)
                               ↓
                          = 38 min TOTAL
                               ↓
YOUR LIVE URLs             →  ✨ LIVE ON INTERNET ✨
```

---

## **🔑 Getting Required Credentials**

### 1. GitHub Personal Access Token
```
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "docsign-deploy"
4. Select scopes: repo, workflow
5. Copy and save token
```

### 2. Vercel API Token
```
1. Go to: https://vercel.com/account/tokens
2. Click "Create"
3. Name: "docsign-deploy"
4. Scope: Full Account
5. Copy token
```

### 3. Render API Key
```
1. Go to: https://dashboard.render.com/account/api-tokens
2. Click "Create New API Key"
3. Copy key
```

### 4. Railway API Token
```
1. Go to: https://railway.app/account/tokens
2. Click "Create New"
3. Copy token
```

### 5. Gmail App Password
```
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Go to: https://myaccount.google.com/apppasswords
3. Select "Mail" and "Custom device"
4. Copy app-specific password
```

---

## **💻 Running the Scripts**

### Option A: Complete Automation (Recommended)
```bash
cd ~/Desktop/docSignGithub

# 1. Gather credentials
./gather_tokens.sh

# 2. Load credentials
source ~/.docsign_deploy_creds

# 3. Run deployment
python3 deploy_auto.py

# 4. Check DEPLOYMENT_URLS_LIVE.md for your URLs
cat DEPLOYMENT_URLS_LIVE.md
```

### Option B: Step by Step
```bash
# Step 1: Gather tokens
./gather_tokens.sh

# Step 2: Push code and prepare
./automated_deploy.sh

# Step 3: Manual platform setup
# Follow prompts for Railway, Render, Vercel
```

### Option C: Helper Script
```bash
./deploy_complete.sh
# Will guide you through everything
```

---

## **🧪 Testing Your Deployment**

Once everything is live, test with:

```bash
# Get your URLs
cat DEPLOYMENT_URLS_LIVE.md

# Test Frontend
curl https://your-vercel-domain.vercel.app

# Test Backend Services
curl https://docsign-auth-service.onrender.com/health
curl https://docsign-document-service.onrender.com/health
curl https://docsign-notification-service.onrender.com/health

# If all return 200 OK, you're good!
```

Then:
1. Open frontend in browser
2. Sign up for new account
3. Set up 2FA
4. Create a test document
5. Try signing it

---

## **❌ Troubleshooting**

### "Command not found: python3"
```bash
# Install Python
sudo apt-get install python3

# Or use Python from another location
which python
```

### "curl: command not found"
```bash
# Install curl
sudo apt-get install curl
```

### "git push failed"
```bash
# Make sure you're in the repo
cd ~/Desktop/docSignGithub

# Set up git config if needed
git config user.name "Your Name"
git config user.email "your@email.com"

# Try again
git push origin main
```

### "API token invalid"
```bash
# Check token was copied correctly
# Regenerate token on platform if needed
# Verify no extra spaces/newlines
```

### "Services not starting"
```bash
# Free tier services take 1-2 minutes to start
# Check logs in service dashboard
# Verify all environment variables are set
```

### "Database connection error"
```bash
# Ensure PostgreSQL provisioned on Railway
# Double-check connection credentials
# Wait for Railway database to be ready
```

---

## **📍 What You'll Get**

After completion, you'll have:

✅ **Live Frontend**
```
https://your-vercel-domain.vercel.app
- Fully functional React app
- Live on the internet
- Connected to backend
```

✅ **Live Backend Services**
```
https://docsign-auth-service.onrender.com
https://docsign-document-service.onrender.com
https://docsign-notification-service.onrender.com
```

✅ **Live Database**
```
PostgreSQL on Railway
- Accessible from services
- Automatically backed up
- Scalable on demand
```

✅ **Email Notifications**
```
Gmail SMTP configured
- Welcome emails
- Document updates
- Signature notifications
```

---

## **📋 Checklist Before Running**

- [ ] Cloned repository to `~/Desktop/docSignGithub`
- [ ] Have GitHub account
- [ ] Have Vercel account (or will create free)
- [ ] Have Render account (or will create free)
- [ ] Have Railway account (or will create free)
- [ ] Have Gmail account with 2FA enabled
- [ ] All 5 API tokens ready to paste

**If yes to all above:** You're ready to deploy!

---

## **🚀 START HERE**

```bash
cd ~/Desktop/docSignGithub
./gather_tokens.sh
```

Then follow the prompts!

---

## **📞 Support**

If you get stuck:
1. Check `DEPLOYMENT_URLS_LIVE.md` for troubleshooting
2. Check service logs in platform dashboards
3. Run health checks: `curl {service-url}/health`
4. Verify environment variables in each platform
5. Check DEPLOYMENT_GUIDE.md for detailed info

---

## **🎉 What's Next After Going Live**

Once deployed:

1. **Add custom domain** (Vercel supports free domains)
2. **Enable SSL/TLS** (automatic on all platforms)
3. **Set up monitoring** (Render has built-in alerts)
4. **Configure backups** (Railway auto-backups)
5. **Test user workflows** (full end-to-end)
6. **Invite test users** (get feedback)
7. **Monitor logs** (catch any issues)

---

**Ready to deploy? Run `./gather_tokens.sh` now!**
