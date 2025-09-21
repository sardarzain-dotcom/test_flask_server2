# Deployment Configuration

## Current Deployment
- **Production URL**: https://testflaskserver2-1010928307866.us-central1.run.app
- **Platform**: Google Cloud Run
- **Region**: us-central1

## Repository Setup Instructions

Since you have a deployed application but no Git repository configured, follow these steps:

### Step 1: Create a Git Repository
1. Go to [GitHub](https://github.com) and create a new repository named `test_flask_server2`
2. Or use GitLab, Bitbucket, or another Git hosting service

### Step 2: Connect Local Repository to Remote
Once you have created the repository, run these commands:

```bash
# Add the remote repository (replace with your actual repository URL)
git remote add origin https://github.com/YOUR_USERNAME/test_flask_server2.git

# Add all files to git
git add .

# Make initial commit
git commit -m "Initial commit - Flask server with Cloud Run deployment"

# Push to repository
git push -u origin main
```

### Step 3: Configure Deployment Pipeline
For automatic deployment to Cloud Run when you push code:

1. **Using GitHub Actions**: Create `.github/workflows/deploy.yml`
2. **Using Cloud Build**: Create `cloudbuild.yaml`
3. **Manual deployment**: Use `gcloud` CLI

## Environment Variables for Deployment
Make sure these are set in your Cloud Run service:
- `FLASK_ENV=production`
- `PORT=8080` (Cloud Run default)
- Any other environment variables your app needs

## Deployment Commands
```bash
# Deploy to Cloud Run (if you have gcloud CLI configured)
gcloud run deploy testflaskserver2 \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```