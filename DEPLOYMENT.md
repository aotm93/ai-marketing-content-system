# Deployment Guide

## Overview

This guide covers deploying the AI Marketing Content System with a streamlined configuration process.
The system is designed to minimize environment variable dependencies. Most configurations are managed via the Admin Panel.

## Prerequisites

1. **PostgreSQL Database**
2. **Redis Cache** (Optional, but recommended for background tasks)
3. **Python 3.10+**

## Minimal Environment Configuration

Only the following environment variables are strictly required for deployment.
All other settings (including WordPress credentials, API keys, etc.) can be configured in the Admin Panel after deployment.

### Required Variables

```bash
# Database Connection
DATABASE_URL=postgresql://user:password@hostname:5432/dbname

# Admin Security (Initial Setup)
ADMIN_PASSWORD=your_secure_admin_password_here
ADMIN_SESSION_SECRET=your_random_secret_key_here_min_32_chars

# System Basics
ENVIRONMENT=production
PORT=8080
```

### Optional Variables (Can be set in Admin Panel later)

These are NO LONGER REQUIRED in the environment but can still be set if preferred.

```bash
# OpenAI / AI Provider
PRIMARY_AI_API_KEY=...

# WordPress
WORDPRESS_URL=...
WORDPRESS_USERNAME=...
WORDPRESS_PASSWORD=...

# Redis
REDIS_URL=...
```

## Deployment Steps

1. **Build Dashboard UI**
   The Next.js dashboard needs to be built and exported before the container handles it.
   ```bash
   cd src/dashboard
   npm install
   npm run build
   cd ../..
   ```

2. **Build Container**
   ```bash
   docker build -t ai-marketing-system .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     -p 8080:8080 \
     -e DATABASE_URL=postgresql://... \
     -e ADMIN_PASSWORD=secure_pass \
     -e ADMIN_SESSION_SECRET=secret_key \
     ai-marketing-system
   ```

3. **Configure System**
   - Navigate to `/admin`
   - Login with your `ADMIN_PASSWORD`
   - Go to **Configuration** tab
   - Enter your WordPress credentials, AI API Keys, and other settings.
   - Click **Save**. The system will apply these settings immediately without redeployment.

## CI/CD Integration

Since the configuration is stored in the database, your CI/CD pipeline (e.g., GitHub Actions, Zeabur, Railway) only needs to provide the database connection string and admin secrets. You do not need to update deployment secrets when you change an API key or WordPress password.

## Troubleshooting

- **Database Connection**: Ensure `DATABASE_URL` is correct. The app will fail to start if it cannot connect to the DB.
- **Admin Login**: If you forget the `ADMIN_PASSWORD`, you can reset it by updating the environment variable and restarting the service.
