# PostgreSQL Setup and Reset Guide

## Why PostgreSQL is Needed

Yes, **PostgreSQL is essential** for Y-Connect WhatsApp Bot. It stores:
- Government scheme information (name, description, eligibility, benefits)
- Scheme translations in multiple languages
- Scheme metadata (status, dates, authority)
- Scheme documents for RAG retrieval

## Local Development Setup

### Option 1: Reset PostgreSQL Password (macOS)

If you have PostgreSQL installed locally and forgot the password:

```bash
# 1. Stop PostgreSQL service
brew services stop postgresql@14

# 2. Start PostgreSQL in single-user mode (no authentication)
postgres --single -D /opt/homebrew/var/postgresql@14 postgres

# 3. In the postgres prompt, reset the password:
ALTER USER postgres WITH PASSWORD 'your_new_password';

# 4. Exit (Ctrl+D) and restart PostgreSQL normally
brew services start postgresql@14

# 5. Test the connection
psql -U postgres -h localhost
```

### Option 2: Use Docker (Recommended for Development)

This is the easiest way - no local PostgreSQL installation needed:

```bash
# 1. Create .env file from example
cp .env.example .env

# 2. Edit .env and set a PostgreSQL password
nano .env
# Set: POSTGRES_PASSWORD=your_secure_password_here

# 3. Start only PostgreSQL and Redis
docker-compose up -d postgres redis

# 4. Verify PostgreSQL is running
docker-compose ps

# 5. Connect to PostgreSQL
docker exec -it y-connect-postgres psql -U postgres -d y_connect
```

### Option 3: Fresh PostgreSQL Installation (macOS)

```bash
# 1. Install PostgreSQL
brew install postgresql@14

# 2. Initialize database cluster
initdb /opt/homebrew/var/postgresql@14

# 3. Start PostgreSQL
brew services start postgresql@14

# 4. Create database and user
createdb y_connect
psql -d y_connect

# 5. In psql, set password:
ALTER USER postgres WITH PASSWORD 'your_password';
```

## Reset PostgreSQL Database (Clear All Data)

### If using Docker:

```bash
# Option A: Remove and recreate the database
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS y_connect;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE y_connect;"

# Option B: Remove the volume and restart (complete reset)
docker-compose down
docker volume rm y-connect_postgres-data
docker-compose up -d postgres redis

# Option C: Run the initialization script
docker-compose exec postgres psql -U postgres -d y_connect -f /docker-entrypoint-initdb.d/init_db.sql
```

### If using local PostgreSQL:

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS y_connect;"
psql -U postgres -c "CREATE DATABASE y_connect;"

# Run initialization script
psql -U postgres -d y_connect -f scripts/init_db.sql
```

## Update .env File

Edit your `.env` file with the correct credentials:

```bash
# For Docker setup
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=y_connect
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here  # Change this!

# For local PostgreSQL (same settings)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=y_connect
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here  # Change this!
```

## Verify Database Connection

```bash
# Test connection with Python
python -c "
from app.database import check_connection
if check_connection():
    print('✓ Database connection successful!')
else:
    print('✗ Database connection failed!')
"

# Or run the database tests
pytest tests/test_database_layer.py -v
```

## AWS Deployment - PostgreSQL Options

For AWS deployment, you have several options:

### Option 1: Amazon RDS PostgreSQL (Recommended)

**Pros:**
- Fully managed (automatic backups, updates, scaling)
- High availability with Multi-AZ
- Automated monitoring and alerting
- Easy to scale

**Setup:**
1. Go to AWS RDS Console
2. Create Database → PostgreSQL
3. Choose instance type (t3.micro for dev, t3.medium+ for production)
4. Set master password
5. Configure VPC and security groups
6. Enable automated backups
7. Get the endpoint URL

**Update .env for RDS:**
```bash
POSTGRES_HOST=your-db-instance.xxxxx.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=y_connect
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_rds_master_password
```

**Cost Estimate:**
- t3.micro (dev): ~$15/month
- t3.medium (production): ~$60/month
- Storage: $0.115/GB/month

### Option 2: Amazon Aurora PostgreSQL

**Pros:**
- Better performance than RDS
- Serverless option available
- Auto-scaling storage
- Better for high-traffic applications

**Cost Estimate:**
- Aurora Serverless v2: Pay per ACU (starts at ~$0.12/hour)
- Good for variable workloads

### Option 3: Self-Managed PostgreSQL on EC2

**Pros:**
- Full control
- Lower cost for small deployments
- Can use Docker Compose

**Cons:**
- You manage backups, updates, security
- More maintenance overhead

**Setup:**
```bash
# On EC2 instance
docker-compose up -d postgres redis qdrant
```

### Option 4: Amazon Lightsail Database

**Pros:**
- Simplest setup
- Predictable pricing
- Good for small to medium apps

**Cost Estimate:**
- $15/month (1GB RAM, 40GB storage)
- $30/month (2GB RAM, 80GB storage)

## Recommended AWS Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Cloud                            │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   ECS/EKS    │      │  RDS Postgres│                │
│  │  (FastAPI)   │─────▶│  (Managed)   │                │
│  └──────────────┘      └──────────────┘                │
│         │                                                │
│         │              ┌──────────────┐                │
│         └─────────────▶│ ElastiCache  │                │
│                        │   (Redis)    │                │
│                        └──────────────┘                │
│                                                          │
│                        ┌──────────────┐                │
│                        │   Qdrant     │                │
│                        │  (Vector DB) │                │
│                        └──────────────┘                │
└─────────────────────────────────────────────────────────┘
```

