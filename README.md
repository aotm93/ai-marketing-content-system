# AI Marketing Content System

Autonomous multi-agent system for generating marketing content and driving organic traffic to WordPress e-commerce stores.

## Overview

This system uses collaborative AI agents to autonomously research, strategize, and execute content marketing campaigns. Designed specifically for wholesale bottle packaging businesses, it can be adapted to any e-commerce niche.

## Key Features

- **Multi-Agent Architecture**: Specialized AI agents work together like a marketing team
- **Autonomous Operation**: Minimal human intervention required
- **Flexible AI Providers**: Support for any OpenAI-compatible API
- **Modular Design**: Easy to extend with plugins
- **Event-Driven**: Loose coupling between components
- **WordPress Integration**: Direct publishing to WordPress sites

## Architecture

### AI Agents

1. **Orchestrator Agent** - Strategic decision maker and coordinator
2. **Market Researcher Agent** - Analyzes trends and competitors
3. **Keyword Strategist Agent** - Discovers and prioritizes keywords
4. **Content Creator Agent** - Generates SEO-optimized articles
5. **Media Creator Agent** - Creates images and infographics
6. **Publish Manager Agent** - Publishes content to WordPress

## Deployment

### Production Deployment (Zeabur)

For production deployment with automatic GitHub integration, see the comprehensive [Deployment Guide](DEPLOYMENT.md).

**Quick Deploy to Zeabur:**

1. Push your code to GitHub
2. Sign up at [Zeabur](https://zeabur.com)
3. Create a new project and add services (PostgreSQL, Redis, Git)
4. Configure environment variables
5. Zeabur automatically deploys on every push to main branch

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database
- WordPress site with Rank Math SEO plugin
- OpenAI API key (or compatible provider) - can be configured after deployment

### Simplified Installation

**New in v2.0**: Minimal configuration required! Only database and admin password needed to start.

1. Clone the repository:
```bash
git clone https://github.com/aotm93/ai-marketing-content-system.git
cd ai-marketing-content-system
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Configure minimal required variables in `.env`:
```bash
# Only these two are required!
DATABASE_URL=postgresql://user:password@localhost:5432/ai_marketing
ADMIN_PASSWORD=your_secure_admin_password_here
```

4. Start the system with Docker:
```bash
docker-compose up -d
```

5. Access the Admin Panel and configure AI/WordPress settings:
```
http://localhost:8000/admin
```

**Note**: AI API keys and WordPress configuration are now set through the admin panel UI, not environment variables!

## Admin Panel

The system includes a secure web-based admin panel for managing all configuration through a user-friendly interface.

### Admin Panel Features

- **Password-Protected Access**: Simple password authentication with JWT tokens
- **Configuration Management**: Update AI, WordPress, and system settings through web interface
- **Auto-Generated Secrets**: Session secrets are automatically generated if not provided
- **Real-time Updates**: Changes are saved to `.env` file automatically
- **Rate Limiting**: Protection against brute force attacks (5 login attempts per 5 minutes)
- **Secure Sessions**: HTTP-only cookies with configurable expiration

### Admin Setup

1. Set admin password in `.env` (only required variable):
```bash
ADMIN_PASSWORD=your_secure_password_here
```

2. (Optional) Session secret auto-generates, but you can set your own:
```bash
# Auto-generated if not set
ADMIN_SESSION_SECRET=your_random_secret_key_min_32_chars
ADMIN_SESSION_EXPIRE_MINUTES=1440  # 24 hours
```

3. Access the admin panel at `http://localhost:8000/admin`

### Admin Panel Usage

1. **Login**: Enter your admin password to access the dashboard
2. **Configure AI Provider**: Set your OpenAI API key, base URL, and models
3. **Configure WordPress**: Set your WordPress URL, username, and app password
4. **Configure SEO**: Verify Rank Math SEO plugin settings
5. **Save Changes**: All changes are persisted automatically
6. **Restart**: Some changes may require system restart to take full effect

### Security Features

- **Rate Limiting**: Login attempts limited to prevent brute force attacks
- **JWT Authentication**: Secure token-based session management
- **HTTP-Only Cookies**: Session tokens not accessible via JavaScript
- **Password Protection**: Only authorized users can access configuration
- **No Direct Access**: Admin panel requires authentication for all operations

## Configuration

### Environment Variables

**Minimal Required Configuration:**

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/ai_marketing
ADMIN_PASSWORD=your_secure_admin_password_here

# Optional (auto-generated if not set)
ADMIN_SESSION_SECRET=auto_generated_on_startup
```

**All other settings are configured through the admin panel UI.**

### AI Provider Setup

Configure through the admin panel after deployment:

1. Log in to admin panel at `/admin`
2. Navigate to AI Provider settings
3. Enter your configuration:
   - Provider: OpenAI (or compatible)
   - Base URL: `https://api.openai.com/v1`
   - API Key: Your OpenAI API key
   - Text Model: `gpt-4o`
   - Image Model: `dall-e-3`
4. (Optional) Configure fallback provider
5. Save changes

### WordPress Setup

**This system uses Rank Math SEO plugin by default.**

1. Install and activate Rank Math SEO plugin on your WordPress site
2. Enable WordPress REST API (enabled by default)
3. Create an application password:
   - Go to WordPress Admin → Users → Profile
   - Scroll to "Application Passwords"
   - Create new password named "AI Marketing System"
   - Copy the generated password
4. Configure in admin panel:
   - WordPress URL: `https://your-site.com`
   - Username: Your WordPress username
   - Password: The application password from step 3
   - SEO Plugin: `rankmath` (default)

For detailed Rank Math SEO setup instructions, see [docs/WORDPRESS_RANKMATH_SETUP.md](docs/WORDPRESS_RANKMATH_SETUP.md)

## Usage

### Basic Workflow

1. **Analyze Product Catalog**
```bash
curl -X POST http://localhost:8000/api/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "orchestrator",
    "task_type": "analyze_catalog",
    "data": {
      "products": ["glass bottles", "plastic bottles", "metal bottles"]
    }
  }'
```

2. **Discover Keywords**
```bash
curl -X POST http://localhost:8000/api/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "keyword_strategist",
    "task_type": "discover_keywords",
    "data": {
      "products": ["glass bottles wholesale"]
    }
  }'
```

3. **Create Content**
```bash
curl -X POST http://localhost:8000/api/v1/content/create \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "wholesale glass bottles for cosmetics",
    "products": ["glass-bottle-100ml", "glass-bottle-250ml"],
    "content_type": "blog_post"
  }'
```

## Project Structure

```
ai-marketing-system/
├── src/
│   ├── agents/              # AI Agent implementations
│   │   ├── orchestrator.py
│   │   ├── market_researcher.py
│   │   ├── keyword_strategist.py
│   │   ├── content_creator.py
│   │   ├── media_creator.py
│   │   └── publish_manager.py
│   ├── core/                # Core system components
│   │   ├── ai_provider.py
│   │   ├── event_bus.py
│   │   └── plugin_manager.py
│   ├── models/              # Database models
│   ├── api/                 # REST API endpoints
│   └── config/              # Configuration
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Development

### Running Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn src.api.main:app --reload
```

### Running Tests

```bash
pytest tests/
```

## Cost Estimation

### Monthly Operating Costs

- **AI Services**: $50-100/month (50 articles)
- **Keyword Research API**: $20-50/month
- **Infrastructure**: $50-100/month
- **Total**: $120-250/month

## Success Metrics

Target results within 6 months:
- 300%+ increase in organic traffic
- 50+ keywords in top 10
- 5%+ CTR from blog to products
- Cost per visitor < $0.50

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
