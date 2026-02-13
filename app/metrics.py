"""Application metrics using Prometheus"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional
import time


# Request metrics
request_count = Counter(
    'yconnect_requests_total',
    'Total number of requests received',
    ['endpoint', 'method']
)

request_duration = Histogram(
    'yconnect_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Error metrics
error_count = Counter(
    'yconnect_errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# Language metrics
language_distribution = Counter(
    'yconnect_language_queries_total',
    'Distribution of queries by language',
    ['language']
)

# Scheme retrieval metrics
scheme_retrieval_success = Counter(
    'yconnect_scheme_retrieval_success_total',
    'Successful scheme retrievals'
)

scheme_retrieval_failure = Counter(
    'yconnect_scheme_retrieval_failure_total',
    'Failed scheme retrievals',
    ['reason']
)

scheme_retrieval_duration = Histogram(
    'yconnect_scheme_retrieval_duration_seconds',
    'Scheme retrieval duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# LLM API metrics
llm_api_calls = Counter(
    'yconnect_llm_api_calls_total',
    'Total LLM API calls',
    ['provider', 'status']
)

llm_api_duration = Histogram(
    'yconnect_llm_api_duration_seconds',
    'LLM API call duration in seconds',
    ['provider'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

llm_api_tokens = Counter(
    'yconnect_llm_api_tokens_total',
    'Total tokens used by LLM API',
    ['provider', 'token_type']
)

llm_api_cost = Counter(
    'yconnect_llm_api_cost_usd',
    'Estimated LLM API cost in USD',
    ['provider']
)

# Active sessions
active_sessions = Gauge(
    'yconnect_active_sessions',
    'Number of active user sessions'
)

# Message queue metrics
queued_messages = Gauge(
    'yconnect_queued_messages',
    'Number of messages in queue'
)

# Database connection pool metrics
db_connections_active = Gauge(
    'yconnect_db_connections_active',
    'Active database connections',
    ['database']
)

db_connections_idle = Gauge(
    'yconnect_db_connections_idle',
    'Idle database connections',
    ['database']
)

# Application info
app_info = Info(
    'yconnect_app',
    'Application information'
)


class MetricsTracker:
    """Helper class for tracking metrics with context"""
    
    def __init__(self):
        self._start_time: Optional[float] = None
    
    def track_request(self, endpoint: str, method: str = "POST"):
        """Track a request"""
        request_count.labels(endpoint=endpoint, method=method).inc()
        self._start_time = time.time()
        return self
    
    def finish_request(self, endpoint: str, method: str = "POST"):
        """Finish tracking a request"""
        if self._start_time:
            duration = time.time() - self._start_time
            request_duration.labels(endpoint=endpoint, method=method).observe(duration)
            self._start_time = None
    
    def track_error(self, error_type: str, component: str):
        """Track an error"""
        error_count.labels(error_type=error_type, component=component).inc()
    
    def track_language(self, language: str):
        """Track language usage"""
        language_distribution.labels(language=language).inc()
    
    def track_scheme_retrieval_success(self, duration: float):
        """Track successful scheme retrieval"""
        scheme_retrieval_success.inc()
        scheme_retrieval_duration.observe(duration)
    
    def track_scheme_retrieval_failure(self, reason: str):
        """Track failed scheme retrieval"""
        scheme_retrieval_failure.labels(reason=reason).inc()
    
    def track_llm_call(
        self,
        provider: str,
        status: str,
        duration: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0
    ):
        """Track LLM API call"""
        llm_api_calls.labels(provider=provider, status=status).inc()
        llm_api_duration.labels(provider=provider).observe(duration)
        
        if input_tokens > 0:
            llm_api_tokens.labels(provider=provider, token_type="input").inc(input_tokens)
        
        if output_tokens > 0:
            llm_api_tokens.labels(provider=provider, token_type="output").inc(output_tokens)
        
        if cost > 0:
            llm_api_cost.labels(provider=provider).inc(cost)
    
    def set_active_sessions(self, count: int):
        """Set active sessions count"""
        active_sessions.set(count)
    
    def set_queued_messages(self, count: int):
        """Set queued messages count"""
        queued_messages.set(count)
    
    def set_db_connections(self, database: str, active: int, idle: int):
        """Set database connection pool metrics"""
        db_connections_active.labels(database=database).set(active)
        db_connections_idle.labels(database=database).set(idle)


# Global metrics tracker instance
metrics_tracker = MetricsTracker()
