# Google Cloud Run Deployment Guide

## Overview

This guide explains how to deploy the Grants MCP server to Google Cloud Run with automatic CI/CD using GitHub Actions. The deployment is optimized for cost-effectiveness, security, and scalability.

## Architecture

```
GitHub Repository (push to main)
         ↓
GitHub Actions (FREE CI/CD)
         ↓
Google Artifact Registry (Docker images)
         ↓
Google Cloud Run (serverless hosting)
         ↓
Users connect via Claude Desktop/claude.ai
```

## Cost Overview

### Monthly Costs (Estimated)
- **Cloud Run**: $0-30/month (generous free tier)
- **Artifact Registry**: $1-3/month (Docker image storage)
- **GitHub Actions**: $0/month (unlimited for public repos)
- **Total**: $5-35/month for most use cases

### Free Tier Benefits
- 180,000 vCPU-seconds/month
- 360,000 GiB-seconds/month
- 2 million requests/month
- Scales to zero when idle (no charges)

## Prerequisites

### 1. Google Cloud Account
- Create account at [Google Cloud Console](https://console.cloud.google.com/)
- Enable billing (required for Cloud Run)
- Get $300 free credits for 90 days

### 2. gcloud CLI Installation
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Initialize and authenticate
gcloud init
gcloud auth login
```

### 3. API Keys
- **Simpler Grants API Key**: Get from [Simpler Grants API](https://api.simpler.grants.gov)

## Setup Instructions

### Step 1: Google Cloud Project Configuration

```bash
# Set your project ID (already configured as 'grants-mcp')
export PROJECT_ID=grants-mcp
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry repository
gcloud artifacts repositories create grants-mcp \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for Grants MCP server"
```

### Step 2: Service Account Setup

```bash
# Create service account for GitHub Actions deployment
gcloud iam service-accounts create github-deployer \
    --display-name="GitHub Actions Deployer" \
    --description="Service account for GitHub Actions CI/CD"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

# Grant service account impersonation permission
gcloud iam service-accounts add-iam-policy-binding \
    grants-mcp-runner@$PROJECT_ID.iam.gserviceaccount.com \
    --member="serviceAccount:github-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Create and download service account key
gcloud iam service-accounts keys create ~/github-deployer-key.json \
    --iam-account=github-deployer@$PROJECT_ID.iam.gserviceaccount.com

# Create service account for Cloud Run (runtime)
gcloud iam service-accounts create grants-mcp-runner \
    --display-name="Grants MCP Runtime" \
    --description="Service account for running the MCP server"
```

### Step 3: GitHub Repository Secrets

Go to your GitHub repository: `https://github.com/Tar-ive/grants-mcp/settings/secrets/actions`

Add these repository secrets:

1. **GCP_SA_KEY**
   - Copy the entire contents of `~/github-deployer-key.json`
   - Paste as the secret value

2. **SIMPLER_GRANTS_API_KEY**
   - Your Simpler Grants API key
   - This will be passed to the Cloud Run service as an environment variable

The **GCP_PROJECT_ID** is already hardcoded as "grants-mcp" in the workflow.

### Step 4: Deploy via GitHub Actions

The deployment is now fully automated! Simply:

```bash
# Push to main branch to trigger deployment
git push origin main
```

The GitHub Actions workflow will:
1. ✅ Build Docker image with caching
2. ✅ Push to Google Artifact Registry
3. ✅ Deploy to Cloud Run
4. ✅ Run health checks
5. ✅ Provide deployment summary with URLs

## Service Configuration

### Cloud Run Service Settings

The deployed service includes:

- **Memory**: 1 GiB
- **CPU**: 1 vCPU
- **Timeout**: 300 seconds
- **Concurrency**: 1000 requests per instance
- **Scaling**: 0 to 100 instances
- **Port**: 8080
- **Public access**: Enabled (no authentication required)

### Environment Variables

```bash
MCP_TRANSPORT=http
PORT=8080
SIMPLER_GRANTS_API_KEY=<from_secrets>
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
CACHE_TTL=300
MAX_CACHE_SIZE=1000
```

## Accessing the Deployed Service

### Service Endpoints

After deployment, you'll get URLs like:
- **MCP Endpoint**: `https://grants-mcp-xxx-uc.a.run.app/mcp`
- **Health Check**: `https://grants-mcp-xxx-uc.a.run.app/health`

### Claude Desktop Integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "grants-mcp-cloud": {
      "command": "npx",
      "args": ["mcp-remote", "https://grants-mcp-xxx-uc.a.run.app/mcp"]
    }
  }
}
```

### Testing the Deployment

```bash
# Test health endpoint
curl https://grants-mcp-xxx-uc.a.run.app/health

