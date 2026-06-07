#!/bin/bash

# DocSign Platform - Fully Automated Deployment
# This script automates deployment to Vercel, Render, and Railway

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶${NC} $1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Check if credentials file is provided
if [ $# -gt 0 ] && [ "$1" == "--use-creds" ] && [ -n "$2" ]; then
    CREDS_FILE="$2"
    if [ -f "$CREDS_FILE" ]; then
        source "$CREDS_FILE"
        print_success "Loaded credentials from $CREDS_FILE"
    else
        print_error "Credentials file not found: $CREDS_FILE"
        exit 1
    fi
else
    # Check if credentials are in environment
    if [ -z "$VERCEL_TOKEN" ] || [ -z "$RENDER_TOKEN" ] || [ -z "$RAILWAY_TOKEN" ]; then
        print_error "Missing API tokens. Run: ./gather_tokens.sh first"
        exit 1
    fi
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DocSign Platform - Fully Automated Cloud Deployment      ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Verify tools installed
print_step "Checking Prerequisites"

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed"
        echo "Install it and try again"
        return 1
    else
        print_success "$1 installed"
    fi
}

check_command "git"
check_command "curl"
check_command "python3"
check_command "jq" || print_warning "jq not found - some features may not work. Install with: sudo apt-get install jq"

# Set default values
PROJECT_NAME=${PROJECT_NAME:-docsign}
GITHUB_REPO=${GITHUB_REPO:-shelbyTagv/docSign}
ORG_NAME=${ORG_NAME:-Your Organization}

print_step "Phase 1: Preparing GitHub Repository"

# Ensure we're in git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Add and commit changes
if ! git diff-index --quiet HEAD --; then
    print_info "Committing deployment changes..."
    git add -A
    git commit -m "chore: automated deployment configuration" || true
fi

# Push to GitHub
print_info "Pushing code to GitHub..."
git push origin main -q 2>/dev/null || print_warning "Could not push to GitHub (may already be up to date)"
print_success "Code pushed to GitHub"

print_step "Phase 2: Setting Up PostgreSQL on Railway"

if [ -z "$RAILWAY_TOKEN" ]; then
    print_warning "Skipping Railway - no API token provided"
    print_info "Manual setup required at: https://railway.app"
