# Y-Connect WhatsApp Bot - Environment Variables Reference

Complete reference for all environment variables used in Y-Connect.

## Application Settings

### APP_NAME
- **Description**: Application name for logging and identification
- **Type**: String
- **Required**: No
- **Default**: `y-connect-whatsapp-bot`
- **Example**: `y-connect-whatsapp-bot`

### APP_ENV
- **Description**: Application environment
- **Type**: String (enum)
- **Required**: Yes
- **Default**: `production`
- **Options**: `development`, `staging`, `production`
- **Example**: `production`
- **Notes**: Affects logging verbosity, HTTPS enforcement, and error details

### LOG_LEVEL
- **Description**: Logging level
- **Type**: String (enum)
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example**: `INFO`
- **Notes**: Use `DEBUG` for development, `INFO` or `WARNING` for production

---

## WhatsApp Business API

### WHATSAPP_API_URL
- **Description**: WhatsApp Business API base URL
- **Type**: URL
- **Required**: Yes
- **Default**: `https://graph.facebook.com/v18.0`
- **Example**: `https://graph.facebook.com/v18.0`
- **Notes**: Update version number as needed

### WHATSAPP_ACCESS_TOKEN
- **Description**: WhatsApp Business API access token
- **Type**: String (secret)
- **Required**: Yes
- **Default**: None
- **Example**: `EAABsbCS1iHgBO7ZC9FZCxqwXjPzZCZBr...`
- **Notes**: Generate from Meta Business dashboard. Use permanent token for production.

### WHATSAPP_PHONE_NUMBER_ID
- **Description**: WhatsApp phone number ID
- **Type**: String
- **Required**: Yes
- **Default**: None
- **Example**: `123456789012345`
- **Notes**: Found in WhatsApp Business API dashboard under "From" section

### WHATSAPP_VERIFY_TOKEN
- **Description**: Webhook verification token
- **Type**: String (secret)
- **Required**: Yes
- **Default**: None
- **Example**: `my_secure_verify_token_12345`
- **Notes**: Choose a random string. Must match token in WhatsApp webhook configuration.

### WHATSAPP_APP_SECRET
- **Description**: App secret for webhook signature verification
- **Type**: String (secret)
- **Required**: Yes
- **Default**: None
- **Example**: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- **Notes**: Found in Meta app dashboard under Settings > Basic

---

## LLM API Configuration

### LLM_PROVIDER
- **Description**: LLM provider name
- **Type**: String (enum)
- **Required**: Yes
- **Default**: `openai`
- **Options**: `openai`, `anthropic`, `sarvam`, `custom`
- **Example**: `openai`
- **Notes**: Determines API format and authentication method

### LLM_API_KEY
- **Description**: LLM API key
- **Type**: String (secret)
- **Required**: Yes
- **Default**: None
- **Example**: `sk-proj-abc123...` (OpenAI) or `sk-ant-abc123...` (Anthropic)
- **Notes**: Keep secure. Rotate regularly.

### LLM_MODEL
- **Description**: LLM model name
- **Type**: String
- **Required**: Yes
- **Default**: `gpt-4`
- **Example**: `gpt-4`, `gpt-3.5-turbo`, `claude-3-opus-20240229`
- **Notes**: Must be compatible with selected provider

### LLM_API_URL
- **Description**: LLM API base URL
- **Type**: URL
- **Required**: Yes
- **Default**: `https://api.openai.com/v1`
- **Example**: `https://api.openai.com/v1` or `https://api.anthropic.com`
- **Notes**: Use custom URL for self-hosted models

---

## Vector Database (Qdrant)

### VECTOR_DB_PROVIDER
- **Description**: Vector database provider
- **Type**: String
- **Required**: Yes
- **Default**: `qdrant`
- **Example**: `qdrant`
- **Notes**: Currently only Qdrant is supported

### VECTOR_DB_URL
- **Description**: Vector database URL
- **Type**: URL
- **Required**: Yes
- **Default**: `http://localhost:6333`
- **Example**: `http://localhost:6333` or `https://xyz.qdrant.io`
- **Notes**: Use `http://qdrant:6333` in Docker Compose

