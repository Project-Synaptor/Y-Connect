#!/bin/bash

# PostgreSQL Setup Script for Y-Connect
# This script creates the database and initializes the schema

set -e

echo "🔧 Setting up PostgreSQL for Y-Connect..."
echo ""

# Prompt for password if not set
if [ -z "$PGPASSWORD" ]; then
    echo "Please enter your PostgreSQL password:"
    read -s PGPASSWORD
    export PGPASSWORD
fi

# Get username (default to current user)
PGUSER=${PGUSER:-$(whoami)}
echo "Using PostgreSQL user: $PGUSER"

# Database name
DBNAME="y_connect"

# Check if database exists
if psql -U $PGUSER -lqt | cut -d \| -f 1 | grep -qw $DBNAME; then
    echo "✅ Database '$DBNAME' already exists"
else
    echo "📦 Creating database '$DBNAME'..."
    createdb -U $PGUSER $DBNAME
    echo "✅ Database created successfully"
fi

echo ""
echo "🔄 Initializing database schema..."
python -c "from app.database import init_database; init_database()"

echo ""
echo "✅ PostgreSQL setup complete!"
echo ""
echo "🧪 Running tests to verify setup..."
python -m pytest tests/test_database_layer.py -v

echo ""
echo "✅ All done! You can now run the full test suite:"
echo "   python -m pytest tests/ -v"
