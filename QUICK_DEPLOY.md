# Quick Deployment Commands

## 1. Generate Security Keys
```bash
# Generate Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 2. Push to GitHub
```bash
git add -A
git commit -m "Update for cloud deployment"
git push origin main
```

## 3. Test Locally with PostgreSQL (Optional)
```bash
# Install PostgreSQL locally
# Then update .env to use PostgreSQL
export DB_TYPE=postgresql
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=docsign
export DB_USER=docsign
export DB_PASSWORD=yourpassword

# Run services
docker-compose -f docker-compose.yml up --build
```

## 4. Render Deployment URLs (After Creating Services)
- Auth Service: https://docsign-auth-service.onrender.com
- Document Service: https://docsign-document-service.onrender.com
- Notification Service: https://docsign-notification-service.onrender.com

## 5. Railway Database Connection
After creating PostgreSQL on Railway, use these values in all Render env vars:
```
DB_HOST={railway_host}
DB_PORT={railway_port}
DB_NAME={railway_database}
DB_USER={railway_user}
DB_PASSWORD={railway_password}
```

## 6. Vercel Frontend URLs
After deploying on Vercel, update:
- CORS_ORIGINS in Render services
- VITE_API_BASE_URL in Vercel

## 7. Gmail SMTP Setup
1. Enable 2-Step Verification in Gmail
2. Go to https://myaccount.google.com/apppasswords
3. Create "App Password" for "Mail" on "Custom device"
4. Use generated password as SMTP_PASS

## 8. Test Health Endpoints
```bash
# After services are running
curl https://docsign-auth-service.onrender.com/health
curl https://docsign-document-service.onrender.com/health
curl https://docsign-notification-service.onrender.com/health
```

## 9. View Logs
- **Render**: Dashboard → Service → Logs
- **Railway**: Dashboard → PostgreSQL → Logs
- **Vercel**: Dashboard → Project → Deployments → Logs
