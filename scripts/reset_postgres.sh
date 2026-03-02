#!/bin/bash

# Y-Connect PostgreSQL Reset Script
# This script helps reset PostgreSQL database for local development

set -e

echo "🔄 Y-Connect PostgreSQL Reset Script"
echo "======================================"
echo ""

# Check if running with Docker or local PostgreSQL
read -p "Are you using Docker? (y/n): " use_docker

if [ "$use_docker" = "y" ] || [ "$use_docker" = "Y" ]; then
    echo ""
    echo "📦 Docker Mode Selected"
    echo ""
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ docker-compose not found. Please install Docker Desktop."
        exit 1
    fi
    
    echo "Select reset option:"
    echo "1. Drop and recreate database (keeps container)"
    echo "2. Remove volume and restart (complete reset)"
    echo "3. Just restart PostgreSQL container"
    read -p "Enter option (1-3): " option
    
    case $option in
        1)
            echo ""
            echo "🗑️  Dropping and recreating database..."
            docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS y_connect;" || true
            docker-compose exec postgres psql -U postgres -c "CREATE DATABASE y_connect;"
            echo "✅ Database recreated"
            
            # Run initialization script if exists
            if [ -f "scripts/init_db.sql" ]; then
                echo "📝 Running initialization script..."
                docker-compose exec -T postgres psql -U postgres -d y_connect < scripts/init_db.sql
                echo "✅ Database initialized"
            fi
            ;;
        2)
            echo ""
            echo "🗑️  Removing volume and restarting..."
            docker-compose down
            docker volume rm y-connect_postgres-data 2>/dev/null || true
            docker-compose up -d postgres redis
            echo "⏳ Waiting for PostgreSQL to start..."
            sleep 5
            echo "✅ PostgreSQL reset complete"
            ;;
        3)
            echo ""
            echo "🔄 Restarting PostgreSQL..."
            docker-compose restart postgres
            echo "⏳ Waiting for PostgreSQL to start..."
            sleep 3
            echo "✅ PostgreSQL restarted"
            ;;
        *)
            echo "❌ Invalid option"
            exit 1
            ;;
    esac
    
    echo ""
    echo "🔍 Testing connection..."
    if docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        echo ""
        echo "📊 Database info:"
        docker-compose exec postgres psql -U postgres -c "\l" | grep y_connect || echo "Database: y_connect"
    else
        echo "❌ PostgreSQL is not responding"
        exit 1
    fi
    
    echo ""
    echo "💡 To connect to PostgreSQL:"
    echo "   docker-compose exec postgres psql -U postgres -d y_connect"
    
else
    echo ""
    echo "💻 Local PostgreSQL Mode Selected"
    echo ""
    
    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        echo "❌ PostgreSQL not found. Please install it first:"
        echo "   brew install postgresql@14"
        exit 1
    fi
    
    # Check if PostgreSQL is running
    if ! pg_isready -h localhost > /dev/null 2>&1; then
        echo "⚠️  PostgreSQL is not running. Starting it..."
        brew services start postgresql@14
        sleep 3
    fi
    
    echo "Select reset option:"
    echo "1. Drop and recreate database"
    echo "2. Reset postgres user password"
    echo "3. Create database if not exists"
    read -p "Enter option (1-3): " option
    
    case $option in
        1)
            echo ""
            read -p "Enter PostgreSQL password: " -s pg_password
            echo ""
            echo "🗑️  Dropping and recreating database..."
            PGPASSWORD=$pg_password psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS y_connect;" || true
            PGPASSWORD=$pg_password psql -U postgres -h localhost -c "CREATE DATABASE y_connect;"
            echo "✅ Database recreated"
            
            # Run initialization script if exists
            if [ -f "scripts/init_db.sql" ]; then
                echo "📝 Running initialization script..."
                PGPASSWORD=$pg_password psql -U postgres -h localhost -d y_connect -f scripts/init_db.sql
                echo "✅ Database initialized"
            fi
            ;;
        2)
            echo ""
            echo "🔐 Resetting postgres user password..."
            echo ""
            echo "⚠️  This requires stopping PostgreSQL and starting in single-user mode."
            echo "   Follow these steps:"
            echo ""
            echo "1. Stop PostgreSQL:"
            echo "   brew services stop postgresql@14"
            echo ""
            echo "2. Start in single-user mode:"
            echo "   postgres --single -D /opt/homebrew/var/postgresql@14 postgres"
            echo ""
            echo "3. In the postgres prompt, run:"
            echo "   ALTER USER postgres WITH PASSWORD 'your_new_password';"
            echo ""
            echo "4. Exit (Ctrl+D) and restart:"
            echo "   brew services start postgresql@14"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        3)
            echo ""
            read -p "Enter PostgreSQL password: " -s pg_password
            echo ""
            echo "📝 Creating database if not exists..."
            PGPASSWORD=$pg_password psql -U postgres -h localhost -c "CREATE DATABASE y_connect;" 2>/dev/null || echo "Database already exists"
            echo "✅ Done"
            ;;
        *)
            echo "❌ Invalid option"
            exit 1
            ;;
    esac
    
    echo ""
    echo "🔍 Testing connection..."
    if pg_isready -h localhost > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
    else
        echo "❌ PostgreSQL is not responding"
        exit 1
    fi
    
    echo ""
    echo "💡 To connect to PostgreSQL:"
    echo "   psql -U postgres -h localhost -d y_connect"
fi

echo ""
echo "🎉 Reset complete!"
echo ""
echo "📝 Next steps:"
echo "1. Update your .env file with the correct password"
echo "2. Run: pytest tests/test_database_layer.py -v"
echo "3. Seed the database: python scripts/seed_database.py"
