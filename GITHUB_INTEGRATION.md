# GitHub Integration Checklist

This checklist ensures your repository is properly configured for automatic deployment to Zeabur.

## Repository Setup

- [ ] Repository created on GitHub
- [ ] All code pushed to main branch
- [ ] `.gitignore` configured to exclude sensitive files
- [ ] `.env` file NOT committed (only `.env.example`)

## Required Files for Zeabur

- [x] `requirements.txt` - Python dependencies
- [x] `Dockerfile` - Container configuration
- [x] `zbpack.json` - Zeabur build configuration
- [x] `Procfile` - Process definition
- [x] `.env.example` - Environment variable template
- [x] `DEPLOYMENT.md` - Deployment guide

## GitHub Actions (Optional)

- [x] `.github/workflows/zeabur-deploy.yml` - Pre-deployment checks

## Security Checklist

- [ ] No API keys in code
- [ ] No passwords in code
- [ ] No `.env` file committed
- [ ] `.gitignore` includes all sensitive files
- [ ] Admin password set in Zeabur environment variables

## Zeabur Configuration

- [ ] Zeabur account created
- [ ] GitHub account connected to Zeabur
- [ ] Repository access granted to Zeabur
- [ ] Auto-deploy enabled for main branch

## Environment Variables in Zeabur

Required variables to set in Zeabur dashboard:

- [ ] `PRIMARY_AI_API_KEY`
- [ ] `WORDPRESS_URL`
- [ ] `WORDPRESS_USERNAME`
- [ ] `WORDPRESS_PASSWORD`
- [ ] `ADMIN_PASSWORD`
- [ ] `ADMIN_SESSION_SECRET`

Auto-configured by Zeabur:
- [x] `DATABASE_URL` (from PostgreSQL service)
- [x] `REDIS_URL` (from Redis service)
- [x] `PORT` (automatically set)

## Deployment Workflow

1. **Local Development**
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. **Automatic Deployment**
   - GitHub receives push
   - Zeabur detects changes
   - Builds application
   - Deploys to production
   - Zero downtime

## Verification Steps

After deployment:

- [ ] Visit application URL (e.g., `https://your-app.zeabur.app`)
- [ ] Check health endpoint: `/health`
- [ ] Access admin panel: `/admin`
- [ ] Login with admin password
- [ ] Verify configuration in admin panel
- [ ] Test API endpoints

## Troubleshooting

If deployment fails:

1. Check Zeabur build logs
2. Verify all environment variables are set
3. Check GitHub Actions logs (if enabled)
4. Ensure all dependencies in `requirements.txt`
5. Review `DEPLOYMENT.md` for detailed troubleshooting

## Support

- Zeabur Documentation: https://zeabur.com/docs
- GitHub Issues: Report in your repository
- Deployment Guide: See `DEPLOYMENT.md`
