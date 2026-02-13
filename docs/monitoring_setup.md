# Monitoring and Observability Setup

This document describes the monitoring and observability features implemented for the Y-Connect WhatsApp Bot.

## Overview

The system includes comprehensive monitoring with:
- **Prometheus metrics** for application performance tracking
- **Alerting system** for proactive issue detection
- **Health checks** for component availability monitoring

## Metrics

### Prometheus Metrics Endpoint

Access metrics at: `GET /metrics`

The endpoint exposes Prometheus-formatted metrics that can be scraped by Prometheus server.

### Available Metrics

#### Request Metrics
- `yconnect_requests_total` - Total number of requests (by endpoint, method)
- `yconnect_request_duration_seconds` - Request duration histogram (by endpoint, method)

#### Error Metrics
- `yconnect_errors_total` - Total errors (by error_type, component)

#### Language Metrics
- `yconnect_language_queries_total` - Query distribution by language

#### Scheme Retrieval Metrics
- `yconnect_scheme_retrieval_success_total` - Successful retrievals
- `yconnect_scheme_retrieval_failure_total` - Failed retrievals (by reason)
- `yconnect_scheme_retrieval_duration_seconds` - Retrieval duration histogram

#### LLM API Metrics
- `yconnect_llm_api_calls_total` - Total LLM API calls (by provider, status)
- `yconnect_llm_api_duration_seconds` - LLM API call duration (by provider)
- `yconnect_llm_api_tokens_total` - Token usage (by provider, token_type)
- `yconnect_llm_api_cost_usd` - Estimated API costs (by provider)

#### Session Metrics
- `yconnect_active_sessions` - Current active sessions
- `yconnect_queued_messages` - Messages in queue

#### Database Metrics
- `yconnect_db_connections_active` - Active database connections (by database)
- `yconnect_db_connections_idle` - Idle database connections (by database)

### Using Metrics

```python
from app.metrics import metrics_tracker

# Track a request
tracker = metrics_tracker.track_request("/webhook", "POST")
# ... do work ...
tracker.finish_request("/webhook", "POST")

# Track an error
metrics_tracker.track_error("validation_error", "webhook")

# Track language usage
metrics_tracker.track_language("hi")

# Track scheme retrieval
metrics_tracker.track_scheme_retrieval_success(duration=1.5)

# Track LLM call
metrics_tracker.track_llm_call(
    provider="openai",
    status="success",
    duration=2.5,
    input_tokens=100,
    output_tokens=50,
    cost=0.001
)
```

## Alerting

### Alert Thresholds

The system monitors and alerts on:

1. **High Error Rate**: >5% errors over last 100 requests
2. **Slow Response Time**: >10% of requests exceed 10 seconds
3. **Database Unavailability**: PostgreSQL, Redis, or Vector Store connection failures
4. **LLM API Failures**: Repeated failures to LLM API

### Alert Cooldown

Alerts have a 5-minute cooldown period to prevent spam. The same alert won't be triggered again within 5 minutes.

### Using Alerting

```python
from app.alerting import alert_manager

# Track request errors (automatic alerting)
alert_manager.track_request_error(is_error=True)

# Track response times (automatic alerting)
alert_manager.track_response_time(duration=12.5)

# Manual alerts
alert_manager.alert_database_unavailable("postgres", "Connection refused")
alert_manager.alert_llm_api_failure("openai", "Timeout", failure_count=3)

# Register custom alert handler
def my_alert_handler(alert):
    print(f"Alert: {alert.name} - {alert.message}")

alert_manager.register_alert_handler(my_alert_handler)
```

### Alert Handlers

By default, alerts are logged. You can register custom handlers to:
- Send emails
- Post to Slack/Discord
- Trigger PagerDuty incidents
- Send SMS notifications

## Health Checks

### Health Check Endpoint

Access health status at: `GET /health`

Returns:
- **200 OK** if all components are healthy
- **503 Service Unavailable** if any component is unhealthy

### Response Format

```json
{
  "status": "healthy",
  "timestamp": "2026-02-13T10:30:00Z",
  "components": {
    "postgres": {
      "component": "postgres",
      "status": "healthy",
      "message": "PostgreSQL is healthy",
      "response_time_ms": 5.2,
      "timestamp": "2026-02-13T10:30:00Z"
    },
    "redis": {
      "component": "redis",
      "status": "healthy",
      "message": "Redis is healthy",
      "details": {
        "connected_clients": 2,
        "used_memory_human": "1.5M"
      },
      "response_time_ms": 2.1,
      "timestamp": "2026-02-13T10:30:00Z"
    },
    "vector_store": {
      "component": "vector_store",
      "status": "healthy",
      "message": "Vector store is healthy",
      "details": {
        "collection": "y_connect_schemes",
        "vectors_count": 1500
      },
      "response_time_ms": 8.3,
      "timestamp": "2026-02-13T10:30:00Z"
    }
  }
}
```

### Health Status Levels

- **healthy**: Component is fully operational
- **degraded**: Component is operational but with reduced functionality
- **unhealthy**: Component is not operational

### Using Health Checks

```python
from app.health_check import health_checker

# Check all components
health_status = await health_checker.check_all()

# Check individual components
postgres_health = await health_checker.check_postgres()
redis_health = await health_checker.check_redis()
vector_store_health = await health_checker.check_vector_store()
```

## Prometheus Setup

### 1. Install Prometheus

Download from: https://prometheus.io/download/

### 2. Configure Prometheus

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'y-connect'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 3. Run Prometheus

```bash
./prometheus --config.file=prometheus.yml
```

Access Prometheus UI at: http://localhost:9090

### 4. Example Queries

```promql
# Request rate
rate(yconnect_requests_total[5m])

# Error rate
rate(yconnect_errors_total[5m]) / rate(yconnect_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(yconnect_request_duration_seconds_bucket[5m]))

# Language distribution
sum by (language) (yconnect_language_queries_total)

# LLM API success rate
rate(yconnect_llm_api_calls_total{status="success"}[5m]) / rate(yconnect_llm_api_calls_total[5m])
```

## Grafana Dashboard (Optional)

### 1. Install Grafana

Download from: https://grafana.com/grafana/download

### 2. Add Prometheus Data Source

- URL: http://localhost:9090
- Access: Server (default)

### 3. Import Dashboard

Create a dashboard with panels for:
- Request rate and error rate
- Response time percentiles (p50, p95, p99)
- Language distribution pie chart
- LLM API usage and costs
- Active sessions gauge
- Component health status

## Best Practices

1. **Monitor Regularly**: Check metrics dashboard daily
2. **Set Up Alerts**: Configure alert handlers for critical issues
3. **Review Alert History**: Analyze patterns in alert history
4. **Health Check Integration**: Use health checks in load balancers
5. **Capacity Planning**: Use metrics to plan for scaling
6. **Cost Tracking**: Monitor LLM API costs to optimize usage

## Troubleshooting

### Metrics Not Appearing

1. Check `/metrics` endpoint is accessible
2. Verify Prometheus is scraping the endpoint
3. Check Prometheus logs for errors

### Alerts Not Triggering

1. Verify alert thresholds are configured correctly
2. Check alert cooldown hasn't been triggered
3. Review alert history to see if alerts were sent

### Health Check Failing

1. Check component logs for connection errors
2. Verify database credentials and connectivity
3. Ensure all required services are running

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Monitoring](https://fastapi.tiangolo.com/advanced/monitoring/)
