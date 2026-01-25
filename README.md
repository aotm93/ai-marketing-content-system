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
- Docker and Docker Compose
- OpenAI API key (or compatible provider)
- WordPress site with REST API enabled

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-marketing-system
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Configure your API keys in `.env`:
```bash
PRIMARY_AI_API_KEY=your_openai_api_key
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_PASSWORD=your_app_password
```

4. Start the system with Docker:
```bash
docker-compose up -d
```

5. Access the API:
```
http://localhost:8000
```

6. Access the Admin Panel:
```
http://localhost:8000/admin
```

## Admin Panel

The system includes a secure web-based admin panel for managing configuration without directly editing files.

### Admin Panel Features

- **Password-Protected Access**: Simple password authentication with JWT tokens
- **Configuration Management**: Update all system settings through a web interface
- **Real-time Updates**: Changes are saved to `.env` file automatically
- **Rate Limiting**: Protection against brute force attacks (5 login attempts per 5 minutes)
- **Secure Sessions**: HTTP-only cookies with configurable expiration

### Admin Setup

1. Set admin credentials in `.env`:
```bash
ADMIN_PASSWORD=your_secure_password_here
ADMIN_SESSION_SECRET=your_random_secret_key_min_32_chars
ADMIN_SESSION_EXPIRE_MINUTES=1440  # 24 hours
```

2. Generate a secure session secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

3. Access the admin panel at `http://localhost:8000/admin`

### Admin Panel Usage

1. **Login**: Enter your admin password to access the dashboard
2. **View Configuration**: All current settings are loaded automatically
3. **Update Settings**: Modify any configuration value in the form
4. **Save Changes**: Click "Save All Changes" to persist updates
5. **Restart**: Some changes require system restart to take full effect

### Security Features

- **Rate Limiting**: Login attempts limited to prevent brute force attacks
- **JWT Authentication**: Secure token-based session management
- **HTTP-Only Cookies**: Session tokens not accessible via JavaScript
- **Password Protection**: Only authorized users can access configuration
- **No Direct Access**: Admin panel requires authentication for all operations

## Configuration

### AI Provider Setup

The system supports any OpenAI-compatible API. Configure in `.env`:

```bash
# Primary Provider
PRIMARY_AI_PROVIDER=openai
PRIMARY_AI_BASE_URL=https://api.openai.com/v1
PRIMARY_AI_API_KEY=your_key
PRIMARY_AI_TEXT_MODEL=gpt-4o
PRIMARY_AI_IMAGE_MODEL=dall-e-3

# Fallback Provider (optional)
FALLBACK_AI_PROVIDER=custom
FALLBACK_AI_BASE_URL=https://your-api.com/v1
FALLBACK_AI_API_KEY=your_key
```

### WordPress Setup

1. Install Rank Math SEO plugin (or Yoast SEO/AIOSEO as alternatives)
2. Enable REST API
3. Create application password
4. Configure in `.env`

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
