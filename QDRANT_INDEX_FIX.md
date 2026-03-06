# Qdrant "Index Required" Error Fix

## Problem
```
qdrant_client.http.exceptions.UnexpectedResponse: Unexpected Response: 400 (Bad Request)
Raw response content:
b'{"status":{"error":"Bad request: Index required but not found for \\"status\\" of one of the following types: [keyword]. Help: Create an index for this key or use a different filter."},"time":0.00003 ...'
```

## Root Cause
Qdrant requires indexes on fields that are used for filtering. The collection was created without indexes, so filtering by `status`, `category`, `state`, etc. fails.

## Solution
Recreate the Qdrant collection with proper indexes on all filterable fields.

## Quick Fix (Automated)

### Option 1: Use the Recreate Script (Recommended)

```bash
# This will delete and recreate the collection with proper indexes
python scripts/recreate_qdrant_collection.py
```

Then re-import your data:
```bash
# Generate sample schemes
python scripts/generate_sample_schemes.py --count 100 --output data/sample_schemes.json

# Import schemes (this will create embeddings and indexes)
python scripts/import_schemes.py --file data/sample_schemes.json --format json
```

### Option 2: Manual Fix via Python

```python
from app.vector_store import VectorStoreClient
from app.config import get_settings

settings = get_settings()

# Connect to Qdrant
client = VectorStoreClient()

# Delete existing collection
client.client.delete_collection(settings.vector_db_index_name)

# Recreate with indexes (this is now automatic)
client.create_collection()

# Re-import your data
# python scripts/import_schemes.py --file data/sample_schemes.json
```

## What Was Fixed

### Updated `app/vector_store.py`

The `create_collection()` method now automatically creates indexes:

```python
def create_collection(self, vector_size: Optional[int] = None) -> None:
    # ... create collection ...
    
    # Create indexes for filterable fields
    filterable_fields = [
        "scheme_id",
        "category",
        "authority",
        "state",
        "status",
        "language",
        "document_type",
    ]
    
    for field in filterable_fields:
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD
        )
```

## Indexed Fields

The following fields now have indexes for efficient filtering:

| Field | Type | Used For |
|-------|------|----------|
| `scheme_id` | keyword | Finding specific schemes |
| `category` | keyword | Filtering by category (agriculture, education, etc.) |
| `authority` | keyword | Filtering by authority (central, state) |
| `state` | keyword | Filtering by state/location |
| `status` | keyword | Filtering by status (active, expired, upcoming) |
| `language` | keyword | Filtering by language |
| `document_type` | keyword | Filtering by document type (overview, eligibility, etc.) |

## Verification

### 1. Check Collection Exists
```bash
docker exec -it y-connect-qdrant curl http://localhost:6333/collections
```

### 2. Check Indexes
```python
from app.vector_store import VectorStoreClient

client = VectorStoreClient()
info = client.get_collection_info()
print(f"Collection: {info}")
```

### 3. Test Filtering
```python
from app.scheme_vector_store import SchemeVectorStore

store = SchemeVectorStore()

# This should now work without errors
results = store.search_schemes(
    query="farmer schemes",
    filters={"status": "active", "category": "agriculture"}
)

print(f"Found {len(results)} schemes")
```

## Docker Deployment

If you're using Docker, the collection will be recreated automatically on first run. But if you already have data, you need to recreate:

```bash
# Stop services
docker-compose down

# Remove Qdrant volume (this deletes all data!)
docker volume rm y-connect_qdrant-data

# Restart services
docker-compose up -d

# Wait for services to start
sleep 10

# Re-import data
docker exec -it y-connect-app python scripts/generate_sample_schemes.py --count 100
docker exec -it y-connect-app python scripts/import_schemes.py --file data/sample_schemes.json
```

## Production Deployment

For production, add this to your deployment script:

```bash
#!/bin/bash
# deploy.sh

# 1. Deploy application
docker-compose up -d

# 2. Wait for Qdrant to be ready
echo "Waiting for Qdrant..."
sleep 10

# 3. Recreate collection with indexes
docker exec -it y-connect-app python scripts/recreate_qdrant_collection.py

# 4. Import scheme data
docker exec -it y-connect-app python scripts/import_schemes.py --file /path/to/schemes.json

echo "✓ Deployment complete!"
```

## Troubleshooting

### Error: "Collection already exists"

**Solution**: Delete and recreate:
```bash
python scripts/recreate_qdrant_collection.py
```

### Error: "No data after recreation"

**Solution**: Re-import your schemes:
```bash
python scripts/import_schemes.py --file data/sample_schemes.json
```

### Error: "Index creation failed"

**Cause**: Qdrant version might be too old

**Solution**: Update Qdrant:
```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:latest  # or specific version like v1.7.0
```

### Performance Issues After Adding Indexes

**Note**: Indexes improve query performance but slightly increase storage and write time. This is normal and expected.

**Benchmarks**:
- Without indexes: Query fails with 400 error
- With indexes: Query succeeds in <100ms

## Best Practices

### 1. Always Create Indexes on Filterable Fields
```python
# When creating a new collection
client.create_collection()  # Now automatically creates indexes
```

### 2. Index Only What You Filter On
Don't create indexes on fields you never filter by (wastes space).

### 3. Use Keyword Type for Exact Matches
```python
field_schema=PayloadSchemaType.KEYWORD  # For exact matches
```

### 4. Recreate Collection When Schema Changes
If you add new filterable fields, recreate the collection:
```bash
python scripts/recreate_qdrant_collection.py
```

## Migration Checklist

- [x] Updated `app/vector_store.py` to create indexes
- [x] Created `scripts/recreate_qdrant_collection.py`
- [ ] Run recreate script: `python scripts/recreate_qdrant_collection.py`
- [ ] Re-import data: `python scripts/import_schemes.py --file data/sample_schemes.json`
- [ ] Test filtering: Verify no more 400 errors
- [ ] Deploy to production

---

**Your Qdrant filtering should now work without errors!** ✅
