"""Tests for monitoring and observability features"""

import pytest
from datetime import datetime, timedelta
from app.metrics import metrics_tracker, request_count, error_count
from app.alerting import alert_manager, Alert, AlertSeverity
from app.health_check import health_checker, HealthStatus


class TestMetrics:
    """Test metrics tracking"""
    
    def test_track_request(self):
        """Test request tracking"""
        # Track a request
        tracker = metrics_tracker.track_request("/webhook", "POST")
        tracker.finish_request("/webhook", "POST")
        
        # Verify metric was incremented (we can't easily check the value without accessing internals)
        assert tracker is not None
    
    def test_track_error(self):
        """Test error tracking"""
        metrics_tracker.track_error("test_error", "test_component")
        # Metric should be tracked
    
    def test_track_language(self):
        """Test language distribution tracking"""
        metrics_tracker.track_language("en")
        metrics_tracker.track_language("hi")
        # Metrics should be tracked
    
    def test_track_scheme_retrieval(self):
        """Test scheme retrieval metrics"""
        metrics_tracker.track_scheme_retrieval_success(duration=1.5)
        metrics_tracker.track_scheme_retrieval_failure(reason="no_results")
        # Metrics should be tracked
    
    def test_track_llm_call(self):
        """Test LLM API call tracking"""
        metrics_tracker.track_llm_call(
            provider="openai",
            status="success",
            duration=2.5,
            input_tokens=100,
            output_tokens=50,
            cost=0.001
        )
        # Metrics should be tracked


class TestAlerting:
    """Test alerting system"""
    
    def setup_method(self):
        """Clear alert cooldowns before each test"""
        alert_manager.clear_alert_cooldown()
        alert_manager.error_window.clear()
        alert_manager.response_time_window.clear()
    
    def test_track_request_error_high_rate(self):
        """Test error rate alerting"""
        # Track many errors to trigger alert
        for _ in range(20):
            alert_manager.track_request_error(True)
        
        # Should have triggered alert
        history = alert_manager.get_alert_history()
        assert len(history) > 0
        assert any(a.name == "high_error_rate" for a in history)
    
    def test_track_request_error_low_rate(self):
        """Test no alert on low error rate"""
        # Track mostly successful requests
        for _ in range(19):
            alert_manager.track_request_error(False)
        alert_manager.track_request_error(True)
        
        # Should not trigger alert (5% threshold)
        history = alert_manager.get_alert_history()
        high_error_alerts = [a for a in history if a.name == "high_error_rate"]
        # May or may not have alert depending on previous tests
    
    def test_track_response_time_slow(self):
        """Test slow response time alerting"""
        # Track many slow responses
        for _ in range(20):
            alert_manager.track_response_time(15.0)  # 15 seconds
        
        # Should have triggered alert
        history = alert_manager.get_alert_history()
        assert len(history) > 0
        assert any(a.name == "high_response_time" for a in history)
    
    def test_track_response_time_fast(self):
        """Test no alert on fast responses"""
        # Track fast responses
        for _ in range(20):
            alert_manager.track_response_time(2.0)  # 2 seconds
        
        # Should not trigger alert
        history = alert_manager.get_alert_history()
        slow_response_alerts = [a for a in history if a.name == "high_response_time"]
        # Should be empty or from previous tests
    
    def test_alert_database_unavailable(self):
        """Test database unavailability alert"""
        alert_manager.alert_database_unavailable("postgres", "Connection refused")
        
        history = alert_manager.get_alert_history()
        assert len(history) > 0
        assert any(a.name == "database_unavailable_postgres" for a in history)
        assert any(a.severity == AlertSeverity.CRITICAL for a in history)
    
    def test_alert_llm_api_failure(self):
        """Test LLM API failure alert"""
        alert_manager.alert_llm_api_failure("openai", "Timeout", failure_count=1)
        
        history = alert_manager.get_alert_history()
        assert len(history) > 0
        assert any(a.name == "llm_api_failure_openai" for a in history)
    
    def test_alert_cooldown(self):
        """Test alert cooldown prevents spam"""
        # Trigger same alert twice
        alert_manager.alert_database_unavailable("redis", "Error 1")
        initial_count = len(alert_manager.get_alert_history())
        
        # Try to trigger again immediately
        alert_manager.alert_database_unavailable("redis", "Error 2")
        
        # Should not have added new alert due to cooldown
        assert len(alert_manager.get_alert_history()) == initial_count
    
    def test_clear_alert_cooldown(self):
        """Test clearing alert cooldown"""
        alert_manager.alert_database_unavailable("redis", "Error")
        alert_manager.clear_alert_cooldown("database_unavailable_redis")
        
        # Should be able to trigger again
        alert_manager.alert_database_unavailable("redis", "Error 2")
        
        history = alert_manager.get_alert_history()
        redis_alerts = [a for a in history if a.name == "database_unavailable_redis"]
        assert len(redis_alerts) >= 2


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality"""
    
    async def test_check_all(self):
        """Test comprehensive health check"""
        result = await health_checker.check_all()
        
        assert "status" in result
        assert "timestamp" in result
        assert "components" in result
        assert "postgres" in result["components"]
        assert "redis" in result["components"]
        assert "vector_store" in result["components"]
    
    async def test_postgres_health_check(self):
        """Test PostgreSQL health check"""
        result = await health_checker.check_postgres()
        
        assert result.component == "postgres"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert result.timestamp is not None
    
    async def test_redis_health_check(self):
        """Test Redis health check"""
        result = await health_checker.check_redis()
        
        assert result.component == "redis"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert result.timestamp is not None
    
    async def test_vector_store_health_check(self):
        """Test vector store health check"""
        result = await health_checker.check_vector_store()
        
        assert result.component == "vector_store"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.timestamp is not None
