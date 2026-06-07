# DocSign Platform - Cloud Deployment Ready

This repository contains a complete document signing platform ready for cloud deployment on **Vercel**, **Render**, and **Railway**.

## 🚀 Quick Start Deployment

### Easiest Way: Use the Deployment Helper Script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will guide you through:
- ✅ Generating secure encryption keys
- ✅ Validating your setup
- ✅ Pushing code to GitHub
- ✅ Providing deployment instructions

## 📋 Deployment Overview

| Component | Platform | Tier | Cost |
|-----------|----------|------|------|
| Frontend (React) | Vercel | Free | $0 |
| Auth Service | Render | Free | $0 |
| Document Service | Render | Free | $0 |
| Notification Service | Render | Free | $0 |
| PostgreSQL Database | Railway | Free | $5 credit |
| **Total Monthly** | - | - | **~$0-5** |

## 📁 Project Structure

```
docSignGithub/
├── frontend/                    # React + Vite application
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── vercel.json             # Vercel configuration
│
├── auth-service/                # FastAPI Authentication Service
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile.prod         # Production Docker image
│   └── .env.example
│
├── document-service/            # FastAPI Document Service
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile.prod
│   └── .env.example
│
├── notification-service/        # FastAPI Email Service
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile.prod
│   └── .env.example
│
├── DEPLOYMENT_GUIDE.md         # Step-by-step deployment guide
├── QUICK_DEPLOY.md             # Quick reference commands
├── deploy.sh                   # Automated deployment helper
└── render.yaml                 # Render deployment configuration
```

## 🔧 What's Been Updated for Cloud Deployment

### ✅ Database
- **MySQL → PostgreSQL** (Railway free tier compatible)
- Auto-detection of DB type in config
- Alembic migrations ready

### ✅ Dependencies
- Added `gunicorn` for production WSGI server
- Added `psycopg2-binary` for PostgreSQL
- Added `whitenoise` for static file serving

### ✅ Configuration
- Environment variable support for all services
- Production Dockerfile for each service
- Vercel configuration for frontend
- Render deployment YAML

### ✅ Frontend
- Dynamic API base URL via `VITE_API_BASE_URL`
- Production build optimization
- Static asset caching

## 📊 Prerequisites

- ✅ GitHub account (already have repo)
- ✅ Vercel account (free)
- ✅ Render account (free)
- ✅ Railway account (free, $5 credit on signup)
- ✅ Gmail account (for notifications)

## 🚀 Deployment Steps (5 minutes)

### Step 1: Generate Security Keys
```bash
./deploy.sh
# Choose option 1: Generate secure keys
# Save the output - you'll need it!
```

### Step 2: Set Up Database (Railway)
1. Go to https://railway.app
2. New Project → Provision PostgreSQL
3. Copy connection details

### Step 3: Deploy Backend Services (Render)
1. Go to https://render.com
2. New Web Service → Connect GitHub
3. Deploy `auth-service`, `document-service`, `notification-service`
4. Add environment variables (from Step 1 + Railway credentials)

### Step 4: Deploy Frontend (Vercel)
1. Go to https://vercel.com
2. Add Project → Select GitHub repo
3. Framework: React, Root: `./frontend`
4. Set `VITE_API_BASE_URL` to your Render backend URL

### Step 5: Verify Deployment
```bash
# Test health endpoints
curl https://docsign-auth-service.onrender.com/health
curl https://docsign-document-service.onrender.com/health
curl https://docsign-notification-service.onrender.com/health

# Visit your frontend
# https://your-project.vercel.app
```

## 📖 Detailed Documentation

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete step-by-step guide
- **[QUICK_DEPLOY.md](./QUICK_DEPLOY.md)** - Quick reference and commands
- **[deploy.sh](./deploy.sh)** - Interactive deployment helper

## 🔐 Security Features

- ✅ RSA 256 JWT authentication
- ✅ TOTP MFA support
- ✅ Fernet encryption for sensitive data
- ✅ PostgreSQL with secure credentials
- ✅ CORS protection
- ✅ Rate limiting on all endpoints
- ✅ Password hashing with bcrypt
- ✅ API key validation for service-to-service

## 🛠️ Technology Stack

### Frontend
- React 18
- Vite (build tool)
- Tailwind CSS
- React Router
- TanStack Query (data fetching)
- Axios (HTTP client)

### Backend
- FastAPI (Python framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Alembic (migrations)
- Gunicorn (production server)

### DevOps
- Docker (containerization)
- Vercel (frontend hosting)
- Render (backend hosting)
- Railway (database hosting)
- GitHub (repository)

## 📞 Support

### Common Issues

**Q: "Connection refused" to database**
- A: Verify Railway PostgreSQL is running and credentials match in Render

**Q: CORS errors on frontend
- A: Check `CORS_ORIGINS` env var matches your Vercel domain

**Q: Services timeout on startup**
- A: Free tier can take 1-2 min. Check logs in respective dashboards

**Q: Email notifications not sending**
- A: Verify Gmail app password is correct. Enable 2FA on Gmail first

## 🎯 Next Steps

1. **Follow DEPLOYMENT_GUIDE.md** for detailed instructions
2. **Run `./deploy.sh`** for automated help
3. **Deploy to Vercel/Render/Railway** using provided configs
4. **Test the application** with provided health endpoints
5. **Monitor logs** via platform dashboards

## 📝 Environment Variables Quick Reference

### Required for All Services
```
INTERNAL_API_KEY          # Shared secret for service auth
```

### Auth & Document Services
```
DB_TYPE=postgresql
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  # From Railway
MASTER_ENCRYPTION_KEY     # Generate with deploy.sh
CORS_ORIGINS              # Your Vercel frontend URL
FRONTEND_URL              # Your Vercel frontend URL
```

### Notification Service
```
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
SMTP_FROM
ORG_NAME
```

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Vercel Deployment Guide](https://vercel.com/docs)
- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app/)

## 📄 License

[Add your license here]

## 👤 Author

Created for automated cloud deployment

---

**Ready to deploy?** Start with `./deploy.sh` or read [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)!
