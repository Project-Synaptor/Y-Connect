# Qdrant 401 Unauthorized Fix

## Problem
Qdrant container was throwing `401 Unauthorized` errors because the client wasn't passing connection credentials properly.

## What Was Fixed

### 1. Updated `app/vector_store.py`
- Added `import os` to read environment variables
- Updated `VectorStoreClient.__init__()` to properly read credentials:
  ```python
  # Get URL from parameter, env var, or config (in that order)
  self.url = url or os.getenv("QDRANT_URL") or settings.vector_db_url
  
  # Get API key from parameter or env var (in that order)
  self.api_key = api_key or os.getenv("QDRANT_API_KEY")
  
  # Initialize Qdrant client with credentials
  self.client = QdrantClient(
      url=self.url,
      api_key=self.api_key
  )
  ```

### 2. Updated `.env`
Added explicit Qdrant credentials:
```bash
# Qdrant Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

### 3. Updated `.env.example`
Added Qdrant credentials with helpful comments:
```bash
# Qdrant Vector Database
# For local Docker: http://qdrant:6333 (in docker-compose) or http://localhost:6333 (local dev)
# For Qdrant Cloud: https://your-cluster.qdrant.io
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

### 4. Updated `docker-compose.yml`
Added Qdrant environment variables to the app service:
```yaml
# Qdrant (explicit credentials)
- QDRANT_URL=http://qdrant:6333
- QDRANT_API_KEY=${QDRANT_API_KEY:-}
```

## Configuration Options

### Local Development (No Authentication)
```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

### Docker Compose (No Authentication)
```bash
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
```

### Qdrant Cloud (With Authentication)
```bash
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your_api_key_here
```

### Local Qdrant with API Key
```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_local_api_key
```

## How to Use

### 1. Update Your .env File

For local development:
```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

For Docker:
```bash
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
```

For Qdrant Cloud:
```bash
QDRANT_URL=https://xyz-abc-123.qdrant.io
QDRANT_API_KEY=your_qdrant_cloud_api_key
```

### 2. Restart Services

```bash
# If using Docker
docker-compose down
docker-compose up -d

# If running locally
# Just restart your app
```

### 3. Verify Connection

```python
from app.vector_store import VectorStoreClient

# Test connection
client = VectorStoreClient()
info = client.get_collection_info()
print(f"Connected to Qdrant: {info}")
```

## Credential Priority

The client checks for credentials in this order:

1. **Function parameters** (when creating VectorStoreClient directly)
2. **Environment variables** (QDRANT_URL, QDRANT_API_KEY)
3. **Config settings** (from settings.vector_db_url)

Example:
```python
# Option 1: Use environment variables (recommended)
client = VectorStoreClient()

# Option 2: Pass explicitly
client = VectorStoreClient(
    url="http://localhost:6333",
    api_key="your_key"
)

# Option 3: Mix (url from env, key explicit)
client = VectorStoreClient(api_key="your_key")
```

## Troubleshooting

### Error: "401 Unauthorized"

**Cause**: API key is required but not provided

**Solution**: 
1. Check if your Qdrant instance requires authentication
2. Add `QDRANT_API_KEY` to .env
3. Restart the application

### Error: "Connection refused"

**Cause**: Wrong URL or Qdrant not running

**Solution**:
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check Qdrant logs
docker logs y-connect-qdrant

# Verify URL in .env matches your setup
# Local dev: http://localhost:6333
# Docker: http://qdrant:6333
# Cloud: https://your-cluster.qdrant.io
```

### Error: "Collection not found"

**Cause**: Collection hasn't been created yet

**Solution**:
```python
from app.vector_store import VectorStoreClient

client = VectorStoreClient()
client.create_collection()  # Creates the collection
```

Or run the import script:
```bash
python scripts/import_schemes.py --file data/sample_schemes.json
```

## Security Best Practices

### 1. Never Commit API Keys
- ✅ `.env` is in `.gitignore`
- ✅ Use `.env.example` for templates
- ❌ Don't hardcode keys in code

### 2. Use Different Keys for Environments
```bash
# Development
QDRANT_API_KEY=dev_key_here

# Production
QDRANT_API_KEY=prod_key_here
```

### 3. Rotate Keys Regularly
- Change API keys every 90 days
- Use different keys for each environment
- Revoke old keys after rotation

### 4. Use Secrets Management in Production
For AWS deployment:
```bash
# Store in AWS Secrets Manager
aws secretsmanager create-secret \
    --name y-connect/qdrant-api-key \
    --secret-string "your_api_key"

# Reference in ECS task definition
"secrets": [
    {
        "name": "QDRANT_API_KEY",
        "valueFrom": "arn:aws:secretsmanager:region:account:secret:y-connect/qdrant-api-key"
    }
]
```

## Testing

### Test Local Connection
```bash
# Start Qdrant
docker-compose up -d qdrant

# Test connection
python -c "
from app.vector_store import VectorStoreClient
client = VectorStoreClient()
print('✓ Connected to Qdrant')
print(f'URL: {client.url}')
print(f'API Key: {\"***\" if client.api_key else \"None\"}')
"
```

### Test with API Key
```bash
# Set API key
export QDRANT_API_KEY=test_key

# Test connection
python -c "
from app.vector_store import VectorStoreClient
client = VectorStoreClient()
print(f'API Key configured: {bool(client.api_key)}')
"
```

## Migration from Old Config

If you were using the old config format:
```bash
# Old (still works for backward compatibility)
VECTOR_DB_URL=http://localhost:6333
VECTOR_DB_API_KEY=

# New (recommended)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

Both work! The new format is checked first, then falls back to the old format.

---

**Your Qdrant connection should now work without 401 errors!** ✅
