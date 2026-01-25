# Deployment Guide - Zeabur

## Overview

This guide covers deploying the AI Marketing Content System to Zeabur with automatic GitHub integration.

## Prerequisites

1. **GitHub Account**: Repository must be pushed to GitHub
2. **Zeabur Account**: Sign up at https://zeabur.com
3. **Required Services**:
   - PostgreSQL database
   - Redis cache
   - Python application

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository includes:
- ✅ `requirements.txt` - Python dependencies
- ✅ `Dockerfile` - Container configuration
- ✅ `zbpack.json` - Zeabur build configuration
- ✅ `Procfile` - Process configuration
- ✅ `.env.example` - Environment variable template

### 2. Push to GitHub

```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit - AI Marketing Content System"

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git push -u origin main
```

### 3. Create Zeabur Project

1. Log in to [Zeabur Dashboard](https://dash.zeabur.com)
2. Click **"Create New Project"**
3. Give your project a name (e.g., "ai-marketing-system")
4. Select your preferred region

### 4. Add Services

#### A. Add PostgreSQL Database

1. Click **"Add Service"** → **"Marketplace"**
2. Select **"PostgreSQL"**
3. Zeabur will automatically provision the database
4. Note: Connection string will be auto-configured

#### B. Add Redis Cache

1. Click **"Add Service"** → **"Marketplace"**
2. Select **"Redis"**
3. Zeabur will automatically provision Redis
4. Note: Connection string will be auto-configured

#### C. Add Python Application

1. Click **"Add Service"** → **"Git"**
2. Connect your GitHub account (if not already connected)
3. Select your repository
4. Select the branch to deploy (usually `main`)
5. Zeabur will auto-detect Python and use `zbpack.json` configuration

### 5. Configure Environment Variables

In your application service settings, add the following environment variables:

#### Required Variables

```bash
# AI Provider Configuration
PRIMARY_AI_PROVIDER=openai
PRIMARY_AI_BASE_URL=https://api.openai.com/v1
PRIMARY_AI_API_KEY=your_openai_api_key_here
PRIMARY_AI_TEXT_MODEL=gpt-4o
PRIMARY_AI_IMAGE_MODEL=dall-e-3

# WordPress Configuration
WORDPRESS_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_PASSWORD=your_wp_app_password
WORDPRESS_API_ENABLED=true

# Admin Authentication
ADMIN_PASSWORD=your_secure_admin_password_here
ADMIN_SESSION_SECRET=your_random_secret_key_here_min_32_chars
ADMIN_SESSION_EXPIRE_MINUTES=1440

# System Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_CONCURRENT_AGENTS=5
CONTENT_GENERATION_TIMEOUT=600
```

#### Auto-Configured by Zeabur

These variables are automatically set by Zeabur when you add the services:

```bash
DATABASE_URL=${POSTGRES_CONNECTION_STRING}
REDIS_URL=${REDIS_CONNECTION_STRING}
PORT=${PORT}
```

#### Optional Variables

```bash
# Fallback AI Provider
FALLBACK_AI_PROVIDER=custom
FALLBACK_AI_BASE_URL=https://your-api.example.com/v1
FALLBACK_AI_API_KEY=your_fallback_api_key_here

# SEO Plugin
SEO_PLUGIN=yoast
SEO_API_KEY=your_seo_plugin_api_key

# Keyword Research API
KEYWORD_API_PROVIDER=dataforseo
KEYWORD_API_KEY=your_keyword_api_key
```

### 6. Enable Automatic Deployment

Zeabur automatically deploys when you push to GitHub:

1. Go to your service settings in Zeabur
2. Under **"Git"** section, ensure:
   - ✅ Auto Deploy is enabled
   - ✅ Branch is set to `main` (or your preferred branch)
3. Every push to the selected branch will trigger automatic deployment

### 7. Access Your Application

After deployment completes:

1. **Get your domain**: Zeabur provides a free subdomain (e.g., `your-app.zeabur.app`)
2. **Access the API**: `https://your-app.zeabur.app/`
3. **Access Admin Panel**: `https://your-app.zeabur.app/admin`
4. **Health Check**: `https://your-app.zeabur.app/health`

### 8. Custom Domain (Optional)

To use your own domain:

1. Go to your service settings in Zeabur
2. Click **"Domains"** tab
3. Click **"Add Domain"**
4. Enter your custom domain
5. Add the provided DNS records to your domain registrar

## Continuous Deployment Workflow

Once configured, your deployment workflow is:

```bash
# 1. Make changes to your code locally
git add .
git commit -m "Your commit message"

# 2. Push to GitHub
git push origin main

# 3. Zeabur automatically detects the push and deploys
# - Pulls latest code from GitHub
# - Builds the application using zbpack.json
# - Runs tests (if configured)
# - Deploys to production
# - Zero downtime deployment
```

## Monitoring and Logs

### View Application Logs

1. Go to your service in Zeabur dashboard
2. Click **"Logs"** tab
3. View real-time logs from your application

### Monitor Resource Usage

1. Click **"Metrics"** tab
2. Monitor:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

## Troubleshooting

### Build Failures

If deployment fails:

1. Check build logs in Zeabur dashboard
2. Verify all dependencies in `requirements.txt`
3. Ensure Python version compatibility (3.10+)
4. Check for syntax errors in code

### Database Connection Issues

If database connection fails:

1. Verify `DATABASE_URL` is set correctly
2. Check PostgreSQL service is running
3. Ensure database credentials are correct
4. Check network connectivity between services

### Application Not Starting

If application doesn't start:

1. Check environment variables are set correctly
2. Verify `PORT` variable is configured
3. Check application logs for errors
4. Ensure all required services (DB, Redis) are running

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files to Git
2. **Admin Password**: Use strong, unique passwords
3. **Session Secret**: Generate cryptographically secure secrets
4. **API Keys**: Rotate keys regularly
5. **HTTPS**: Always use HTTPS in production (Zeabur provides this automatically)

## Cost Estimation

### Zeabur Pricing

- **Free Tier**: Available for testing and small projects
- **Developer Plan**: ~$5-10/month for small production apps
- **Team Plan**: ~$20-50/month for larger deployments

### Additional Services

- **PostgreSQL**: Included in Zeabur plans
- **Redis**: Included in Zeabur plans
- **AI API Costs**: $50-100/month (based on usage)
- **Total Estimated**: $55-160/month

## Scaling Considerations

### Vertical Scaling

Zeabur allows you to scale resources:

1. Go to service settings
2. Adjust CPU and memory allocation
3. Changes apply automatically

### Horizontal Scaling

For high traffic:

1. Consider using Celery workers for background tasks
2. Add load balancing (contact Zeabur support)
3. Optimize database queries and caching

## Support and Resources

- **Zeabur Documentation**: https://zeabur.com/docs
- **Zeabur Discord**: Join for community support
- **GitHub Issues**: Report bugs in your repository

## Next Steps

After deployment:

1. Test all endpoints and admin panel
2. Configure WordPress integration
3. Set up monitoring and alerts
4. Run initial content generation tests
5. Monitor costs and optimize as needed