### VECTOR_DB_API_KEY
- **Description**: Vector database API key
- **Type**: String (secret)
- **Required**: No (Yes for Qdrant Cloud)
- **Default**: Empty
- **Example**: `abc123def456...`
- **Notes**: Required for Qdrant Cloud, optional for self-hosted

### VECTOR_DB_INDEX_NAME
- **Description**: Vector database collection/index name
- **Type**: String
- **Required**: Yes
- **Default**: `y-connect-schemes`
- **Example**: `y-connect-schemes`
- **Notes**: Collection will be created automatically if it doesn't exist

### VECTOR_EMBEDDING_DIMENSION
- **Description**: Embedding vector dimension
- **Type**: Integer
- **Required**: Yes
- **Default**: `384`
- **Example**: `384` (for all-MiniLM-L6-v2), `768` (for multilingual-e5-large)
- **Notes**: Must match the embedding model dimension

---

## PostgreSQL Database

### POSTGRES_HOST
- **Description**: PostgreSQL host
- **Type**: String
- **Required**: Yes
- **Default**: `localhost`
- **Example**: `localhost` or `postgres` (in Docker)
- **Notes**: Use service name in Docker Compose

### POSTGRES_PORT
- **Description**: PostgreSQL port
- **Type**: Integer
- **Required**: Yes
- **Default**: `5432`
- **Example**: `5432`

### POSTGRES_DB
- **Description**: PostgreSQL database name
- **Type**: String
- **Required**: Yes
- **Default**: `y_connect`
- **Example**: `y_connect`

### POSTGRES_USER
- **Description**: PostgreSQL username
- **Type**: String
- **Required**: Yes
- **Default**: `postgres`
- **Example**: `postgres`

### POSTGRES_PASSWORD
- **Description**: PostgreSQL password
- **Type**: String (secret)
- **Required**: Yes
- **Default**: None
- **Example**: `MySecureP@ssw0rd123`
- **Notes**: Use strong password. Rotate regularly.

### POSTGRES_POOL_SIZE
- **Description**: Database connection pool size
- **Type**: Integer
- **Required**: No
- **Default**: `10`
- **Example**: `10`
- **Notes**: Increase for high-traffic deployments

### POSTGRES_MAX_OVERFLOW
- **Description**: Maximum overflow connections
- **Type**: Integer
- **Required**: No
- **Default**: `20`
- **Example**: `20`
- **Notes**: Additional connections beyond pool size

---

## Redis Configuration

### REDIS_HOST
- **Description**: Redis host
- **Type**: String
- **Required**: Yes
- **Default**: `localhost`
- **Example**: `localhost` or `redis` (in Docker)

### REDIS_PORT
- **Description**: Redis port
- **Type**: Integer
- **Required**: Yes
- **Default**: `6379`
- **Example**: `6379`

### REDIS_DB
- **Description**: Redis database number
- **Type**: Integer
- **Required**: No
- **Default**: `0`
- **Example**: `0`
- **Notes**: Redis supports databases 0-15

### REDIS_PASSWORD
- **Description**: Redis password
- **Type**: String (secret)
- **Required**: No
- **Default**: Empty (no authentication)
- **Example**: `MyRedisP@ssw0rd`
- **Notes**: Recommended for production

### REDIS_SESSION_TTL
- **Description**: Session time-to-live in seconds
- **Type**: Integer
- **Required**: No
- **Default**: `86400` (24 hours)
- **Example**: `86400`
- **Notes**: Sessions expire after this duration

---

## Session Management

### SESSION_EXPIRY_HOURS
- **Description**: Session expiry time in hours
- **Type**: Integer
- **Required**: No
- **Default**: `24`
- **Example**: `24`
- **Notes**: Must align with REDIS_SESSION_TTL

---

## Performance Settings

### MAX_CONCURRENT_SESSIONS
- **Description**: Maximum concurrent user sessions
- **Type**: Integer
- **Required**: No
- **Default**: `100`
- **Example**: `100`
- **Notes**: Adjust based on server capacity

### RESPONSE_TIMEOUT_SECONDS
- **Description**: Maximum response time in seconds
- **Type**: Integer
- **Required**: No
- **Default**: `10`
- **Example**: `10`
- **Notes**: Includes RAG retrieval and LLM generation

