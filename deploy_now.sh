#!/bin/bash

# DocSign - Simple One-Command Deployment
# Usage: ./deploy_now.sh

set -e

cd "$(dirname "$0")" || exit

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          DocSign - One-Command Deployment                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if credentials exist
if [ ! -f "$HOME/.docsign_deploy_creds" ]; then
    echo "First time? Let's gather your credentials..."
    echo ""
    ./gather_tokens.sh
fi

# Load credentials
source "$HOME/.docsign_deploy_creds"

# Run deployment
python3 deploy_auto.py

# Show results
if [ -f "DEPLOYMENT_URLS_LIVE.md" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                  ✅ DEPLOYMENT READY                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Your deployment configuration is ready!"
    echo ""
    echo "📋 See DEPLOYMENT_URLS_LIVE.md for:"
    echo "   - Frontend URL"
    echo "   - Backend service URLs"
    echo "   - Database connection details"
    echo "   - Environment variables"
    echo "   - Testing instructions"
    echo ""
    echo "Next: Complete manual setup on Render/Railway/Vercel"
    echo "(Script provides all configs - just copy/paste)"
fi