# Test MCP tools list
curl -X POST https://grants-mcp-xxx-uc.a.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Monitoring and Maintenance

### Cloud Run Monitoring

1. **Metrics Dashboard**: 
   - Go to [Cloud Run Console](https://console.cloud.google.com/run)
   - Click on your service → Metrics tab

2. **Key Metrics to Monitor**:
   - Request count and latency
   - Instance count and CPU utilization
   - Error rate and container crashes
   - Memory usage

### Log Viewing

```bash
# View recent logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=grants-mcp" \
  --limit=50 \
  --format="table(timestamp,textPayload)"

# Follow live logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=grants-mcp"
```

### Cost Monitoring

1. **Billing Dashboard**: [Google Cloud Billing](https://console.cloud.google.com/billing)
2. **Cost Breakdown**: Monitor Cloud Run and Artifact Registry usage
3. **Budget Alerts**: Set up budget alerts for cost control

## Troubleshooting

### Common Issues

1. **Deployment Fails with Permission Error**
   ```bash
   # Check service account permissions
   gcloud projects get-iam-policy $PROJECT_ID
   ```

2. **Service Not Responding**
   ```bash
   # Check service status
   gcloud run services describe grants-mcp --region=us-central1
   
   # View logs for errors
   gcloud logs read "resource.type=cloud_run_revision"
   ```

3. **Health Check Failures**
   - Verify the `/health` endpoint is accessible
   - Check if the service is properly starting up
   - Review startup logs for initialization errors

### Manual Deployment (Emergency)

If GitHub Actions fails, deploy manually:

```bash
# Build and push image
docker build -t us-central1-docker.pkg.dev/grants-mcp/grants-mcp/server:manual .
docker push us-central1-docker.pkg.dev/grants-mcp/grants-mcp/server:manual

# Deploy to Cloud Run
gcloud run deploy grants-mcp \
  --image us-central1-docker.pkg.dev/grants-mcp/grants-mcp/server:manual \
  --platform managed \
  --region us-central1 \
  --port 8080 \
  --set-env-vars SIMPLER_GRANTS_API_KEY=your_key_here \
  --allow-unauthenticated
```

## Security Considerations

### Service Account Security
- ✅ Minimal IAM permissions (Cloud Run Admin, Artifact Registry Writer)
- ✅ Non-root container user
- ✅ No hardcoded credentials in repository

### API Key Management
- ✅ API key stored in GitHub Secrets (encrypted)
- ✅ Passed as environment variable to Cloud Run
- ✅ Not exposed in logs or container image

### Network Security
- ✅ HTTPS-only communication
- ✅ Google Cloud's built-in DDoS protection
- ✅ Automatic TLS certificate management

## Scaling and Performance

### Auto-scaling Configuration
- **Min instances**: 0 (scales to zero when idle)
- **Max instances**: 100 (can handle high traffic)
- **Concurrency**: 1000 requests per instance
- **CPU allocation**: During request processing only

### Performance Optimizations
- ✅ Multi-stage Docker build for smaller images
- ✅ Layer caching in GitHub Actions
- ✅ FastMCP framework for efficient MCP protocol handling
- ✅ In-memory caching for API responses

### Load Testing
```bash
# Install Apache Bench for load testing
sudo apt-get install apache2-utils

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 https://grants-mcp-xxx-uc.a.run.app/health
```

## Updates and Maintenance

### Automatic Updates
- ✅ Every push to `main` branch triggers deployment
- ✅ Zero-downtime deployments with traffic shifting
- ✅ Automatic rollback on health check failures

### Manual Updates
```bash
# Update environment variables
gcloud run services update grants-mcp \
  --region=us-central1 \
  --set-env-vars NEW_VAR=value

# Update resource limits
gcloud run services update grants-mcp \
  --region=us-central1 \
  --memory=2Gi \
  --cpu=2
```

### Version Management
- Container images are tagged with Git SHA for traceability
- Previous versions remain in Artifact Registry for rollback
- GitHub releases can trigger specific version deployments

This deployment provides a production-ready, scalable, and cost-effective solution for hosting the Grants MCP server on Google Cloud Run with full CI/CD automation.