#!/bin/bash

# DocSign Deployment Helper Script
# This script helps automate parts of the deployment process

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        DocSign Platform - Deployment Helper Script         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Generate Secure Keys
generate_keys() {
    print_status "Generating secure keys..."
    
    echo ""
    print_status "FERNET KEY (for encryption):"
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "$FERNET_KEY"
    
    echo ""
    print_status "INTERNAL API KEY (for service-to-service communication):"
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "$API_KEY"
    
    echo ""
    print_success "Keys generated! Save these values securely."
    echo ""
}

# Step 2: Check GitHub Repository
check_git_setup() {
    print_status "Checking Git repository..."
    
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a Git repository. Please run: git init && git remote add origin https://github.com/shelbyTagv/docSign.git"
        return 1
    fi
    
    REMOTE_URL=$(git config --get remote.origin.url)
    print_success "Git repository found: $REMOTE_URL"
    
    if git status --porcelain | grep -q .; then
        print_warning "Uncommitted changes detected. Remember to push before deployment."
    else
        print_success "Repository is clean"
    fi
}

# Step 3: Validate Environment Variables
validate_env() {
    print_status "Validating environment variables..."
    
    local required_vars=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER" "DB_PASSWORD" "MASTER_ENCRYPTION_KEY" "INTERNAL_API_KEY")
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing environment variables: ${missing_vars[*]}"
        print_status "Create a .env file with these variables"
        return 1
    else
        print_success "All required environment variables are set"
    fi
}

# Step 4: Build Docker Images
build_docker_images() {
    print_status "Building Docker images..."
    
    print_status "Building auth-service..."
    docker build -f auth-service/Dockerfile.prod -t docsign-auth-service:prod ./auth-service
    print_success "auth-service built"
    
    print_status "Building document-service..."
    docker build -f document-service/Dockerfile.prod -t docsign-document-service:prod ./document-service
    print_success "document-service built"
    
    print_status "Building notification-service..."
    docker build -f notification-service/Dockerfile.prod -t docsign-notification-service:prod ./notification-service
    print_success "notification-service built"
}

# Step 5: Push Code to GitHub
push_to_github() {
    print_status "Pushing code to GitHub..."
    
    if ! git diff-index --quiet HEAD --; then
        print_status "Committing changes..."
        git add -A
        git commit -m "chore: update for cloud deployment"
    fi
    
    print_status "Pushing to origin..."
    git push origin main
    print_success "Code pushed to GitHub"
}

# Step 6: Display Deployment Instructions
show_deployment_instructions() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                 NEXT STEPS FOR DEPLOYMENT                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_status "1. RAILWAY (PostgreSQL Database)"
    echo "   - Go to: https://railway.app"
    echo "   - Create new project → Provision PostgreSQL"
    echo "   - Note down: Host, Port, Database, User, Password"
    echo ""
    
    print_status "2. RENDER (Backend Services)"
    echo "   - Go to: https://render.com"
    echo "   - For each service (Auth, Document, Notification):"
    echo "     • Click 'New+' → 'Web Service'"
    echo "     • Connect your GitHub repo"
    echo "     • Set build/start commands (see DEPLOYMENT_GUIDE.md)"
    echo "     • Add environment variables"
    echo ""
    
    print_status "3. VERCEL (Frontend)"
    echo "   - Go to: https://vercel.com"
    echo "   - Add project → Select your GitHub repo"
    echo "   - Framework preset: React"
    echo "   - Root directory: ./frontend"
    echo "   - Add VITE_API_BASE_URL environment variable"
    echo ""
    
    print_status "4. Environment Variables Needed"
    echo "   Database (from Railway):"
    echo "     - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
    echo ""
    echo "   Security:"
    echo "     - MASTER_ENCRYPTION_KEY: $FERNET_KEY"
    echo "     - INTERNAL_API_KEY: $API_KEY"
    echo ""
    echo "   Notification (Gmail):"
    echo "     - SMTP_HOST: smtp.gmail.com"
    echo "     - SMTP_PORT: 587"
    echo "     - SMTP_USER: your-email@gmail.com"
    echo "     - SMTP_PASS: your-app-specific-password (from Gmail settings)"
    echo ""
    
    print_status "5. Verification"
    echo "   After all services are running, test endpoints:"
    echo "   - GET https://docsign-auth-service.onrender.com/health"
    echo "   - GET https://docsign-document-service.onrender.com/health"
    echo "   - GET https://docsign-notification-service.onrender.com/health"
    echo ""
    
    print_status "Documentation: See DEPLOYMENT_GUIDE.md for detailed instructions"
    echo ""
}

# Main Menu
main_menu() {
    echo ""
    echo "What would you like to do?"
    echo "1. Generate secure keys"
    echo "2. Check Git setup"
    echo "3. Push to GitHub"
    echo "4. Build Docker images (test locally)"
    echo "5. Show deployment instructions"
    echo "6. Do all of the above"
    echo "0. Exit"
    echo ""
    read -p "Enter your choice (0-6): " choice
    
    case $choice in
        1)
            generate_keys
            main_menu
            ;;
        2)
            check_git_setup
            main_menu
            ;;
        3)
            push_to_github
            main_menu
            ;;
        4)
            if ! command -v docker &> /dev/null; then
                print_error "Docker is not installed. Please install Docker first."
            else
                build_docker_images
            fi
            main_menu
            ;;
        5)
            show_deployment_instructions
            main_menu
            ;;
        6)
            generate_keys
            check_git_setup
            push_to_github
            show_deployment_instructions
            ;;
        0)
            print_success "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please try again."
            main_menu
            ;;
    esac
}

# Run main menu
main_menu
