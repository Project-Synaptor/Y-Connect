# AWS Deployment Guide for Y-Connect WhatsApp Bot

## Overview

This guide covers deploying Y-Connect to AWS using managed services for production reliability.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                               │
│                                                                  │
│  ┌──────────────┐                                               │
│  │ Application  │                                               │
│  │ Load Balancer│                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────┐                      │
│  │     ECS Fargate / EKS Cluster        │                      │
│  │  ┌────────────┐    ┌────────────┐   │                      │
│  │  │  FastAPI   │    │  FastAPI   │   │                      │
│  │  │  Container │    │  Container │   │                      │
│  │  └─────┬──────┘    └─────┬──────┘   │                      │
│  └────────┼─────────────────┼───────────┘                      │
│           │                 │                                   │
│           ├─────────────────┴──────────┐                       │
│           │                            │                        │
│           ▼                            ▼                        │
│  ┌─────────────────┐        ┌──────────────────┐              │
│  │  RDS PostgreSQL │        │  ElastiCache     │              │
│  │  (Multi-AZ)     │        │  Redis           │              │
│  └─────────────────┘        └──────────────────┘              │
│                                                                  │
│           ┌──────────────────────────────┐                     │
│           │  Qdrant Vector DB            │                     │
│           │  (ECS or EC2)                │                     │
│           └──────────────────────────────┘                     │
│                                                                  │
│  ┌──────────────────────────────────────────────┐              │
│  │  CloudWatch Logs & Metrics                   │              │
│  └──────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Docker installed locally
4. Domain name (optional, for custom domain)

## Step-by-Step Deployment

### Step 1: Set Up VPC and Networking

```bash
# Create VPC with public and private subnets
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=y-connect-vpc}]'

# Note the VPC ID from output
export VPC_ID=vpc-xxxxx

# Create public subnets (for ALB)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create private subnets (for ECS, RDS, Redis)
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.10.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.11.0/24 --availability-zone us-east-1b

# Create Internet Gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=y-connect-igw}]'
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id igw-xxxxx

# Create NAT Gateway (for private subnets to access internet)
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Create NAT Gateway in public subnet
aws ec2 create-nat-gateway --subnet-id subnet-xxxxx --allocation-id eipalloc-xxxxx
```

### Step 2: Create RDS PostgreSQL Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name y-connect-db-subnet \
    --db-subnet-group-description "Y-Connect DB Subnet Group" \
    --subnet-ids subnet-xxxxx subnet-yyyyy

# Create security group for RDS
aws ec2 create-security-group \
    --group-name y-connect-rds-sg \
    --description "Security group for Y-Connect RDS" \
    --vpc-id $VPC_ID

# Allow PostgreSQL access from ECS security group
aws ec2 authorize-security-group-ingress \
    --group-id sg-rds-xxxxx \
    --protocol tcp \
    --port 5432 \
    --source-group sg-ecs-xxxxx

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier y-connect-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 14.7 \
    --master-username postgres \
    --master-user-password "YOUR_SECURE_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-rds-xxxxx \
    --db-subnet-group-name y-connect-db-subnet \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --multi-az \
    --storage-encrypted \
    --publicly-accessible false \
    --enable-cloudwatch-logs-exports '["postgresql"]' \
    --tags Key=Name,Value=y-connect-db

# Wait for RDS to be available (takes 5-10 minutes)
aws rds wait db-instance-available --db-instance-identifier y-connect-db

# Get RDS endpoint
aws rds describe-db-instances \
    --db-instance-identifier y-connect-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

### Step 3: Create ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name y-connect-redis-subnet \
    --cache-subnet-group-description "Y-Connect Redis Subnet Group" \
    --subnet-ids subnet-xxxxx subnet-yyyyy

# Create security group for Redis
aws ec2 create-security-group \
    --group-name y-connect-redis-sg \
    --description "Security group for Y-Connect Redis" \
    --vpc-id $VPC_ID

