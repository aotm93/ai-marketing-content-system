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

## New Features (Traffic Acquisition)

The following features were added to enhance traffic acquisition capabilities:

### 1. DataForSEO Keyword Research

Get real search volume and keyword difficulty data from DataForSEO API.

**Setup:**
1. Sign up at [DataForSEO](https://app.dataforseo.com/register)
2. Get your API credentials (email and password)
3. Configure in Admin Panel or set environment variables:
   ```bash
   KEYWORD_API_PROVIDER=dataforseo
   KEYWORD_API_USERNAME=your_email@example.com
   KEYWORD_API_KEY=your_dataforseo_password
   ```

**API Endpoints:**
- `GET /api/v1/keywords/suggestions?seed={keyword}` - Get keyword suggestions
- `GET /api/v1/keywords/difficulty?keywords=kw1,kw2` - Get keyword difficulty scores
- `GET /api/v1/keywords/pool` - View current keyword pool
- `POST /api/v1/keywords/refresh` - Refresh keyword pool with API data

**Scheduled Job:**
- Runs weekly on Mondays at 4 AM to refresh keyword pool

### 2. DataForSEO Backlink Discovery

Discover backlink opportunities using DataForSEO Backlinks API.

**Setup:**
- Uses same DataForSEO credentials as keyword research

**Features:**
- Find unlinked brand mentions
- Discover resource page opportunities
- Track outreach status
- 50 outreach emails per day limit (with admin approval)

**Scheduled Job:**
- Runs weekly on Sundays at 3 AM to scan for new opportunities

### 3. Resend Email Marketing

Email subscription system with automated sequences.

**Setup:**
1. Sign up at [Resend](https://resend.com)
2. Get your API key from [API Keys](https://resend.com/api-keys)
3. Configure sender email (must be verified domain)
4. Set environment variables:
   ```bash
   RESEND_API_KEY=re_your_api_key_here
   RESEND_FROM_EMAIL=noreply@yourdomain.com
   ```

**WordPress Integration:**
Add the subscribe form to any WordPress page:
```
[seo_subscribe api_url="https://your-api.com"]
```

**Public API Endpoints:**
- `POST /api/v1/email/subscribe` - Subscribe to email list
- `POST /api/v1/email/unsubscribe` - Unsubscribe from email list

**Admin API Endpoints:**
- `GET /api/v1/email/subscribers` - List subscribers
- `GET /api/v1/email/sequences` - List email sequences
- `POST /api/v1/email/sequences` - Create new sequence
- `POST /api/v1/email/broadcast` - Send broadcast email

**Scheduled Job:**
- Runs hourly to process pending email sequence steps

## Troubleshooting

- **Database Connection**: Ensure `DATABASE_URL` is correct. The app will fail to start if it cannot connect to the DB.
- **Admin Login**: If you forget the `ADMIN_PASSWORD`, you can reset it by updating the environment variable and restarting the service.
- **DataForSEO API**: If keyword research returns empty results, verify your API credentials are correct and your account has sufficient credits.
- **Resend Email**: If emails fail to send, ensure your domain is verified in Resend and the API key is correct.
- **WordPress Shortcode**: If the subscribe form doesn't appear, check that the `api_url` attribute is correct and the JS file is accessible at `/static/js/subscribe.js`.