### RAG_TOP_K_RESULTS
- **Description**: Number of top results to retrieve from vector store
- **Type**: Integer
- **Required**: No
- **Default**: `5`
- **Example**: `5`
- **Notes**: Higher values increase context but slow down processing

### RAG_CONFIDENCE_THRESHOLD
- **Description**: Minimum confidence score for retrieval results
- **Type**: Float (0.0 to 1.0)
- **Required**: No
- **Default**: `0.7`
- **Example**: `0.7`
- **Notes**: Results below this threshold are filtered out

---

## Message Settings

### MAX_MESSAGE_LENGTH
- **Description**: Maximum message length in characters
- **Type**: Integer
- **Required**: No
- **Default**: `1600`
- **Example**: `1600`
- **Notes**: WhatsApp best practice limit

### CHUNK_SIZE_TOKENS
- **Description**: Document chunk size in tokens
- **Type**: Integer
- **Required**: No
- **Default**: `512`
- **Example**: `512`
- **Notes**: For embedding generation

### CHUNK_OVERLAP_TOKENS
- **Description**: Overlap between chunks in tokens
- **Type**: Integer
- **Required**: No
- **Default**: `50`
- **Example**: `50`
- **Notes**: Maintains context across chunks

---

## Monitoring (Optional)

### GRAFANA_ADMIN_PASSWORD
- **Description**: Grafana admin password
- **Type**: String (secret)
- **Required**: No (Yes if using monitoring)
- **Default**: `admin`
- **Example**: `MyGrafanaP@ssw0rd`
- **Notes**: Change default password immediately

---

## Environment-Specific Configurations

### Development

```bash
APP_ENV=development
LOG_LEVEL=DEBUG
POSTGRES_PASSWORD=dev_password
REDIS_PASSWORD=
MAX_CONCURRENT_SESSIONS=50
```

### Staging

```bash
APP_ENV=staging
LOG_LEVEL=INFO
POSTGRES_PASSWORD=staging_secure_password
REDIS_PASSWORD=staging_redis_password
MAX_CONCURRENT_SESSIONS=75
```

### Production

```bash
APP_ENV=production
LOG_LEVEL=WARNING
POSTGRES_PASSWORD=production_very_secure_password
REDIS_PASSWORD=production_redis_password
MAX_CONCURRENT_SESSIONS=100
```

---

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong passwords** for all services (minimum 16 characters)
3. **Rotate secrets regularly** (every 90 days)
4. **Use environment-specific values** (don't reuse passwords across environments)
5. **Restrict access** to production environment variables
6. **Use secret management tools** (AWS Secrets Manager, HashiCorp Vault, etc.)
7. **Enable HTTPS** in production (`APP_ENV=production`)
8. **Set Redis password** in production
9. **Use permanent WhatsApp tokens** (not temporary 24-hour tokens)
10. **Monitor API key usage** and set up alerts for unusual activity

---

## Validation

Use this script to validate your environment configuration:

```bash
# Run validation script
python scripts/validate_env.py

# Or using Docker
docker exec -it y-connect-app python scripts/validate_env.py
```

The script checks:
- All required variables are set
- URLs are valid
- Passwords meet minimum strength requirements
- Database connections work
- API keys are valid

---

## Troubleshooting

### Missing Required Variables

**Error**: `KeyError: 'WHATSAPP_ACCESS_TOKEN'`

**Solution**: Ensure all required variables are set in `.env`

### Invalid URL Format

**Error**: `Invalid URL format for VECTOR_DB_URL`

**Solution**: URLs must include protocol (http:// or https://)

### Database Connection Failed

**Error**: `Could not connect to PostgreSQL`

**Solution**: Verify `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`

### Redis Connection Failed

**Error**: `Could not connect to Redis`

**Solution**: Check `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` (if set)

---

## Additional Resources

- [Deployment Guide](DEPLOYMENT.md)
- [Quick Start Guide](QUICK_START.md)
- [Security Best Practices](SECURITY.md)
- [Troubleshooting Guide](DEPLOYMENT.md#troubleshooting)