# Allow Redis access from ECS
aws ec2 authorize-security-group-ingress \
    --group-id sg-redis-xxxxx \
    --protocol tcp \
    --port 6379 \
    --source-group sg-ecs-xxxxx

# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id y-connect-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --engine-version 7.0 \
    --num-cache-nodes 1 \
    --cache-subnet-group-name y-connect-redis-subnet \
    --security-group-ids sg-redis-xxxxx \
    --snapshot-retention-limit 5 \
    --preferred-maintenance-window "mon:05:00-mon:06:00" \
    --tags Key=Name,Value=y-connect-redis

# Get Redis endpoint
aws elasticache describe-cache-clusters \
    --cache-cluster-id y-connect-redis \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text
```

### Step 4: Store Secrets in AWS Secrets Manager

```bash
# Store PostgreSQL password
aws secretsmanager create-secret \
    --name y-connect/postgres-password \
    --description "PostgreSQL password for Y-Connect" \
    --secret-string "YOUR_SECURE_PASSWORD"

# Store WhatsApp credentials
aws secretsmanager create-secret \
    --name y-connect/whatsapp-credentials \
    --description "WhatsApp API credentials" \
    --secret-string '{
        "access_token": "YOUR_WHATSAPP_ACCESS_TOKEN",
        "phone_number_id": "YOUR_PHONE_NUMBER_ID",
        "verify_token": "YOUR_VERIFY_TOKEN",
        "app_secret": "YOUR_APP_SECRET"
    }'

# Store LLM API key
aws secretsmanager create-secret \
    --name y-connect/llm-api-key \
    --description "LLM API key" \
    --secret-string "YOUR_LLM_API_KEY"
```

### Step 5: Create ECR Repository and Push Docker Image

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name y-connect-app \
    --image-scanning-configuration scanOnPush=true

# Get ECR login
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t y-connect-app .
docker tag y-connect-app:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/y-connect-app:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/y-connect-app:latest
```

### Step 6: Create ECS Cluster and Task Definition

```bash
# Create ECS cluster
aws ecs create-cluster \
    --cluster-name y-connect-cluster \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1

# Create task execution role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file://ecs-task-execution-role.json

# Attach policies
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Register task definition (see task-definition.json below)
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

Create `task-definition.json`:

```json
{
  "family": "y-connect-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "y-connect-app",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/y-connect-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "APP_ENV", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "POSTGRES_HOST", "value": "YOUR_RDS_ENDPOINT"},
        {"name": "POSTGRES_PORT", "value": "5432"},
        {"name": "POSTGRES_DB", "value": "y_connect"},
        {"name": "POSTGRES_USER", "value": "postgres"},
        {"name": "REDIS_HOST", "value": "YOUR_REDIS_ENDPOINT"},
        {"name": "REDIS_PORT", "value": "6379"}
      ],
      "secrets": [
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:y-connect/postgres-password"
        },
        {
          "name": "WHATSAPP_ACCESS_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:y-connect/whatsapp-credentials:access_token::"
        },
        {
          "name": "LLM_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:y-connect/llm-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/y-connect-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Step 7: Create Application Load Balancer

```bash
# Create security group for ALB
aws ec2 create-security-group \
    --group-name y-connect-alb-sg \
    --description "Security group for Y-Connect ALB" \
    --vpc-id $VPC_ID

# Allow HTTP and HTTPS
aws ec2 authorize-security-group-ingress \
    --group-id sg-alb-xxxxx \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-alb-xxxxx \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# Create ALB
aws elbv2 create-load-balancer \
    --name y-connect-alb \
    --subnets subnet-public-1 subnet-public-2 \
    --security-groups sg-alb-xxxxx \
    --scheme internet-facing \
    --type application

# Create target group
aws elbv2 create-target-group \
    --name y-connect-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

### Step 8: Create ECS Service

```bash
# Create security group for ECS tasks
aws ec2 create-security-group \
    --group-name y-connect-ecs-sg \
    --description "Security group for Y-Connect ECS tasks" \
    --vpc-id $VPC_ID

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress \
    --group-id sg-ecs-xxxxx \
    --protocol tcp \
    --port 8000 \
    --source-group sg-alb-xxxxx

# Create ECS service
aws ecs create-service \
    --cluster y-connect-cluster \
    --service-name y-connect-service \
    --task-definition y-connect-app:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-private-1,subnet-private-2],securityGroups=[sg-ecs-xxxxx],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=y-connect-app,containerPort=8000" \
    --health-check-grace-period-seconds 60 \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
