# Y-Connect Scripts

This directory contains utility scripts for managing the Y-Connect WhatsApp Bot.

## Database Scripts

### init_db.sql
Initializes the PostgreSQL database schema.

**Usage:**
```bash
# Automatically run on first PostgreSQL container start
# Or manually:
docker exec -it y-connect-postgres psql -U postgres -d y_connect -f /docker-entrypoint-initdb.d/init_db.sql
```

### import_schemes.py
Imports government schemes from JSON/CSV files into the database and vector store.

**Usage:**
```bash
# Import all schemes from data/schemes/
docker exec -it y-connect-app python scripts/import_schemes.py

# Import specific file
docker exec -it y-connect-app python scripts/import_schemes.py --file data/schemes/agriculture.json
```

### update_schemes.py
Updates existing schemes in the database and regenerates embeddings.

**Usage:**
```bash
# Update all schemes
docker exec -it y-connect-app python scripts/update_schemes.py

# Update specific scheme
docker exec -it y-connect-app python scripts/update_schemes.py --scheme-id PM-KISAN-001
```

## Maintenance Scripts

### backup_database.sh
Creates backups of PostgreSQL and Qdrant data.

**Usage:**
```bash
# Create backup
./scripts/backup_database.sh

# Backups saved to ./backups/ directory
```

### restore_database.sh
Restores database from backup.

**Usage:**
```bash
# Restore from specific backup
./scripts/restore_database.sh backups/backup_20240213.sql
```

### cleanup_sessions.py
Manually triggers session cleanup (normally runs automatically).

**Usage:**
```bash
docker exec -it y-connect-app python scripts/cleanup_sessions.py
```

## Validation Scripts

### validate_env.py
Validates environment configuration.

**Usage:**
```bash
docker exec -it y-connect-app python scripts/validate_env.py
```

### test_whatsapp_api.py
Tests WhatsApp Business API connectivity.

**Usage:**
```bash
docker exec -it y-connect-app python scripts/test_whatsapp_api.py
```

### test_llm_api.py
Tests LLM API connectivity.

**Usage:**
```bash
docker exec -it y-connect-app python scripts/test_llm_api.py
```

## Monitoring Scripts

### check_health.sh
Checks health of all services.

**Usage:**
```bash
./scripts/check_health.sh
```

### generate_report.py
Generates usage and performance reports.

**Usage:**
```bash
docker exec -it y-connect-app python scripts/generate_report.py --period weekly
```

## Development Scripts

### seed_test_data.py
Seeds database with test data for development.

**Usage:**
```bash
docker exec -it y-connect-app python scripts/seed_test_data.py
```

### reset_database.py
Resets database (WARNING: Deletes all data).

**Usage:**
```bash
docker exec -it y-connect-app python scripts/reset_database.py --confirm
```

## Notes

- All Python scripts should be run inside the Docker container
- Shell scripts can be run from the host machine
- Always backup data before running destructive operations
- Check script documentation for additional options and flags
