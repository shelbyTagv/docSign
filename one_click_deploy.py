#!/usr/bin/env python3
"""
🚀 DocSign - ONE-CLICK CLOUD DEPLOYMENT
Generates Render Blueprint & Vercel instant deploy links
Just click the links and select "Deploy" - everything is pre-configured!
"""

import json
import sys
from pathlib import Path

class OneClickDeploy:
    def __init__(self):
        self.github_repo = "shelbyTagv/docSign"
        self.github_url = "https://github.com/shelbyTagv/docSign"
    
    def generate_render_button(self):
        """Generate Render Blueprint deploy button"""
        # Render Blueprint URL: https://render.com/deploy?repo=<github_url>&branch=<branch>
        render_url = f"https://render.com/deploy?repo={self.github_url}/tree/main"
        return render_url
    
    def generate_vercel_button(self):
        """Generate Vercel instant deploy button"""
        # Vercel GitHub integration will auto-deploy from vercel.json
        vercel_url = f"https://vercel.com/new/clone?repository-url={self.github_url}&project-name=docsign&repository-name=docSign"
        return vercel_url
    
    def print_deployment_guide(self):
        """Print deployment instructions"""
        render_url = self.generate_render_button()
        vercel_url = self.generate_vercel_button()
        
        guide = f"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     🚀 DocSign - ONE-CLICK AUTOMATIC DEPLOYMENT                 ║
║                                                                  ║
║          Everything is pre-configured. Just click!              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

📍 DATABASE (Already Live!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ PostgreSQL on Railway
  Host: acela.proxy.rlwy.net:59853
  Database: railway
  Ready to use!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📘 STEP 1: DEPLOY TO RENDER (Backend Services) [3 minutes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Click this button:

🔗 RENDER DEPLOY LINK
{render_url}

OR visit and select "docSign":
  https://render.com/deploy

What happens:
  1. Render loads the Blueprint (render.yaml) with ALL settings
  2. Shows 3 services pre-configured:
     - docsign-auth-service
     - docsign-document-service  
     - docsign-notification-service
  3. All environment variables are pre-filled ✓
  4. Click "Deploy" and wait 3-5 minutes

Done! You'll have 3 live URLs:
  🔐 https://docsign-auth-service.onrender.com
  📄 https://docsign-document-service.onrender.com
  📧 https://docsign-notification-service.onrender.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📘 STEP 2: DEPLOY TO VERCEL (Frontend) [2 minutes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Click this button:

🔗 VERCEL DEPLOY LINK
{vercel_url}

OR visit:
  https://vercel.com/new/clone?repository-url={self.github_url}

What happens:
  1. Vercel imports the docSign GitHub repo
  2. Loads settings from vercel.json ✓
  3. Sets root directory to "frontend" ✓
  4. Environment variables pre-configured ✓
  5. Click "Deploy" and wait 1-2 minutes

Done! You'll have:
  🌐 https://docsign.vercel.app (or similar)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ TEST YOUR LIVE SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After both deployments complete:

1. Open frontend in browser:
   https://docsign.vercel.app

2. Test backend services (should return ✓):
   curl https://docsign-auth-service.onrender.com/health
   curl https://docsign-document-service.onrender.com/health
   curl https://docsign-notification-service.onrender.com/health

3. Create test account in frontend:
   - Sign up with email
   - Create a document
   - Download signed PDF

4. Check notification service sending emails

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 YOUR COMPLETE LIVE SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After deployment, you'll have:

┌─ INFRASTRUCTURE ─────────────────────────────────────────────┐
│                                                               │
│  🌐 Frontend              https://docsign.vercel.app          │
│     React app + Vite build, hosted on Vercel free tier       │
│                                                               │
│  🔐 Auth Service          https://docsign-auth-service...     │
│     User authentication + JWT + MFA, on Render free tier     │
│                                                               │
│  📄 Document Service      https://docsign-document...         │
│     PDF generation + digital signatures, Render free tier    │
│                                                               │
│  📧 Notification Service  https://docsign-notification...     │
│     Email notifications + status updates, Render free tier   │
│                                                               │
│  🗄️ Database               PostgreSQL on Railway              │
│     acela.proxy.rlwy.net:59853 - Already live!               │
│                                                               │
└───────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 MONITOR YOUR DEPLOYMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dashboards:
  → Render:   https://dashboard.render.com
  → Vercel:   https://vercel.com/dashboard
  → Railway:  https://railway.app/dashboard

Check logs:
  → Render: Click service → "Logs" tab
  → Vercel: Click project → "Deployments" tab

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Services show "Build Failed"?
  → Check Render dashboard logs
  → Verify all environment variables are set
  → Check GitHub repo is connected

Frontend can't connect to API?
  → Open browser console (F12)
  → Check the API URL in the error message
  → Verify VITE_API_BASE_URL in Vercel settings

Emails not sending?
  → Check notification service logs on Render
  → Verify SMTP credentials: h220218p@hit.ac.zw
  → Check Gmail app password is valid

Database connection fails?
  → Test connection: psql -h acela.proxy.rlwy.net -p 59853 -U postgres
  → Password: FFRcvuhsnQzlAYIMnyvGLMhxjNPDSnYS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Click "Render Deploy" button above ↑
2. Wait for 3 services to deploy (~3-5 min)
3. Click "Vercel Deploy" button above ↑
4. Wait for frontend to deploy (~1-2 min)
5. Open https://docsign.vercel.app
6. Create test account
7. Upload and sign a document
8. Done! System is live on internet 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Questions? Check the deployment logs in the respective dashboards.

Generated: {Path.cwd()}
"""
        print(guide)
        
        # Save to file
        with open(Path.cwd() / 'ONE_CLICK_DEPLOY.md', 'w') as f:
            f.write(guide)
        
        print(f"\n✓ Guide saved to: ONE_CLICK_DEPLOY.md")
        
        return guide

if __name__ == '__main__':
    deployer = OneClickDeploy()
    deployer.print_deployment_guide()
