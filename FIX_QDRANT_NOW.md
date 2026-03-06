# Fix Qdrant 400 Error - Run This Now!

## The Problem
Your Qdrant collection doesn't have indexes, so filtering fails with:
```
400 Bad Request: Index required but not found for "status"
```

## Quick Fix (2 Steps)

### Step 1: Temporary Fix (Already Applied)
✅ I've commented out the status filter in `app/rag_engine.py` so your app works NOW.

**Restart your app:**
```bash
# If using Docker
docker-compose restart app

# If running locally
# Just restart your Python process
```

Your app should now work, but without status filtering (will return active AND expired schemes).

### Step 2: Permanent Fix (Run When Ready)

**Option A: Recreate Collection (Deletes Data)**
```bash
# This will delete all existing data and recreate with indexes
python scripts/recreate_qdrant_collection.py

# Then re-import your data
python scripts/generate_sample_schemes.py --count 100
python scripts/import_schemes.py --file data/sample_schemes.json
```

**Option B: Add Indexes to Existing Collection (Keeps Data)**
```bash
# Run this Python script to add indexes without deleting data
python -c "
from app.vector_store import VectorStoreClient
from qdrant_client.models import PayloadSchemaType

client = VectorStoreClient()

# Add indexes to existing collection
fields = ['scheme_id', 'category', 'authority', 'state', 'status', 'language', 'document_type']

for field in fields:
    try:
        client.client.create_payload_index(
            collection_name=client.collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f'✓ Created index for: {field}')
    except Exception as e:
        print(f'⚠ Could not create index for {field}: {e}')

print('✓ Done! Indexes created.')
"
```

### Step 3: Re-enable Status Filter

After running Step 2 (either Option A or B), uncomment the status filter:

**Edit `app/rag_engine.py` line ~300:**
```python
# Change this:
# filters["status"] = SchemeStatus.ACTIVE.value

# To this:
filters["status"] = SchemeStatus.ACTIVE.value
```

**Then restart:**
```bash
docker-compose restart app
```

## Which Option Should I Choose?

### Choose Option A (Recreate) if:
- ✅ You don't have important data yet
- ✅ You're still in development
- ✅ You want a clean start

### Choose Option B (Add Indexes) if:
- ✅ You have data you want to keep
- ✅ You're in production
- ✅ Re-importing data is difficult

## Verify It Works

```bash
# Test the pipeline
python -c "
import asyncio
from app.yconnect_pipeline import process_whatsapp_message

async def test():
    response = await process_whatsapp_message(
        'Show me farmer schemes',
        '+919876543210'
    )
    print(response)

asyncio.run(test())
"
```

## Current Status

✅ **Temporary fix applied** - Your app works now (without status filtering)  
⏳ **Permanent fix needed** - Run Step 2 when ready  
⏳ **Re-enable filter** - Run Step 3 after Step 2

## Quick Commands Reference

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check Qdrant logs
docker logs y-connect-qdrant

# Check app logs
docker logs y-connect-app | tail -50

# Restart app
docker-compose restart app

# Full restart
docker-compose down && docker-compose up -d
```

---

**Your app should work NOW with the temporary fix!** 🎉

Run the permanent fix when you're ready to enable status filtering.
