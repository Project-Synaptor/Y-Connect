# Database Setup Guide

## Overview

Y-Connect requires PostgreSQL and Redis for full functionality. This guide covers setup options for local development and testing.

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))

### Steps

1. **Start the databases:**
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

3. **Initialize the database schema:**
   ```bash
   python -c "from app.database import init_database; init_database()"
   ```

4. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

5. **Stop the databases when done:**
   ```bash
   docker-compose -f docker-compose.test.yml down
   ```

## Alternative: Local Installation

### Redis Setup (macOS)

```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

### PostgreSQL Setup (macOS)

```bash
# Install PostgreSQL
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Create database
createdb y_connect

# Set password (if needed)
psql postgres -c "ALTER USER postgres WITH PASSWORD 'test_password';"
```

## Environment Configuration

Ensure your `.env` file has the correct database credentials:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=y_connect
POSTGRES_USER=postgres
POSTGRES_PASSWORD=test_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

## Troubleshooting

### PostgreSQL Connection Issues

**Error: "password authentication failed"**

Solution 1: Update pg_hba.conf to use trust authentication:
```bash
# Edit the file
nano /opt/homebrew/var/postgresql@14/pg_hba.conf

# Change 'md5' or 'scram-sha-256' to 'trust' for local connections
# Then restart PostgreSQL
brew services restart postgresql@14
```

Solution 2: Set a password for the postgres user:
```bash
psql postgres -c "ALTER USER postgres WITH PASSWORD 'test_password';"
```

### Redis Connection Issues

**Error: "Connection refused"**

```bash
# Check if Redis is running
brew services list | grep redis

# Start Redis if not running
brew services start redis

# Test connection
redis-cli ping
```

### Docker Issues

**Error: "Cannot connect to Docker daemon"**

- Ensure Docker Desktop is running
- Check Docker Desktop status in the menu bar

**Error: "Port already in use"**

```bash
# Stop conflicting services
brew services stop postgresql@14
brew services stop redis

# Or use different ports in docker-compose.test.yml
```

## Database Schema

The database schema is automatically created when you run `init_database()`. It includes:

- `schemes` table: Government scheme information
- `scheme_documents` table: Scheme content for RAG retrieval
- Indexes for efficient querying

## Test Data

To populate the database with test data:

```bash
# Run the seeding script (when available)
python scripts/seed_test_data.py
```

## Health Checks

Verify database connectivity:

```python
from app.database import check_connection
from app.session_store import RedisSessionStore

# Check PostgreSQL
assert check_connection(), "PostgreSQL connection failed"

# Check Redis
session_store = RedisSessionStore()
assert session_store.check_connection(), "Redis connection failed"
```

## Production Considerations

For production deployment:

1. Use managed database services (AWS RDS, Azure Database, etc.)
2. Enable SSL/TLS for database connections
3. Use strong passwords and rotate them regularly
4. Set up database backups
5. Configure connection pooling appropriately
6. Monitor database performance and logs
