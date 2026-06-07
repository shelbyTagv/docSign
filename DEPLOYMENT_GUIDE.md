# DocSign Platform - Deployment Guide

## Overview
This guide walks you through deploying the DocSign system to production using:
- **Frontend**: Vercel (free tier)
- **Backend Services**: Render (free tier)
- **Database**: Railway PostgreSQL (free tier)

## Prerequisites
1. GitHub repository with your code: https://github.com/shelbyTagv/docSign.git
2. Accounts on: [Vercel](https://vercel.com), [Render](https://render.com), [Railway](https://railway.app)
3. Environment variables configured

## Step 1: Prepare Your Repository

### 1.1 Push to GitHub
```bash
cd ~/Desktop/docSignGithub
git add .
git commit -m "Update for cloud deployment: PostgreSQL support, Vercel/Render configs"
git push origin main
```

### 1.2 Update Frontend API Base URL
Edit `frontend/src/api/api.js` to use environment variable:
```javascript
const api = axios.create({
  baseURL: process.env.VITE_API_BASE_URL || "/api",
  timeout: 30000,
  // ... rest of config
});
```

Edit `frontend/vite.config.js`:
```javascript
export default defineConfig({
  // ... other config
  define: {
    'process.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL || 'http://localhost/api'),
  },
})
```

## Step 2: Set Up PostgreSQL on Railway

### 2.1 Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Provision PostgreSQL"
3. Wait for database to be ready

### 2.2 Note Database Credentials
From Railway dashboard, copy:
- Host
- Port
- Database name
- Username
- Password

### 2.3 Initialize Database Schema
You'll need to run the PostgreSQL migration. For now, keep the MySQL `init.sql` as reference - it will be auto-migrated when services first connect.

## Step 3: Deploy Backend Services on Render

### 3.1 Create Auth Service
1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `docsign-auth-service`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r auth-service/requirements.txt`
   - **Start Command**: 
     ```
     cd auth-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 app.main:app
     ```
   - **Region**: Pick closest to you

### 3.2 Add Environment Variables for Auth Service
Add these in Render dashboard under "Environment":

```
PYTHONUNBUFFERED=true
DB_TYPE=postgresql
DB_HOST={railway_host}
DB_PORT=5432
DB_NAME=docsign
DB_USER={railway_user}
DB_PASSWORD={railway_password}
SERVICE_PORT=8001
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MASTER_ENCRYPTION_KEY={generate_fernet_key}
INTERNAL_API_KEY={secure_random_key}
CORS_ORIGINS=https://your-vercel-domain.vercel.app
FRONTEND_URL=https://your-vercel-domain.vercel.app
NOTIFICATION_SERVICE_URL=https://docsign-notification-service.onrender.com
```

**Generate secure keys**:
```bash
# Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# API key (generate a strong random string)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.3 Create Document Service
1. Repeat Step 3.1, but:
   - **Name**: `docsign-document-service`
   - **Build/Start Commands**: Use paths for `document-service/`
   - **Start Command**: 
     ```
     cd document-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002 app.main:app
     ```

### 3.4 Add Environment Variables for Document Service
```
PYTHONUNBUFFERED=true
DB_TYPE=postgresql
DB_HOST={railway_host}
DB_PORT=5432
DB_NAME=docsign
DB_USER={railway_user}
DB_PASSWORD={railway_password}
SERVICE_PORT=8002
CORS_ORIGINS=https://your-vercel-domain.vercel.app
FRONTEND_URL=https://your-vercel-domain.vercel.app
AUTH_SERVICE_URL=https://docsign-auth-service.onrender.com
NOTIFICATION_SERVICE_URL=https://docsign-notification-service.onrender.com
PDF_STORAGE_PATH=/var/tmp/pdfs
INTERNAL_API_KEY={same_as_auth_service}
```

### 3.5 Create Notification Service
1. Repeat Step 3.1, but:
   - **Name**: `docsign-notification-service`
   - **Build/Start Commands**: Use paths for `notification-service/`
   - **Start Command**: 
     ```
     cd notification-service && gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8003 app.main:app
     ```

### 3.6 Add Environment Variables for Notification Service
```
PYTHONUNBUFFERED=true
SERVICE_PORT=8003
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-specific-password
SMTP_FROM=DocSign Platform <noreply@yourdomain.com>
INTERNAL_API_KEY={same_as_auth_service}
FRONTEND_URL=https://your-vercel-domain.vercel.app
ORG_NAME=Your Organization
```

**For Gmail**:
- Enable 2FA on your Gmail account
- Generate an [App Password](https://myaccount.google.com/apppasswords)
- Use that as `SMTP_PASS`

## Step 4: Deploy Frontend on Vercel

### 4.1 Import Project
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Select your GitHub repository
4. Configure:
   - **Framework**: React
   - **Root Directory**: `./frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 4.2 Add Environment Variables
In Vercel dashboard, add under "Environment Variables":

```
VITE_API_BASE_URL=https://your-backend-url/api
```

Replace `your-backend-url` with an API gateway URL. Since you have multiple services on Render, you have two options:

**Option A: Use an API Proxy/Router** (Recommended)
- Create a simple Node.js proxy on Render that routes to all services
- Point `VITE_API_BASE_URL` to that proxy

**Option B: Point to Individual Services** (Simpler for testing)
- Modify frontend to point directly to auth service
- Update service URLs in each component

For now, use Option A structure:
```
VITE_API_BASE_URL=https://docsign-api-gateway.onrender.com/api
```

### 4.3 Deploy
Click "Deploy" - Vercel will automatically deploy on every GitHub push.

## Step 5: Create API Gateway (Optional but Recommended)

To route all frontend requests through a single endpoint, create a lightweight Node.js proxy.

Create `api-gateway/server.js`:
```javascript
const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('express-http-proxy');

const app = express();
app.use(cors());

app.use('/api/auth', createProxyMiddleware({
  target: process.env.AUTH_SERVICE_URL,
  changeOrigin: true,
}));

app.use('/api/documents', createProxyMiddleware({
  target: process.env.DOCUMENT_SERVICE_URL,
  changeOrigin: true,
}));

app.listen(8000, () => console.log('API Gateway running on port 8000'));
```

## Step 6: Verify Deployment

### 6.1 Test Services Health Endpoints
```bash
# Auth Service
curl https://docsign-auth-service.onrender.com/health

# Document Service
curl https://docsign-document-service.onrender.com/health

# Notification Service
curl https://docsign-notification-service.onrender.com/health
```

### 6.2 Test Frontend
Visit your Vercel deployment URL and verify:
- Login page loads
- Can create an account
- Can login
- Can view dashboard

### 6.3 Database Connection
Check service logs in Render dashboard for any database connection errors.

## Common Issues & Fixes

### Issue: "Connection refused" to database
**Solution**: Verify Railway PostgreSQL is running and credentials are correct in Render env vars

### Issue: "CORS error" on frontend
**Solution**: Ensure `CORS_ORIGINS` env var in backend matches your Vercel domain

### Issue: Services timeout on first start
**Solution**: Free tier services take 1-2 minutes to start. Check logs and wait.

### Issue: PDF storage not working
**Solution**: Free tier services have ephemeral storage. Use cloud storage (AWS S3, etc.) for production

## Next Steps

1. **Custom Domain**: Connect your domain to Vercel
2. **SSL Certificate**: Automatically provided by all platforms
3. **Monitoring**: Set up alerts in Render dashboard
4. **Backups**: Configure automatic PostgreSQL backups in Railway
5. **Scaling**: Upgrade to paid tiers when needed

## Production Checklist

- [ ] Database backups configured
- [ ] SSL/TLS enabled on all services
- [ ] Secrets stored securely (not in code)
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Email notifications tested
- [ ] PDF generation tested
- [ ] Error logging configured
- [ ] Uptime monitoring enabled

## Support

For platform-specific help:
- [Vercel Docs](https://vercel.com/docs)
- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