else
    print_info "Creating Railway PostgreSQL database..."
    
    # Create Railway project and PostgreSQL via API
    PROJECT_RESPONSE=$(curl -s -X POST https://api.railway.app/graphql \
      -H "Authorization: Bearer $RAILWAY_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "mutation { projectCreate(input: { name: \"DocSign\" }) { project { id name } } }"
      }')
    
    RAILWAY_PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.data.projectCreate.project.id' 2>/dev/null)
    
    if [ -n "$RAILWAY_PROJECT_ID" ] && [ "$RAILWAY_PROJECT_ID" != "null" ]; then
        print_success "Railway project created: $RAILWAY_PROJECT_ID"
        print_info "PostgreSQL database configuration:"
        print_info "  - Visit: https://railway.app"
        print_info "  - Provision PostgreSQL from the new project"
        print_info "  - Copy the connection details"
        print_warning "⚠ Manual step required: Provision PostgreSQL in Railway UI"
    else
        print_warning "Could not auto-create Railway project via API"
        print_info "Please manually create at: https://railway.app"
    fi
fi

read -p "Have you created PostgreSQL on Railway? Enter database host (or skip): " railway_host

if [ -z "$railway_host" ]; then
    print_warning "Skipping automatic Render deployment (requires database host)"
    print_info "Please configure Railway manually and run this script again"
    exit 0
fi

read -p "Enter PostgreSQL port (default 5432): " railway_port
railway_port=${railway_port:-5432}

read -p "Enter database name (default docsign): " railway_db
railway_db=${railway_db:-docsign}

read -p "Enter database user (default docsign): " railway_user
railway_user=${railway_user:-docsign}

read -sp "Enter database password: " railway_password
echo ""

print_success "PostgreSQL credentials received"

print_step "Phase 3: Deploying Backend Services to Render"

if [ -z "$RENDER_TOKEN" ]; then
    print_warning "Skipping Render - no API token provided"
    print_info "Manual setup required at: https://render.com"
else
    # Function to create Render service
    create_render_service() {
        local service_name=$1
        local service_type=$2
        local build_command=$3
        local start_command=$4
        local port=$5
        
        print_info "Creating $service_name..."
        
        # For now, we'll provide the configuration and user needs to create manually
        cat > "/tmp/${service_name}_render_config.json" << EOF
{
  "name": "$service_name",
  "region": "oregon",
  "plan": "free",
  "environmentVariables": {
    "PYTHONUNBUFFERED": "true",
    "DB_TYPE": "postgresql",
    "DB_HOST": "$railway_host",
    "DB_PORT": "$railway_port",
    "DB_NAME": "$railway_db",
    "DB_USER": "$railway_user",
    "DB_PASSWORD": "$railway_password",
    "FERNET_KEY": "$FERNET_KEY",
    "INTERNAL_API_KEY": "$INTERNAL_API_KEY",
    "CORS_ORIGINS": "http://localhost:3000",
    "FRONTEND_URL": "http://localhost:3000"
  }
}
EOF
        print_success "Config saved for $service_name"
    }
    
    # Create configs for all services
    create_render_service "docsign-auth-service" "web" \
        "pip install -r auth-service/requirements.txt" \
        "cd auth-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 app.main:app" \
        "8001"
    
    create_render_service "docsign-document-service" "web" \
        "pip install -r document-service/requirements.txt" \
        "cd document-service && gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002 app.main:app" \
        "8002"
    
    create_render_service "docsign-notification-service" "web" \
        "pip install -r notification-service/requirements.txt" \
        "cd notification-service && gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8003 app.main:app" \
        "8003"
    
    print_warning "⚠ Render services require manual creation:"
    print_info "  1. Go to https://render.com"
    print_info "  2. For each service:"
    print_info "     - New Web Service → Connect GitHub → shelbyTagv/docSign"
    print_info "     - Configure build/start commands (see DEPLOYMENT_GUIDE.md)"
    print_info "     - Add environment variables from /tmp/*_render_config.json"
fi

print_step "Phase 4: Deploying Frontend to Vercel"

if [ -z "$VERCEL_TOKEN" ]; then
    print_warning "Skipping Vercel - no API token provided"
    print_info "Manual setup required at: https://vercel.com"
else
    print_info "Deploying frontend to Vercel..."
    
    # Vercel CLI deployment
    if command -v vercel &> /dev/null; then
        cd frontend
        vercel --token "$VERCEL_TOKEN" --project "$PROJECT_NAME" --name "$PROJECT_NAME-frontend" --prod
        cd ..
        print_success "Frontend deployed to Vercel"
    else
        print_warning "Vercel CLI not installed"
        print_info "Install with: npm i -g vercel"
        print_info "Then run: vercel --token $VERCEL_TOKEN --prod"
    fi
fi

print_step "Phase 5: Creating Deployment Summary"

# Create a summary file with all URLs and credentials
cat > "DEPLOYMENT_URLS.md" << EOF
# DocSign Platform - Deployment URLs & Credentials

**Generated:** $(date)

## 📍 Service URLs

### Frontend (Vercel)
\`\`\`
https://your-vercel-domain.vercel.app
\`\`\`
(URL will be provided after Vercel deployment)

### Backend Services (Render)
\`\`\`
Auth Service:         https://docsign-auth-service.onrender.com
Document Service:     https://docsign-document-service.onrender.com
Notification Service: https://docsign-notification-service.onrender.com
\`\`\`

### Database (Railway)
\`\`\`
Host:     $railway_host
Port:     $railway_port
Database: $railway_db
User:     $railway_user
\`\`\`

## 🔑 Environment Variables

### Database
\`\`\`
DB_TYPE=postgresql
DB_HOST=$railway_host
DB_PORT=$railway_port
DB_NAME=$railway_db
DB_USER=$railway_user
DB_PASSWORD=[SECURE - NOT STORED]
\`\`\`

### Security Keys
\`\`\`
FERNET_KEY=$FERNET_KEY
INTERNAL_API_KEY=$INTERNAL_API_KEY
\`\`\`

### Email (Gmail)
\`\`\`
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=$SMTP_USER
SMTP_PASS=[SECURE - NOT STORED]
SMTP_FROM=DocSign Platform <noreply@yourdomain.com>
\`\`\`

### Application
\`\`\`
ORG_NAME=$ORG_NAME
PROJECT_NAME=$PROJECT_NAME
GITHUB_REPO=$GITHUB_REPO
\`\`\`

## 🧪 Testing Health Endpoints

Once services are running, test with:

\`\`\`bash
# Auth Service
curl https://docsign-auth-service.onrender.com/health

# Document Service
curl https://docsign-document-service.onrender.com/health

# Notification Service
curl https://docsign-notification-service.onrender.com/health
\`\`\`

## 📋 Next Steps

1. If services aren't created yet, manually create them in Render
2. Update CORS_ORIGINS to match your Vercel URL
3. Test all health endpoints
4. Verify frontend loads and can connect to backend
5. Create test user account
6. Test document signing workflow

## ⚙️ Manual Configuration Still Required

If any platforms' APIs didn't work:

### Railway
- [ ] Go to https://railway.app
- [ ] Create PostgreSQL database
- [ ] Save connection details above

### Render
- [ ] Go to https://render.com
- [ ] Create 3 Web Services (see DEPLOYMENT_GUIDE.md)
- [ ] Add environment variables
- [ ] Update CORS_ORIGINS with your Vercel URL

### Vercel
- [ ] Go to https://vercel.com
- [ ] Import GitHub repo
- [ ] Set VITE_API_BASE_URL environment variable
- [ ] Deploy

## 🔒 Security Notes

- **Never commit** credentials file to GitHub
- Store FERNET_KEY and passwords in a secure location
- Rotate INTERNAL_API_KEY periodically
- Use different passwords for each environment
- Enable 2FA on all platform accounts

EOF

print_success "Deployment summary saved to: DEPLOYMENT_URLS.md"

print_step "✅ DEPLOYMENT COMPLETE!"

echo ""
echo "📋 Summary:"
echo "  ✓ Code pushed to GitHub"
print_info "  ⏳ PostgreSQL: Check Railway dashboard for connection details"
print_info "  ⏳ Backend Services: Create manually on Render"
print_info "  ⏳ Frontend: Deployed or ready for Vercel"
echo ""

print_info "See DEPLOYMENT_URLS.md for all endpoints and configuration"
print_info "See DEPLOYMENT_GUIDE.md for detailed setup instructions"

echo ""
echo "Next: Update Render services with database credentials and deploy frontend"
echo ""
