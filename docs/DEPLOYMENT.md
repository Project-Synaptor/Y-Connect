# Y-Connect WhatsApp Bot - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [WhatsApp Business API Setup](#whatsapp-business-api-setup)
4. [Vector Store Setup](#vector-store-setup)
5. [LLM API Setup](#llm-api-setup)
6. [Database Setup](#database-setup)
7. [Deployment Options](#deployment-options)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [Deployment Checklist](#deployment-checklist)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended for production)
- **Storage**: Minimum 20GB available disk space
- **Network**: HTTPS-enabled domain with valid SSL certificate (for production)

### Required Accounts and API Keys

1. **WhatsApp Business API** account
2. **LLM Provider** account (OpenAI, Anthropic, or self-hosted)
3. **Vector Database** (Qdrant Cloud or self-hosted)
4. **Domain and SSL Certificate** (for webhook endpoint)

---

## Environment Variables

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Application Settings
APP_NAME=y-connect-whatsapp-bot
APP_ENV=production  # Options: development, staging, production
LOG_LEVEL=INFO      # Options: DEBUG, INFO, WARNING, ERROR

# WhatsApp Business API
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token_here
WHATSAPP_APP_SECRET=your_app_secret_here

# LLM API (OpenAI/Anthropic/Other)
LLM_PROVIDER=openai  # Options: openai, anthropic, sarvam, custom
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=gpt-4      # Options: gpt-4, gpt-3.5-turbo, claude-3-opus, etc.
LLM_API_URL=https://api.openai.com/v1

# Vector Database (Qdrant)
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_URL=http://localhost:6333  # Or Qdrant Cloud URL
VECTOR_DB_API_KEY=                   # Leave empty for local, required for cloud
VECTOR_DB_INDEX_NAME=y-connect-schemes
VECTOR_EMBEDDING_DIMENSION=384

# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=y_connect
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_postgres_password_here
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=20

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_secure_redis_password_here  # Leave empty for no auth
REDIS_SESSION_TTL=86400  # 24 hours in seconds

# Session Management
SESSION_EXPIRY_HOURS=24

# Performance Settings
MAX_CONCURRENT_SESSIONS=100
RESPONSE_TIMEOUT_SECONDS=10
RAG_TOP_K_RESULTS=5
RAG_CONFIDENCE_THRESHOLD=0.7

# Message Settings
MAX_MESSAGE_LENGTH=1600
CHUNK_SIZE_TOKENS=512
CHUNK_OVERLAP_TOKENS=50

# Monitoring (Optional)
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password_here
```

### Environment Variable Descriptions

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `APP_ENV` | Application environment | Yes | `production` |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Business API access token | Yes | - |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | Yes | - |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | Yes | - |
| `WHATSAPP_APP_SECRET` | App secret for signature verification | Yes | - |
| `LLM_API_KEY` | LLM provider API key | Yes | - |
| `POSTGRES_PASSWORD` | PostgreSQL database password | Yes | - |
| `VECTOR_DB_URL` | Vector database URL | Yes | `http://localhost:6333` |
| `REDIS_PASSWORD` | Redis password (optional) | No | - |

---

## WhatsApp Business API Setup

### Step 1: Create a Meta Business Account

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app or use an existing one
3. Add the **WhatsApp** product to your app

### Step 2: Get API Credentials

1. Navigate to **WhatsApp > API Setup**
2. Copy the following credentials:
   - **Phone Number ID**: Found in the "From" section
   - **Access Token**: Temporary token (valid for 24 hours) or create a permanent token
   - **App Secret**: Found in **Settings > Basic**

### Step 3: Configure Webhook

1. In the WhatsApp dashboard, go to **Configuration > Webhook**
2. Set the webhook URL: `https://your-domain.com/webhook`
3. Set the verify token (must match `WHATSAPP_VERIFY_TOKEN` in `.env`)
4. Subscribe to the following webhook fields:
   - `messages`
   - `message_status` (optional)

### Step 4: Verify Webhook

The webhook will be automatically verified when you save the configuration. The Y-Connect application must be running and accessible at the webhook URL.

### Step 5: Add Phone Numbers

1. Add test phone numbers in the **API Setup** section
2. For production, complete the business verification process
3. Request production access from Meta

### Important Notes

- **Temporary tokens** expire after 24 hours. Generate a permanent token for production.
- **Rate limits**: WhatsApp has rate limits based on your tier (Tier 1: 1,000 messages/day).
- **Business verification** is required for production use with unlimited phone numbers.

---

## Vector Store Setup

### Option 1: Self-Hosted Qdrant (Included in Docker Compose)

The `docker-compose.yml` includes a Qdrant service that runs locally. No additional setup required.

```bash
# Qdrant will be available at:
# - HTTP API: http://localhost:6333
# - gRPC API: http://localhost:6334
```

### Option 2: Qdrant Cloud

1. Sign up at [Qdrant Cloud](https://cloud.qdrant.io/)
2. Create a new cluster
3. Copy the cluster URL and API key
4. Update `.env`:
   ```bash
   VECTOR_DB_URL=https://your-cluster.qdrant.io
   VECTOR_DB_API_KEY=your_api_key_here
   ```

### Initialize Vector Store

After deployment, run the scheme import script to populate the vector store:

```bash
# Using Docker
docker exec -it y-connect-app python scripts/import_schemes.py

# Or locally
python scripts/import_schemes.py
```

---

## LLM API Setup

### Option 1: OpenAI

1. Sign up at [OpenAI Platform](https://platform.openai.com/)
2. Create an API key in **API Keys** section
3. Update `.env`:
   ```bash
   LLM_PROVIDER=openai
   LLM_API_KEY=sk-...
   LLM_MODEL=gpt-4
   LLM_API_URL=https://api.openai.com/v1
   ```

**Recommended Models:**
- `gpt-4`: Best quality, higher cost
- `gpt-3.5-turbo`: Good balance of quality and cost

### Option 2: Anthropic Claude

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Update `.env`:
   ```bash
   LLM_PROVIDER=anthropic
   LLM_API_KEY=sk-ant-...
   LLM_MODEL=claude-3-opus-20240229
   LLM_API_URL=https://api.anthropic.com
   ```

### Option 3: Self-Hosted (Llama, Mistral, etc.)

1. Deploy a model using [Ollama](https://ollama.ai/), [vLLM](https://github.com/vllm-project/vllm), or similar
2. Update `.env`:
   ```bash
   LLM_PROVIDER=custom
   LLM_API_KEY=  # May not be required
   LLM_MODEL=llama2
   LLM_API_URL=http://your-llm-server:8000
   ```

### Cost Considerations

- **OpenAI GPT-4**: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- **OpenAI GPT-3.5**: ~$0.0015 per 1K input tokens, ~$0.002 per 1K output tokens
- **Anthropic Claude**: Similar to GPT-4 pricing
- **Self-hosted**: Infrastructure costs only

---

## Database Setup

### PostgreSQL

The PostgreSQL database is included in the Docker Compose setup. The schema will be automatically initialized on first run.

#### Manual Schema Initialization

If needed, you can manually initialize the database:

```bash
# Connect to PostgreSQL
docker exec -it y-connect-postgres psql -U postgres -d y_connect

# Run the initialization script
\i /docker-entrypoint-initdb.d/init_db.sql
```

#### Database Migrations

For schema updates, use the migration scripts in `scripts/migrations/`:

```bash
docker exec -it y-connect-app python scripts/run_migrations.py
```

### Redis

Redis is used for session management and caching. It's included in the Docker Compose setup with the following configuration:

- **Max Memory**: 256MB
- **Eviction Policy**: allkeys-lru (Least Recently Used)
- **Persistence**: RDB snapshots to `/data` volume

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

#### Production Deployment

```bash
# 1. Clone the repository
git clone https://github.com/your-org/y-connect-whatsapp-bot.git
cd y-connect-whatsapp-bot

# 2. Create and configure .env file
cp .env.example .env
nano .env  # Edit with your credentials

# 3. Build and start services
docker-compose up -d

# 4. Check service health
docker-compose ps
docker-compose logs -f app

# 5. Initialize database and vector store
docker exec -it y-connect-app python scripts/import_schemes.py
```

#### Development Deployment

```bash
# Use the development compose file
docker-compose -f docker-compose.dev.yml up

# This enables hot-reload for code changes
```

### Option 2: Kubernetes (Recommended for Large Scale)

Kubernetes manifests are available in the `k8s/` directory (to be created separately).

```bash
# Apply Kubernetes configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/qdrant.yaml
kubectl apply -f k8s/app.yaml
kubectl apply -f k8s/ingress.yaml
```

### Option 3: Cloud Platforms

#### AWS ECS/Fargate

1. Push Docker image to ECR
2. Create ECS task definition
3. Configure Application Load Balancer
4. Set up RDS for PostgreSQL
5. Use ElastiCache for Redis
6. Use Qdrant Cloud for vector store

#### Google Cloud Run

1. Push Docker image to GCR
2. Deploy to Cloud Run
3. Use Cloud SQL for PostgreSQL
4. Use Memorystore for Redis
5. Use Qdrant Cloud for vector store

#### Azure Container Instances

1. Push Docker image to ACR
2. Deploy to Container Instances
3. Use Azure Database for PostgreSQL
4. Use Azure Cache for Redis
5. Use Qdrant Cloud for vector store

---

## Monitoring and Observability

### Prometheus Metrics

The application exposes Prometheus metrics at `/metrics`:

```bash
# Access metrics
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration
- `whatsapp_messages_received_total`: Messages received
- `whatsapp_messages_sent_total`: Messages sent
- `rag_retrieval_duration_seconds`: RAG retrieval time
- `llm_generation_duration_seconds`: LLM generation time

### Grafana Dashboards

Start Grafana with monitoring profile:

```bash
docker-compose --profile monitoring up -d
```

Access Grafana at `http://localhost:3000`:
- **Username**: admin
- **Password**: Set in `GRAFANA_ADMIN_PASSWORD` env var

### Health Checks

The application provides a comprehensive health check endpoint:

```bash
# Check application health
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "timestamp": "2024-02-13T10:30:00Z",
  "components": {
    "postgres": "healthy",
    "redis": "healthy",
    "vector_store": "healthy"
  }
}
```

### Logging

Logs are written in JSON format for easy parsing:

```bash
# View application logs
docker-compose logs -f app

# View specific component logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All environment variables configured in `.env`
- [ ] WhatsApp Business API credentials obtained
- [ ] LLM API key obtained and tested
- [ ] Domain and SSL certificate configured
- [ ] Firewall rules configured (ports 80, 443, 8000)
- [ ] Database backup strategy defined
- [ ] Monitoring and alerting configured

### Deployment

- [ ] Docker and Docker Compose installed
- [ ] `.env` file created and validated
- [ ] Docker images built successfully
- [ ] All services started: `docker-compose up -d`
- [ ] Health check endpoint returns healthy status
- [ ] Database schema initialized
- [ ] Vector store populated with scheme data
- [ ] Webhook URL configured in WhatsApp dashboard
- [ ] Webhook verification successful

### Post-Deployment

- [ ] Send test message to WhatsApp bot
- [ ] Verify message processing and response
- [ ] Check logs for errors
- [ ] Monitor metrics in Grafana
- [ ] Test multi-language support
- [ ] Test scheme retrieval and RAG responses
- [ ] Verify session management and expiry
- [ ] Load test with concurrent users
- [ ] Set up automated backups
- [ ] Document incident response procedures

### Security Checklist

- [ ] HTTPS enforced for all endpoints
- [ ] Webhook signature verification enabled
- [ ] Database passwords are strong and unique
- [ ] API keys stored securely (not in code)
- [ ] Redis password configured (if exposed)
- [ ] Firewall rules restrict unnecessary access
- [ ] Regular security updates scheduled
- [ ] PII anonymization verified in logs
- [ ] Session data expiry working correctly

---

## Troubleshooting

### Common Issues

#### 1. Webhook Verification Fails

**Symptoms**: WhatsApp shows "Verification failed" error

**Solutions**:
- Verify `WHATSAPP_VERIFY_TOKEN` matches the token in WhatsApp dashboard
- Ensure application is accessible at the webhook URL
- Check application logs: `docker-compose logs app`
- Test webhook endpoint: `curl https://your-domain.com/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test`

#### 2. Database Connection Errors

**Symptoms**: Application fails to start, logs show database connection errors

**Solutions**:
- Check PostgreSQL is running: `docker-compose ps postgres`
- Verify database credentials in `.env`
- Check PostgreSQL logs: `docker-compose logs postgres`
- Ensure database is healthy: `docker exec -it y-connect-postgres pg_isready -U postgres`

#### 3. Vector Store Errors

**Symptoms**: Scheme retrieval fails, RAG errors in logs

**Solutions**:
- Check Qdrant is running: `docker-compose ps qdrant`
- Verify vector store URL in `.env`
- Check if collections exist: `curl http://localhost:6333/collections`
- Re-import schemes: `docker exec -it y-connect-app python scripts/import_schemes.py`

#### 4. LLM API Errors

**Symptoms**: Response generation fails, timeout errors

**Solutions**:
- Verify LLM API key is valid
- Check API rate limits and quotas
- Test API directly: `curl -H "Authorization: Bearer $LLM_API_KEY" https://api.openai.com/v1/models`
- Increase timeout: Set `RESPONSE_TIMEOUT_SECONDS=20` in `.env`

#### 5. High Memory Usage

**Symptoms**: Application crashes, out of memory errors

**Solutions**:
- Increase Docker memory limit
- Reduce `POSTGRES_POOL_SIZE` and `MAX_CONCURRENT_SESSIONS`
- Enable Redis memory eviction
- Monitor with: `docker stats`

#### 6. Slow Response Times

**Symptoms**: Users experience delays, timeout errors

**Solutions**:
- Check database query performance
- Verify vector store index is optimized
- Reduce `RAG_TOP_K_RESULTS` to 3
- Enable caching for frequent queries
- Scale horizontally with multiple app instances

### Getting Help

- **Documentation**: Check `docs/` directory for detailed guides
- **Logs**: Always check logs first: `docker-compose logs -f`
- **Health Check**: Verify component health: `curl http://localhost:8000/health`
- **Metrics**: Check Prometheus metrics for anomalies
- **Community**: Open an issue on GitHub

---

## Maintenance

### Regular Tasks

#### Daily
- Monitor error rates and response times
- Check disk space usage
- Review application logs for anomalies

#### Weekly
- Review and update scheme database
- Check for security updates
- Analyze user query patterns
- Review LLM API costs

#### Monthly
- Database backup verification
- Performance optimization review
- Security audit
- Update dependencies

### Backup and Recovery

#### Database Backup

```bash
# Backup PostgreSQL
docker exec y-connect-postgres pg_dump -U postgres y_connect > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
docker exec -i y-connect-postgres psql -U postgres y_connect < backup_20240213.sql
```

#### Vector Store Backup

```bash
# Backup Qdrant data
docker exec y-connect-qdrant tar -czf /tmp/qdrant_backup.tar.gz /qdrant/storage
docker cp y-connect-qdrant:/tmp/qdrant_backup.tar.gz ./qdrant_backup_$(date +%Y%m%d).tar.gz
```

### Scaling

#### Horizontal Scaling

```bash
# Scale application instances
docker-compose up -d --scale app=3

# Use a load balancer (nginx, HAProxy) to distribute traffic
```

#### Vertical Scaling

Update resource limits in `docker-compose.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Support

For additional support:
- **Email**: support@y-connect.example.com
- **Documentation**: https://docs.y-connect.example.com
- **GitHub Issues**: https://github.com/your-org/y-connect-whatsapp-bot/issues