## Quick Start for AWS Deployment

### 1. Create RDS PostgreSQL Database

```bash
# Using AWS CLI
aws rds create-db-instance \
    --db-instance-identifier y-connect-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 14.7 \
    --master-username postgres \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxx \
    --db-subnet-group-name your-subnet-group \
    --backup-retention-period 7 \
    --publicly-accessible false
```

### 2. Create ElastiCache Redis

```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id y-connect-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids sg-xxxxx
```

### 3. Deploy Application to ECS

```bash
# Build and push Docker image
docker build -t y-connect-app .
docker tag y-connect-app:latest YOUR_ECR_REPO/y-connect-app:latest
docker push YOUR_ECR_REPO/y-connect-app:latest

# Update ECS task definition with RDS endpoint
# Deploy to ECS service
```

### 4. Set Environment Variables in ECS

In your ECS task definition, add:
```json
{
  "environment": [
    {"name": "POSTGRES_HOST", "value": "your-rds-endpoint.amazonaws.com"},
    {"name": "POSTGRES_PASSWORD", "value": "stored-in-secrets-manager"},
    {"name": "REDIS_HOST", "value": "your-elasticache-endpoint.amazonaws.com"}
  ]
}
```

## Security Best Practices

### 1. Use AWS Secrets Manager

```bash
# Store PostgreSQL password
aws secretsmanager create-secret \
    --name y-connect/postgres-password \
    --secret-string "your_secure_password"

# Reference in ECS task definition
{
  "secrets": [
    {
      "name": "POSTGRES_PASSWORD",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:y-connect/postgres-password"
    }
  ]
}
```

### 2. Network Security

- Place RDS in private subnet (no public access)
- Use security groups to restrict access
- Enable SSL/TLS for database connections
- Use VPC peering if needed

### 3. Database Security

```sql
-- Create application-specific user (don't use postgres user)
CREATE USER y_connect_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE y_connect TO y_connect_app;
GRANT USAGE ON SCHEMA public TO y_connect_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO y_connect_app;
```

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
docker-compose ps postgres
# or
brew services list | grep postgresql

# Check if port is open
nc -zv localhost 5432

# Check logs
docker-compose logs postgres
```

### Authentication Failed

```bash
# Verify credentials in .env
cat .env | grep POSTGRES

# Test connection manually
psql -h localhost -U postgres -d y_connect

# Reset password (see Option 1 above)
```

### Database Does Not Exist

```bash
# Create database
docker-compose exec postgres createdb -U postgres y_connect
# or
psql -U postgres -c "CREATE DATABASE y_connect;"
```

## Cost Optimization for AWS

### Development Environment
- RDS t3.micro: $15/month
- ElastiCache t3.micro: $12/month
- ECS Fargate (0.25 vCPU, 0.5GB): $10/month
- **Total: ~$40/month**

### Production Environment
- RDS t3.medium (Multi-AZ): $120/month
- ElastiCache t3.small: $25/month
- ECS Fargate (1 vCPU, 2GB, 2 tasks): $60/month
- ALB: $20/month
- **Total: ~$225/month**

### Cost Savings Tips
1. Use Reserved Instances for RDS (save 30-60%)
2. Use Aurora Serverless for variable workloads
3. Enable RDS storage autoscaling
4. Use Spot instances for non-critical workloads
5. Set up CloudWatch alarms to monitor costs

## Next Steps

1. ✅ Reset PostgreSQL password locally
2. ✅ Update .env file with correct credentials
3. ✅ Run database tests to verify connection
4. ✅ Seed database with sample schemes
5. ✅ Deploy to AWS using RDS
6. ✅ Configure security groups and secrets
7. ✅ Set up monitoring and backups
