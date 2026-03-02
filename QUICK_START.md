# Y-Connect WhatsApp Bot - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Option 1: Docker (Recommended - Easiest)

```bash
# 1. Clone and navigate to project
cd Y-Connect

# 2. Create .env file
cp .env.example .env

# 3. Edit .env and set a PostgreSQL password
nano .env
# Change: POSTGRES_PASSWORD=your_secure_password_here

# 4. Start all services
docker-compose up -d

# 5. Wait for services to start (30 seconds)
sleep 30

# 6. Check if everything is running
docker-compose ps

# 7. Run tests
pytest tests/ --ignore=tests/test_database_layer.py -v

# 8. Access the application
curl http://localhost:8000/health
```

### Option 2: Local Development

```bash
# 1. Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# 2. Create database
createdb y_connect

# 3. Set PostgreSQL password
psql -d postgres -c "ALTER USER postgres WITH PASSWORD 'your_password';"

# 4. Create .env file
cp .env.example .env
nano .env  # Update POSTGRES_PASSWORD

# 5. Install Python dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Run tests
pytest tests/ -v

# 7. Start the application
uvicorn app.main:app --reload
```

## 🔧 Reset PostgreSQL

### If using Docker:

```bash
# Run the reset script
./scripts/reset_postgres.sh

# Or manually:
docker-compose down
docker volume rm y-connect_postgres-data
docker-compose up -d postgres redis
```

### If using local PostgreSQL:

```bash
# Run the reset script
./scripts/reset_postgres.sh

# Or manually reset password:
brew services stop postgresql@14
postgres --single -D /opt/homebrew/var/postgresql@14 postgres
# In postgres prompt: ALTER USER postgres WITH PASSWORD 'new_password';
# Exit with Ctrl+D
brew services start postgresql@14
```

## ☁️ Deploy to AWS

### Prerequisites
- AWS Account
- AWS CLI configured
- Docker installed

### Quick Deploy (Using RDS)

```bash
# 1. Create RDS PostgreSQL
aws rds create-db-instance \
    --db-instance-identifier y-connect-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username postgres \
    --master-user-password YOUR_PASSWORD \
    --allocated-storage 20

# 2. Create ElastiCache Redis
aws elasticache create-cache-cluster \
    --cache-cluster-id y-connect-redis \
    --cache-node-type cache.t3.micro \
    --engine redis

# 3. Build and push Docker image
aws ecr create-repository --repository-name y-connect-app
docker build -t y-connect-app .
docker tag y-connect-app:latest YOUR_ECR_REPO/y-connect-app:latest
docker push YOUR_ECR_REPO/y-connect-app:latest

# 4. Deploy to ECS
# See docs/AWS_DEPLOYMENT.md for detailed steps
```

## 📚 Documentation

- **PostgreSQL Setup**: `docs/POSTGRESQL_SETUP.md`
- **AWS Deployment**: `docs/AWS_DEPLOYMENT.md`
- **Test Results**: `test_results_summary.md`
- **Requirements**: `.kiro/specs/y-connect-whatsapp-bot/requirements.md`
- **Design**: `.kiro/specs/y-connect-whatsapp-bot/design.md`
- **Tasks**: `.kiro/specs/y-connect-whatsapp-bot/tasks.md`

## 🧪 Run Tests

```bash
# All tests (fast - 8 seconds)
pytest tests/ --ignore=tests/test_database_layer.py -v

# With database tests (requires PostgreSQL)
pytest tests/ -v

# Specific test file
pytest tests/test_language_detector.py -v

# Property-based tests only
pytest tests/test_*_properties.py -v
```

## 🔍 Verify Setup

```bash
# Check PostgreSQL connection
docker-compose exec postgres psql -U postgres -d y_connect -c "SELECT version();"

# Check Redis connection
docker-compose exec redis redis-cli ping

# Check application health
curl http://localhost:8000/health

# View logs
docker-compose logs -f app
```

## 💰 AWS Cost Estimates

### Development (~$50/month)
- RDS t3.micro: $15
- ElastiCache t3.micro: $12
- ECS Fargate: $10
- ALB: $18

### Production (~$250/month)
- RDS t3.medium (Multi-AZ): $120
- ElastiCache t3.small: $25
- ECS Fargate (2 tasks): $60
- ALB: $18
- NAT Gateway: $32

## 🆘 Common Issues

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Reset database
./scripts/reset_postgres.sh
```

### Tests Failing

```bash
# Update .env with correct credentials
nano .env

# Restart services
docker-compose restart

# Run tests again
pytest tests/ -v
```

### Docker Issues

```bash
# Clean up everything
docker-compose down -v
docker system prune -a

# Start fresh
docker-compose up -d
```

## 📞 Support

For detailed guides, see:
- PostgreSQL issues: `docs/POSTGRESQL_SETUP.md`
- AWS deployment: `docs/AWS_DEPLOYMENT.md`
- Test failures: `test_results_summary.md`

## ✅ Next Steps

1. ✅ Set up PostgreSQL (local or Docker)
2. ✅ Update .env file with credentials
3. ✅ Run tests to verify setup
4. ✅ Seed database with sample schemes
5. ✅ Configure WhatsApp Business API
6. ✅ Deploy to AWS
7. ✅ Set up monitoring and alerts
