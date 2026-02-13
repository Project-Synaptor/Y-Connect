# Y-Connect Quick Start Guide

## Current Status ✅

**Checkpoint 8 Complete:** Core components are working independently!

- ✅ 134 tests passing (all business logic)
- ✅ Redis installed and running
- 🔄 PostgreSQL setup in progress (Docker recommended)

## Next Steps

### 1. Install Docker Desktop (5 minutes)

Download and install from: https://www.docker.com/products/docker-desktop

### 2. Start Databases (30 seconds)

```bash
# Start PostgreSQL and Redis containers
docker-compose -f docker-compose.test.yml up -d

# Verify containers are running
docker-compose -f docker-compose.test.yml ps
```

### 3. Initialize Database (10 seconds)

```bash
# Create database schema
python -c "from app.database import init_database; init_database()"
```

### 4. Run Full Test Suite (15 seconds)

```bash
# Run all tests
python -m pytest tests/ -v

# Expected: All 142+ tests should pass
```

## What's Working Now

### ✅ Core Components (No Infrastructure Needed)
- Data models and validation
- Language detection (10 Indian languages)
- Query processing and entity extraction
- Session management logic
- Property-based tests for correctness

### 🔄 Needs Infrastructure
- Database operations (PostgreSQL)
- Session persistence (Redis - ✅ ready)
- Vector search (Qdrant/Pinecone - not yet configured)

## Test Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run tests with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run only property-based tests
python -m pytest tests/ -k "property" -v
```

## Troubleshooting

### Docker Issues

**"Cannot connect to Docker daemon"**
- Make sure Docker Desktop is running (check menu bar)

**"Port 5432 already in use"**
```bash
# Stop local PostgreSQL
brew services stop postgresql@14
```

**"Port 6379 already in use"**
```bash
# Stop local Redis
brew services stop redis
```

### Database Issues

**"Connection refused"**
```bash
# Check if containers are running
docker-compose -f docker-compose.test.yml ps

# Restart containers
docker-compose -f docker-compose.test.yml restart
```

**"Database does not exist"**
```bash
# Reinitialize database
python -c "from app.database import init_database; init_database()"
```

## Development Workflow

1. **Make code changes**
2. **Run tests:** `python -m pytest tests/ -v`
3. **Check specific component:** `python -m pytest tests/test_<component>.py -v`
4. **Commit when tests pass**

## Documentation

- `docs/database_setup.md` - Detailed database setup guide
- `docs/checkpoint_8_summary.md` - Test results and status
- `docs/vector_store_setup.md` - Vector database configuration

## Next Task

**Task 9: Implement RAG Engine component**
- Create RAGEngine class
- Implement retrieve_schemes() using vector search
- Implement rerank_results() based on user context
- Integrate LLM for response generation

## Need Help?

Check the documentation in the `docs/` folder or review the test files in `tests/` for examples.
