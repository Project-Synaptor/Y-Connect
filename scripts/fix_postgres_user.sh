#!/bin/bash

# Fix PostgreSQL User Setup for Y-Connect
# This script creates the postgres user and sets up the database

set -e

echo "🔧 PostgreSQL User Fix Script"
echo "=============================="
echo ""

# Get current user
CURRENT_USER=$(whoami)
echo "Current macOS user: $CURRENT_USER"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL is not running. Starting it..."
    brew services start postgresql@14
    sleep 3
fi

echo "✅ PostgreSQL is running"
echo ""

# Step 1: Create postgres superuser role
echo "📝 Creating 'postgres' superuser role..."
psql -d postgres -c "CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'Yalgaar_04';" 2>/dev/null || \
psql -d postgres -c "ALTER ROLE postgres WITH PASSWORD 'Yalgaar_04';" 2>/dev/null || \
echo "Note: postgres role might already exist"

echo "✅ postgres role created/updated"
echo ""

# Step 2: Create y_connect database
echo "📝 Creating 'y_connect' database..."
psql -d postgres -c "CREATE DATABASE y_connect OWNER postgres;" 2>/dev/null || \
echo "Note: y_connect database might already exist"

echo "✅ y_connect database ready"
echo ""

# Step 3: Grant privileges
echo "📝 Setting up permissions..."
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE y_connect TO postgres;" 2>/dev/null || true

echo "✅ Permissions set"
echo ""

# Step 4: Test connection
echo "🔍 Testing connection..."
if PGPASSWORD='Yalgaar_04' psql -h localhost -U postgres -d y_connect -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Connection successful!"
    echo ""
    echo "📊 Database info:"
    PGPASSWORD='Yalgaar_04' psql -h localhost -U postgres -d y_connect -c "SELECT current_database(), current_user, version();" | head -5
else
    echo "❌ Connection failed. Trying alternative method..."
    echo ""
    
    # Alternative: Use current user to create postgres user
    echo "Creating postgres user with current user ($CURRENT_USER)..."
    createuser -s postgres 2>/dev/null || echo "postgres user exists"
    psql -d postgres -c "ALTER USER postgres WITH PASSWORD 'Yalgaar_04';"
    
    # Test again
    if PGPASSWORD='Yalgaar_04' psql -h localhost -U postgres -d y_connect -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Connection successful after fix!"
    else
        echo "❌ Still having issues. Manual steps needed."
        exit 1
    fi
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Your .env file should have:"
echo "POSTGRES_HOST=localhost"
echo "POSTGRES_PORT=5432"
echo "POSTGRES_DB=y_connect"
echo "POSTGRES_USER=postgres"
echo "POSTGRES_PASSWORD=Yalgaar_04"
echo ""
echo "💡 To connect manually:"
echo "   PGPASSWORD='Yalgaar_04' psql -h localhost -U postgres -d y_connect"
echo ""
echo "🧪 To run tests:"
echo "   pytest tests/test_database_layer.py -v"
