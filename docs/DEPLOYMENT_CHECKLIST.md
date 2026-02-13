# Y-Connect WhatsApp Bot - Deployment Checklist

Use this checklist to ensure a smooth deployment of Y-Connect to production.

## Pre-Deployment Phase

### Infrastructure Setup

- [ ] **Server/Cloud Platform Selected**
  - [ ] Minimum 4GB RAM, 2 CPU cores
  - [ ] 20GB+ available disk space
  - [ ] Docker and Docker Compose installed
  - [ ] Network connectivity verified

- [ ] **Domain and SSL Certificate**
  - [ ] Domain name registered and configured
  - [ ] SSL certificate obtained (Let's Encrypt, commercial CA, etc.)
  - [ ] DNS records configured (A/AAAA records)
  - [ ] HTTPS accessible and verified

- [ ] **Firewall Configuration**
  - [ ] Port 80 (HTTP) open for Let's Encrypt verification
  - [ ] Port 443 (HTTPS) open for webhook
  - [ ] Port 8000 accessible (if not behind reverse proxy)
  - [ ] Unnecessary ports closed
  - [ ] Rate limiting configured

### API Credentials

- [ ] **WhatsApp Business API**
  - [ ] Meta Business account created
  - [ ] WhatsApp Business app created
  - [ ] Phone number added and verified
  - [ ] Access token generated (permanent, not temporary)
  - [ ] Phone number ID obtained
  - [ ] Webhook verify token created (random, secure)
  - [ ] App secret obtained
  - [ ] Business verification completed (for production)

- [ ] **LLM Provider**
  - [ ] Account created (OpenAI, Anthropic, etc.)
  - [ ] API key generated
  - [ ] Billing configured and limits set
  - [ ] Model access verified (gpt-4, claude-3, etc.)
  - [ ] Rate limits understood
  - [ ] Cost monitoring enabled

- [ ] **Vector Database**
  - [ ] Qdrant Cloud account created (or self-hosted setup)
  - [ ] Cluster created and configured
  - [ ] API key obtained (if using cloud)
  - [ ] Network access configured
  - [ ] Backup strategy defined

### Environment Configuration

- [ ] **Environment File Created**
  - [ ] `.env` file created from `.env.example`
  - [ ] All required variables set
  - [ ] Secrets are strong and unique
  - [ ] No placeholder values remaining
  - [ ] File permissions restricted (chmod 600)

- [ ] **Environment Variables Validated**
  - [ ] `APP_ENV=production`
  - [ ] `LOG_LEVEL` appropriate for production
  - [ ] WhatsApp credentials correct
  - [ ] LLM API key valid
  - [ ] Database passwords strong (16+ characters)
  - [ ] Redis password set
  - [ ] All URLs use HTTPS in production

### Security Review

- [ ] **Secrets Management**
  - [ ] No secrets in version control
  - [ ] `.env` file in `.gitignore`
  - [ ] Secrets stored securely (vault, secrets manager)
  - [ ] Access to secrets restricted
  - [ ] Secret rotation schedule defined

- [ ] **Application Security**
  - [ ] HTTPS enforcement enabled (`APP_ENV=production`)
  - [ ] Webhook signature verification enabled
  - [ ] CORS configured appropriately
  - [ ] Rate limiting enabled
  - [ ] Security headers configured
  - [ ] PII anonymization verified

- [ ] **Database Security**
  - [ ] Strong PostgreSQL password
  - [ ] Database not exposed to public internet
  - [ ] Redis password configured
  - [ ] Connection encryption enabled (if applicable)

### Data Preparation

- [ ] **Government Schemes Data**
  - [ ] Scheme data collected and validated
  - [ ] Data in correct format (JSON/CSV)
  - [ ] Translations available for all languages
  - [ ] Data placed in `data/schemes/` directory
  - [ ] Import script tested

- [ ] **Database Schema**
  - [ ] Schema initialization script reviewed
  - [ ] Migrations prepared (if needed)
  - [ ] Indexes defined for performance
  - [ ] Backup strategy defined

---

## Deployment Phase

### Initial Deployment

- [ ] **Code Deployment**
  - [ ] Repository cloned to server
  - [ ] Correct branch/tag checked out
  - [ ] `.env` file created and configured
  - [ ] File permissions set correctly

- [ ] **Docker Setup**
  - [ ] Docker images built successfully
    ```bash
    docker-compose build
    ```
  - [ ] No build errors
  - [ ] Image size reasonable (<2GB)

- [ ] **Service Startup**
  - [ ] All services started
    ```bash
    docker-compose up -d
    ```
  - [ ] PostgreSQL healthy
    ```bash
    docker-compose ps postgres
    ```
  - [ ] Redis healthy
    ```bash
    docker-compose ps redis
    ```
  - [ ] Qdrant healthy
    ```bash
    docker-compose ps qdrant
    ```
  - [ ] Application healthy
    ```bash
    docker-compose ps app
    ```

- [ ] **Health Checks**
  - [ ] Health endpoint returns 200
    ```bash
    curl http://localhost:8000/health
    ```
  - [ ] All components report healthy
  - [ ] No errors in logs
    ```bash
    docker-compose logs app
    ```

### Data Initialization

- [ ] **Database Setup**
  - [ ] Schema initialized successfully
  - [ ] Tables created
  - [ ] Indexes created
  - [ ] No migration errors

- [ ] **Vector Store Setup**
  - [ ] Collection created in Qdrant
  - [ ] Embedding model loaded
  - [ ] Test embedding generated successfully

- [ ] **Scheme Import**
  - [ ] Import script executed
    ```bash
    docker exec -it y-connect-app python scripts/import_schemes.py
    ```
  - [ ] All schemes imported
  - [ ] Embeddings generated
  - [ ] Vector store populated
  - [ ] Import logs reviewed

### WhatsApp Integration

- [ ] **Webhook Configuration**
  - [ ] Webhook URL set in WhatsApp dashboard
    - URL: `https://your-domain.com/webhook`
  - [ ] Verify token matches `.env` value
  - [ ] Webhook verification successful
  - [ ] `messages` field subscribed
  - [ ] Webhook logs show successful verification

- [ ] **Test Message**
  - [ ] Test message sent to bot
  - [ ] Message received by application
  - [ ] Webhook signature verified
  - [ ] Message processed successfully
  - [ ] Response generated
  - [ ] Response sent to WhatsApp
  - [ ] User received response

---

## Post-Deployment Phase

### Functional Testing

- [ ] **Basic Functionality**
  - [ ] Welcome message works for new users
  - [ ] Help command works
  - [ ] Category menu displays correctly
  - [ ] Scheme search works
  - [ ] Scheme details display correctly

- [ ] **Multi-Language Support**
  - [ ] Hindi queries work
  - [ ] English queries work
  - [ ] Tamil queries work
  - [ ] Telugu queries work
  - [ ] Bengali queries work
  - [ ] Marathi queries work
  - [ ] Gujarati queries work
  - [ ] Kannada queries work
  - [ ] Malayalam queries work
  - [ ] Punjabi queries work
  - [ ] Language switching works

- [ ] **RAG Functionality**
  - [ ] Scheme retrieval works
  - [ ] Responses are accurate
  - [ ] Citations included
  - [ ] Confidence threshold respected
  - [ ] Context-aware retrieval works

- [ ] **Session Management**
  - [ ] Sessions created correctly
  - [ ] Conversation context maintained
  - [ ] Sessions expire after 24 hours
  - [ ] Session data deleted on expiry

- [ ] **Error Handling**
  - [ ] Invalid messages handled gracefully
  - [ ] Multimedia messages acknowledged
  - [ ] API failures handled
  - [ ] Fallback responses work
  - [ ] Error messages user-friendly

### Performance Testing

- [ ] **Response Time**
  - [ ] 95% of requests complete within 10 seconds
  - [ ] Average response time acceptable
  - [ ] No timeout errors under normal load

- [ ] **Load Testing**
  - [ ] Tested with 50 concurrent users
  - [ ] Tested with 100 concurrent users
  - [ ] No performance degradation
  - [ ] No memory leaks
  - [ ] Database connections stable

- [ ] **Resource Usage**
  - [ ] CPU usage acceptable (<80% average)
  - [ ] Memory usage stable
  - [ ] Disk space sufficient
  - [ ] Network bandwidth adequate

### Monitoring Setup

- [ ] **Application Monitoring**
  - [ ] Prometheus metrics accessible
    ```bash
    curl http://localhost:8000/metrics
    ```
  - [ ] Key metrics tracked:
    - [ ] Request count
    - [ ] Response time
    - [ ] Error rate
    - [ ] Message count
    - [ ] RAG retrieval time
    - [ ] LLM generation time

- [ ] **Grafana Dashboards** (Optional)
  - [ ] Grafana started
    ```bash
    docker-compose --profile monitoring up -d
    ```
  - [ ] Prometheus datasource configured
  - [ ] Dashboards imported
  - [ ] Visualizations working

- [ ] **Alerting**
  - [ ] Alert rules configured
  - [ ] Alert destinations set (email, Slack, PagerDuty)
  - [ ] Test alerts sent and received
  - [ ] Alert thresholds appropriate:
    - [ ] Error rate >5% over 5 minutes
    - [ ] Response time >10s for >10% requests
    - [ ] Database unavailable
    - [ ] Redis unavailable
    - [ ] Vector store unavailable

- [ ] **Logging**
  - [ ] Logs accessible
    ```bash
    docker-compose logs -f app
    ```
  - [ ] Log level appropriate (INFO or WARNING)
  - [ ] PII anonymized in logs
  - [ ] Log rotation configured
  - [ ] Log aggregation setup (optional)

### Backup and Recovery

- [ ] **Backup Strategy**
  - [ ] PostgreSQL backup scheduled
  - [ ] Qdrant backup scheduled
  - [ ] Backup retention policy defined
  - [ ] Backup storage configured
  - [ ] Backup encryption enabled

- [ ] **Backup Testing**
  - [ ] Test backup created
  - [ ] Test restore performed
  - [ ] Restore successful
  - [ ] Data integrity verified

- [ ] **Disaster Recovery Plan**
  - [ ] Recovery procedures documented
  - [ ] RTO (Recovery Time Objective) defined
  - [ ] RPO (Recovery Point Objective) defined
  - [ ] Failover procedures tested

### Documentation

- [ ] **Operational Documentation**
  - [ ] Deployment guide reviewed
  - [ ] Environment variables documented
  - [ ] Troubleshooting guide available
  - [ ] Runbook created for common issues

- [ ] **Team Training**
  - [ ] Team trained on deployment process
  - [ ] Team trained on monitoring
  - [ ] Team trained on incident response
  - [ ] On-call rotation defined

### Security Audit

- [ ] **Security Verification**
  - [ ] HTTPS enforced
  - [ ] Webhook signature verification working
  - [ ] No secrets in logs
  - [ ] PII anonymization working
  - [ ] Session data expiry working
  - [ ] Database not publicly accessible
  - [ ] Redis not publicly accessible
  - [ ] Unnecessary ports closed

- [ ] **Compliance**
  - [ ] Data privacy requirements met
  - [ ] User consent mechanisms in place
  - [ ] Data retention policy implemented
  - [ ] Audit logging enabled

---

## Go-Live Checklist

### Final Verification

- [ ] **All Tests Passed**
  - [ ] Functional tests: ✓
  - [ ] Performance tests: ✓
  - [ ] Security tests: ✓
  - [ ] Integration tests: ✓

- [ ] **Monitoring Active**
  - [ ] Metrics collecting: ✓
  - [ ] Alerts configured: ✓
  - [ ] Dashboards accessible: ✓
  - [ ] On-call team ready: ✓

- [ ] **Backups Configured**
  - [ ] Automated backups: ✓
  - [ ] Backup tested: ✓
  - [ ] Recovery tested: ✓

- [ ] **Documentation Complete**
  - [ ] Deployment guide: ✓
  - [ ] Runbook: ✓
  - [ ] Troubleshooting guide: ✓
  - [ ] Team trained: ✓

### Go-Live

- [ ] **Soft Launch**
  - [ ] Limited user group (10-50 users)
  - [ ] Monitor for 24-48 hours
  - [ ] Collect feedback
  - [ ] Fix critical issues

- [ ] **Full Launch**
  - [ ] Announce to all users
  - [ ] Monitor closely for first week
  - [ ] Respond to user feedback
  - [ ] Optimize based on usage patterns

---

## Post-Launch

### Week 1

- [ ] **Daily Monitoring**
  - [ ] Check error rates
  - [ ] Review response times
  - [ ] Monitor resource usage
  - [ ] Review user feedback

- [ ] **Issue Resolution**
  - [ ] Address critical bugs immediately
  - [ ] Prioritize high-impact issues
  - [ ] Document common problems
  - [ ] Update troubleshooting guide

### Week 2-4

- [ ] **Performance Optimization**
  - [ ] Analyze slow queries
  - [ ] Optimize database indexes
  - [ ] Tune cache settings
  - [ ] Adjust resource limits

- [ ] **Feature Refinement**
  - [ ] Improve response quality
  - [ ] Add frequently requested features
  - [ ] Enhance error messages
  - [ ] Update scheme database

### Ongoing

- [ ] **Regular Maintenance**
  - [ ] Weekly scheme updates
  - [ ] Monthly security updates
  - [ ] Quarterly dependency updates
  - [ ] Regular backup verification

- [ ] **Continuous Improvement**
  - [ ] Analyze user queries
  - [ ] Improve RAG accuracy
  - [ ] Optimize costs
  - [ ] Enhance user experience

---

## Sign-Off

### Deployment Team

- [ ] **Technical Lead**: _________________ Date: _______
- [ ] **DevOps Engineer**: _________________ Date: _______
- [ ] **Security Engineer**: _________________ Date: _______
- [ ] **QA Engineer**: _________________ Date: _______

### Stakeholders

- [ ] **Product Manager**: _________________ Date: _______
- [ ] **Project Manager**: _________________ Date: _______

---

## Notes

Use this section to document any deployment-specific notes, issues encountered, or deviations from the standard process:

```
[Add notes here]
```

---

## Rollback Plan

In case of critical issues:

1. **Stop the application**
   ```bash
   docker-compose down
   ```

2. **Restore previous version**
   ```bash
   git checkout <previous-tag>
   docker-compose up -d
   ```

3. **Restore database** (if needed)
   ```bash
   docker exec -i y-connect-postgres psql -U postgres y_connect < backup.sql
   ```

4. **Verify rollback**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Notify stakeholders**

---

## Support Contacts

- **Technical Lead**: [email]
- **DevOps Team**: [email/slack]
- **On-Call**: [phone/pagerduty]
- **WhatsApp Support**: [contact]
- **LLM Provider Support**: [contact]
