#!/bin/bash

# Y-Connect Database Setup Script
# This script sets up PostgreSQL and Redis for local development

set -e

echo "🚀 Setting up Y-Connect databases..."

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    echo "❌ Redis is not installed. Installing via Homebrew..."
    brew install redis
else
    echo "✅ Redis is already installed"
fi

# Start Redis service
echo "🔄 Starting Redis service..."
brew services start redis

# Wait for Redis to start
sleep 2

# Check Redis connection
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Installing via Homebrew..."
    brew install postgresql@14
    brew services start postgresql@14
else
    echo "✅ PostgreSQL is already installed"
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values if not in .env
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-test_password}
POSTGRES_DB=${POSTGRES_DB:-y_connect}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

echo "🔄 Setting up PostgreSQL database..."

# Check if database exists
if psql -U $POSTGRES_USER -h $POSTGRES_HOST -lqt | cut -d \| -f 1 | grep -qw $POSTGRES_DB; then
    echo "✅ Database '$POSTGRES_DB' already exists"
else
    echo "📦 Creating database '$POSTGRES_DB'..."
    createdb -U $POSTGRES_USER -h $POSTGRES_HOST $POSTGRES_DB
    echo "✅ Database created"
fi

# Initialize database schema
echo "🔄 Initializing database schema..."
python -c "from app.database import init_database; init_database()"

echo ""
echo "✅ Database setup complete!"
echo ""
echo "📊 Connection details:"
echo "  PostgreSQL: postgresql://$POSTGRES_USER:****@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
echo "  Redis: redis://$REDIS_HOST:$REDIS_PORT/$REDIS_DB"
echo ""
echo "🧪 Run tests with: python -m pytest tests/ -v"
