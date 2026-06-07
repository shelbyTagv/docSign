#!/bin/bash

# DocSign - Complete One-Command Deployment
# This script handles everything end-to-end

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DocSign Platform - Complete Deployment Script          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Gather tokens
echo -e "${BLUE}Step 1/3: Gathering API Tokens${NC}"
if [ ! -f "$HOME/.docsign_deploy_creds" ]; then
    echo "Run this first to gather credentials:"
    echo "  ./gather_tokens.sh"
    exit 1
else
    echo "Loading credentials..."
    source "$HOME/.docsign_deploy_creds"
fi

# Step 2: Run automated deployment
echo ""
echo -e "${BLUE}Step 2/3: Deploying Services${NC}"
./automated_deploy.sh --use-creds "$HOME/.docsign_deploy_creds"

# Step 3: Generate final report
echo ""
echo -e "${BLUE}Step 3/3: Generating Final Report${NC}"

if [ -f "DEPLOYMENT_URLS.md" ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment configuration complete!${NC}"
    echo ""
    echo "Your deployment URLs and configuration are in: DEPLOYMENT_URLS.md"
    echo ""
    echo "Manual steps remaining:"
    echo "  1. Create PostgreSQL on Railway"
    echo "  2. Create 3 services on Render (auth, document, notification)"
    echo "  3. Deploy frontend on Vercel"
    echo ""
    echo "See DEPLOYMENT_URLS.md for all details"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo "Next: Follow steps in DEPLOYMENT_URLS.md to complete setup"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
