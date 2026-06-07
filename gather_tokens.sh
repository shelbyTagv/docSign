#!/bin/bash

# DocSign - API Token Generation Guide
# This script helps you generate all required API tokens

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DocSign - Automated Deployment Token Generator         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Create credentials file
CREDS_FILE="$HOME/.docsign_deploy_creds"

print_step "This script will help you gather API tokens for automated deployment"
echo ""

# 1. GitHub Token
echo "─────────────────────────────────────────────────────────────"
print_step "1. GITHUB PERSONAL ACCESS TOKEN"
echo ""
echo "You mentioned you have a GitHub token ready."
echo ""
read -p "Paste your GitHub Personal Access Token (or press Enter to skip): " github_token

if [ -n "$github_token" ]; then
    print_success "GitHub token received"
fi

echo ""

# 2. Vercel Token
echo "─────────────────────────────────────────────────────────────"
print_step "2. VERCEL API TOKEN"
echo ""
echo "Steps to generate:"
echo "  1. Go to: https://vercel.com/account/tokens"
echo "  2. Click 'Create' → Name it 'docsign-deploy'"
echo "  3. Copy the token"
echo ""
read -p "Paste your Vercel API Token: " vercel_token

if [ -z "$vercel_token" ]; then
    print_warning "Skipping Vercel (manual deployment)"
else
    print_success "Vercel token received"
fi

echo ""

# 3. Render Token
echo "─────────────────────────────────────────────────────────────"
print_step "3. RENDER API KEY"
echo ""
echo "Steps to generate:"
echo "  1. Go to: https://dashboard.render.com/account/api-tokens"
echo "  2. Click 'Create API Key'"
echo "  3. Copy the key"
echo ""
read -p "Paste your Render API Key: " render_token

if [ -z "$render_token" ]; then
    print_warning "Skipping Render (manual deployment)"
else
    print_success "Render token received"
fi

echo ""

# 4. Railway Token
echo "─────────────────────────────────────────────────────────────"
print_step "4. RAILWAY API TOKEN"
echo ""
echo "Steps to generate:"
echo "  1. Go to: https://railway.app/account/tokens"
echo "  2. Click 'Create New Token'"
echo "  3. Copy the token"
echo ""
read -p "Paste your Railway API Token: " railway_token

if [ -z "$railway_token" ]; then
    print_warning "Skipping Railway (manual deployment)"
else
    print_success "Railway token received"
fi

echo ""

# 5. Security Keys
echo "─────────────────────────────────────────────────────────────"
print_step "5. SECURITY KEYS (Generating...)"
echo ""

FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
INTERNAL_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

print_success "FERNET_KEY generated"
print_success "INTERNAL_API_KEY generated"

echo ""

# 6. Gmail Setup
echo "─────────────────────────────────────────────────────────────"
print_step "6. GMAIL APP PASSWORD"
echo ""
echo "You mentioned Gmail is ready."
echo ""
read -p "Enter your Gmail address (e.g., user@gmail.com): " smtp_user
read -sp "Enter your Gmail App Password (won't be shown): " smtp_pass
echo ""

if [ -n "$smtp_user" ] && [ -n "$smtp_pass" ]; then
    print_success "Gmail credentials received"
fi

echo ""

# 7. Other Configuration
echo "─────────────────────────────────────────────────────────────"
print_step "7. DEPLOYMENT CONFIGURATION"
echo ""

read -p "Enter your project name (default: docsign): " project_name
project_name=${project_name:-docsign}

read -p "Enter your organization name (default: Your Organization): " org_name
org_name=${org_name:-Your Organization}

print_success "Configuration received"

echo ""

# Save to file using bash variable expansion
cat > "$CREDS_FILE" << EOF
# DocSign Deployment Credentials
# This file contains sensitive information - keep it secure!
# Generated: $(date)

export GITHUB_TOKEN="$github_token"
export VERCEL_TOKEN="$vercel_token"
export RENDER_TOKEN="$render_token"
export RAILWAY_TOKEN="$railway_token"
export FERNET_KEY="$FERNET_KEY"
export INTERNAL_API_KEY="$INTERNAL_API_KEY"
export SMTP_USER="$smtp_user"
export SMTP_PASS="$smtp_pass"
export PROJECT_NAME="$project_name"
export ORG_NAME="$org_name"
export GITHUB_REPO="shelbyTagv/docSign"
EOF

# Save credentials securely
chmod 600 "$CREDS_FILE"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    SUMMARY                                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
print_success "Credentials saved to: $CREDS_FILE"
print_warning "⚠ This file contains sensitive data - keep it private!"
echo ""
echo "Next steps:"
echo "  1. Run: source $CREDS_FILE"
echo "  2. Run: ./automated_deploy.sh"
echo ""
echo "Or run automated deployment with:"
echo "  ./automated_deploy.sh --use-creds $CREDS_FILE"
echo ""