```

### Step 9: Set Up Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/y-connect-cluster/y-connect-service \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --resource-id service/y-connect-cluster/y-connect-service \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-name cpu-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

Create `scaling-policy.json`:

```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

### Step 10: Set Up CloudWatch Monitoring

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/y-connect-app

# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
    --alarm-name y-connect-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2

aws cloudwatch put-metric-alarm \
    --alarm-name y-connect-high-error-rate \
    --alarm-description "Alert when error rate exceeds 5%" \
    --metric-name 5XXError \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1
```

## Cost Estimation

### Development Environment (~$50/month)
- RDS t3.micro (Single-AZ): $15
- ElastiCache t3.micro: $12
- ECS Fargate (0.25 vCPU, 0.5GB, 1 task): $10
- ALB: $18
- Data transfer: $5

### Production Environment (~$250/month)
- RDS t3.medium (Multi-AZ): $120
- ElastiCache t3.small: $25
- ECS Fargate (1 vCPU, 2GB, 2 tasks): $60
- ALB: $18
- NAT Gateway: $32
- Data transfer: $20
- CloudWatch: $10

## Deployment Checklist

- [ ] VPC and subnets created
- [ ] RDS PostgreSQL database created and accessible
- [ ] ElastiCache Redis created
- [ ] Secrets stored in Secrets Manager
- [ ] Docker image built and pushed to ECR
- [ ] ECS cluster and task definition created
- [ ] ALB and target group configured
- [ ] ECS service running with desired count
- [ ] Auto scaling configured
- [ ] CloudWatch alarms set up
- [ ] Database initialized with schema
- [ ] Sample schemes seeded
- [ ] WhatsApp webhook configured
- [ ] SSL certificate configured (if using custom domain)
- [ ] Monitoring dashboard created

## Post-Deployment

### Initialize Database

```bash
# Connect to RDS via bastion host or VPN
psql -h YOUR_RDS_ENDPOINT -U postgres -d y_connect

# Run initialization script
\i scripts/init_db.sql

# Seed with sample data
python scripts/seed_database.py
```

### Configure WhatsApp Webhook

Update your WhatsApp Business API webhook URL to:
```
https://YOUR_ALB_DNS_NAME/webhook
```

Or if using custom domain:
```
https://api.yourdomain.com/webhook
```

### Monitor Application

```bash
# View ECS service status
aws ecs describe-services \
    --cluster y-connect-cluster \
    --services y-connect-service

# View logs
aws logs tail /ecs/y-connect-app --follow

# Check health
curl https://YOUR_ALB_DNS_NAME/health
```

## Troubleshooting

### Service Not Starting

```bash
# Check task logs
aws logs tail /ecs/y-connect-app --follow

# Check task status
aws ecs describe-tasks \
    --cluster y-connect-cluster \
    --tasks TASK_ID
```

### Database Connection Issues

- Verify security group allows traffic from ECS tasks
- Check RDS endpoint in environment variables
- Verify secrets are correctly configured
- Test connection from ECS task

### High Costs

- Use Fargate Spot for non-critical workloads (70% savings)
- Use RDS Reserved Instances (30-60% savings)
- Enable RDS storage autoscaling
- Set up budget alerts in AWS Cost Explorer

## Next Steps

1. Set up CI/CD pipeline with GitHub Actions or AWS CodePipeline
2. Configure custom domain with Route 53
3. Set up SSL certificate with ACM
4. Implement blue-green deployments
5. Set up disaster recovery and backups
6. Configure WAF for security
7. Set up X-Ray for distributed tracing
