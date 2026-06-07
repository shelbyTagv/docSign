# DocSign Platform - Deployment Checklist

Complete this checklist to successfully deploy your application to production.

## Phase 1: Preparation (5 min)

- [ ] You have a GitHub account with the repository set up
- [ ] You have signed up for: Vercel, Render, Railway
- [ ] You have Gmail account with 2FA enabled (for notifications)
- [ ] You've read the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

## Phase 2: Security Keys (2 min)

- [ ] Run `./deploy.sh` and generate keys:
  - [ ] Copy **FERNET_KEY** to secure location
  - [ ] Copy **INTERNAL_API_KEY** to secure location
- [ ] Store these in a password manager (you'll need them multiple times)

## Phase 3: Database Setup - Railway (3 min)

- [ ] Go to https://railway.app
- [ ] Create New Project
- [ ] Provision PostgreSQL (Free tier)
- [ ] Wait for database to be ready (~1 min)
- [ ] Copy and save these values:
  - [ ] `DB_HOST` - Your PostgreSQL host
  - [ ] `DB_PORT` - Should be 5432
  - [ ] `DB_NAME` - Should be default database name
  - [ ] `DB_USER` - PostgreSQL username
  - [ ] `DB_PASSWORD` - PostgreSQL password

## Phase 4: Backend Deployment - Render (15 min)

### 4.1 Create Auth Service

- [ ] Go to https://render.com
- [ ] Click "New+" → "Web Service"
- [ ] Connect your GitHub repository (shelbyTagv/docSign)
- [ ] Configure:
  - [ ] **Name**: `docsign-auth-service`
  - [ ] **Environment**: Python 3
  - [ ] **Branch**: main
  - [ ] **Build Command**: `pip install -r auth-service/requirements.txt`
  - [ ] **Start Command**: `cd auth-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 app.main:app`
  - [ ] **Region**: Closest to your users
  - [ ] **Plan**: Free
- [ ] Click "Create Web Service"

### 4.2 Add Environment Variables to Auth Service

In Render dashboard, go to Environment and add:

```
PYTHONUNBUFFERED=true
DB_TYPE=postgresql
DB_HOST={copy_from_railway}
DB_PORT={copy_from_railway}
DB_NAME={copy_from_railway}
DB_USER={copy_from_railway}
DB_PASSWORD={copy_from_railway}
SERVICE_PORT=8001
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MASTER_ENCRYPTION_KEY={paste_fernet_key_here}
INTERNAL_API_KEY={paste_api_key_here}
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
NOTIFICATION_SERVICE_URL=https://docsign-notification-service.onrender.com
```

- [ ] Save and wait for deployment (~3-5 min)
- [ ] Check logs for errors
- [ ] Copy the URL: `https://docsign-auth-service.onrender.com`

### 4.3 Create Document Service

- [ ] Repeat 4.1 with:
  - [ ] **Name**: `docsign-document-service`
  - [ ] **Build Command**: `pip install -r document-service/requirements.txt`
  - [ ] **Start Command**: `cd document-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002 app.main:app`

### 4.4 Add Environment Variables to Document Service

```
PYTHONUNBUFFERED=true
DB_TYPE=postgresql
DB_HOST={copy_from_railway}
DB_PORT={copy_from_railway}
DB_NAME={copy_from_railway}
DB_USER={copy_from_railway}
DB_PASSWORD={copy_from_railway}
SERVICE_PORT=8002
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
AUTH_SERVICE_URL=https://docsign-auth-service.onrender.com
NOTIFICATION_SERVICE_URL=https://docsign-notification-service.onrender.com
PDF_STORAGE_PATH=/var/tmp/pdfs
INTERNAL_API_KEY={paste_api_key_here_same_as_auth}
```

- [ ] Save and wait for deployment

### 4.5 Create Notification Service

- [ ] Repeat 4.1 with:
  - [ ] **Name**: `docsign-notification-service`
  - [ ] **Build Command**: `pip install -r notification-service/requirements.txt`
  - [ ] **Start Command**: `cd notification-service && gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8003 app.main:app`

### 4.6 Add Environment Variables to Notification Service

```
PYTHONUNBUFFERED=true
SERVICE_PORT=8003
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER={your_gmail@gmail.com}
SMTP_PASS={app_specific_password_from_gmail}
SMTP_FROM=DocSign Platform <noreply@yourdomain.com>
INTERNAL_API_KEY={paste_api_key_here_same_as_auth}
FRONTEND_URL=http://localhost:3000
ORG_NAME=Your Organization
```

**For Gmail SMTP:**
- [ ] Go to https://myaccount.google.com/apppasswords
- [ ] Select "Mail" and "Custom device"
- [ ] Generate app password
- [ ] Use that as SMTP_PASS

- [ ] Save and wait for deployment

## Phase 5: Frontend Deployment - Vercel (5 min)

- [ ] Go to https://vercel.com
- [ ] Click "Add New" → "Project"
- [ ] Import your GitHub repository (shelbyTagv/docSign)
- [ ] Configure:
  - [ ] **Framework Preset**: React
  - [ ] **Root Directory**: `./frontend`
  - [ ] **Build Command**: `npm run build`
  - [ ] **Output Directory**: `dist`
  - [ ] **Install Command**: `npm install`
- [ ] Click "Deploy"
- [ ] Wait for deployment (~2-3 min)

### 5.1 Add Environment Variables to Frontend

After deployment starts, go to Project Settings → Environment Variables

Add:
```
VITE_API_BASE_URL=http://localhost:3000/api
```

**Note**: For now use relative URL. After you get your Render service URLs, update this to:
```
VITE_API_BASE_URL=https://docsign-document-service.onrender.com/api
```

- [ ] Save environment variables
- [ ] Redeploy frontend (or it will auto-redeploy)
- [ ] Copy the deployment URL (e.g., `https://your-project.vercel.app`)

## Phase 6: Configuration Updates

- [ ] Update CORS_ORIGINS in Render services to your Vercel URL:
  ```
  CORS_ORIGINS=https://your-project.vercel.app
  FRONTEND_URL=https://your-project.vercel.app
  ```
- [ ] Redeploy all Render services (they'll auto-redeploy with env changes)

## Phase 7: Verification (5 min)

- [ ] Test health endpoints:
  ```bash
  curl https://docsign-auth-service.onrender.com/health
  curl https://docsign-document-service.onrender.com/health
  curl https://docsign-notification-service.onrender.com/health
  ```

- [ ] Visit your Vercel URL in browser
- [ ] Can you see the login page? ✓
- [ ] Try creating an account
- [ ] Try logging in
- [ ] Check Render logs for any errors
- [ ] Try sending a test document for signing

## Phase 8: Production Hardening (Optional)

- [ ] Enable custom domain on Vercel
- [ ] Configure SSL/TLS (automatic on all platforms)
- [ ] Set up monitoring alerts in Render
- [ ] Configure backup in Railway
- [ ] Update SMTP settings with production email
- [ ] Test email notifications
- [ ] Review security settings

## Troubleshooting

### Services won't start
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure database credentials are correct
- Check that Python version and dependencies are compatible

### Database connection errors
- Verify Railway PostgreSQL is running
- Test connection: `psql postgresql://{user}:{pass}@{host}:{port}/{db}`
- Ensure IP allowlist includes Render services (usually auto-configured)

### CORS errors in browser
- Verify CORS_ORIGINS env var matches your Vercel URL exactly
- Restart services after updating env vars

### Email not sending
- Verify SMTP credentials are correct
- Ensure Gmail account has 2FA and app-specific password
- Check notification service logs

### Frontend not loading API
- Verify VITE_API_BASE_URL is set correctly
- Check if backend services are running (health endpoints)
- Look at browser console for errors

## Success Criteria

When complete, you should be able to:

- [ ] Access your frontend at `https://your-project.vercel.app`
- [ ] Create a new user account
- [ ] Log in with those credentials
- [ ] Create and view documents
- [ ] Receive system emails (after SMTP config)
- [ ] Upload and download files
- [ ] All services showing green/healthy status

---

**Got stuck?** 
1. Check the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions
2. Review service logs in the respective dashboards
3. Verify all environment variables are set correctly
4. Ensure all services have had time to start (1-2 minutes)

**Congratulations on your deployment!** 🎉
