# Y-Connect WhatsApp Bot - Quick Start Guide

Get Y-Connect up and running in 10 minutes!

## Prerequisites

- Docker and Docker Compose installed
- WhatsApp Business API credentials
- LLM API key (OpenAI, Anthropic, etc.)

## Quick Setup

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/y-connect-whatsapp-bot.git
cd y-connect-whatsapp-bot

# Copy environment template
cp .env.example .env
```

### 2. Edit Environment Variables

Open `.env` and set these required variables:

```bash
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_APP_SECRET=your_app_secret_here

# LLM API
LLM_API_KEY=your_llm_key_here

# Database
POSTGRES_PASSWORD=choose_secure_password
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### 4. Initialize Data

```bash
# Import government schemes
docker exec -it y-connect-app python scripts/import_schemes.py

# Verify setup
curl http://localhost:8000/health
```

### 5. Configure WhatsApp Webhook

1. Go to your WhatsApp Business dashboard
2. Navigate to Configuration > Webhook
3. Set webhook URL: `https://your-domain.com/webhook`
4. Set verify token (same as `WHATSAPP_VERIFY_TOKEN` in `.env`)
5. Subscribe to `messages` field

### 6. Test the Bot

Send a message to your WhatsApp Business number:

```
Hello
```

You should receive a welcome message!

## Development Mode

For local development with hot-reload:

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up

# Code changes will automatically reload
```

## Common Commands

```bash
# View logs
docker-compose logs -f app

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and restart
git pull
docker-compose up -d --build

# Access database
docker exec -it y-connect-postgres psql -U postgres -d y_connect

# Access Redis
docker exec -it y-connect-redis redis-cli
```

## Monitoring

Access monitoring dashboards:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Verify .env file
cat .env

# Check port conflicts
netstat -an | grep -E '8000|5432|6379|6333'
```

### Webhook verification fails

```bash
# Test webhook endpoint
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test"

# Should return: test
```

### Database connection errors

```bash
# Check PostgreSQL health
docker exec -it y-connect-postgres pg_isready -U postgres

# Restart database
docker-compose restart postgres
```

## Next Steps

- Read the full [Deployment Guide](DEPLOYMENT.md)
- Configure [Monitoring and Alerts](MONITORING.md)
- Review [Security Best Practices](SECURITY.md)
- Explore [API Documentation](API.md)

## Support

Need help? Check:
- [Troubleshooting Guide](DEPLOYMENT.md#troubleshooting)
- [GitHub Issues](https://github.com/your-org/y-connect-whatsapp-bot/issues)
- [Documentation](https://docs.y-connect.example.com)
