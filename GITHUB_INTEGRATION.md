# GitHub Integration Checklist

This checklist ensures your repository is properly configured for automatic deployment to Zeabur.

## Repository Setup

- [ ] Repository created on GitHub
- [ ] All code pushed to main branch
- [ ] `.gitignore` configured to exclude sensitive files
- [ ] `.env` file NOT committed (only `.env.example`)

## Required Files for Deployment

- [x] `requirements.txt` - Python dependencies
- [x] `Dockerfile` - Container configuration
- [x] `zbpack.json` - Zeabur build configuration
- [x] `Procfile` - Process definition
- [x] `.env.example` - Environment variable template
- [x] `DEPLOYMENT.md` - Deployment guide

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

## Environment Variables Strategy

**SIMPLIFIED DEPLOYMENT**: We now use a database-driven configuration.

### Deployment Variables (Set in Zeabur)
Only these are strictly required for the app to start:
- [ ] `DATABASE_URL` (Auto-configured by Zeabur PostgreSQL service)
- [ ] `REDIS_URL` (Auto-configured by Zeabur Redis service)
- [ ] `ADMIN_PASSWORD` (Set manually - for initial login)
- [ ] `ADMIN_SESSION_SECRET` (Set manually - for security)

### Business Configuration (Set in Admin Panel)
Do **NOT** set these in Zeabur unless you explicitly want to override the database settings:
- `PRIMARY_AI_API_KEY`
- `WORDPRESS_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_PASSWORD`

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

## Verification Steps

After deployment:

- [ ] Visit application URL (e.g., `https://your-app.zeabur.app`)
- [ ] Check health endpoint: `/health`
- [ ] **Action Required**: Go to `/admin` -> Login -> **Configuration**
- [ ] **Action Required**: Enter WordPress & AI credentials in Admin Panel and Save
- [ ] Verify configuration is saved
- [ ] Test API endpoints

## Troubleshooting

If deployment fails:

1. Check Zeabur build logs
2. Verify `DATABASE_URL` is correct
3. Ensure `ADMIN_PASSWORD` is set
4. Review `DEPLOYMENT.md` for detailed troubleshooting
