"""Health check module for Y-Connect WhatsApp Bot

Checks connectivity and health of all system components.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import asyncio

from app.config import get_settings
from app.alerting import alert_manager

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResult:
    """Result of a health check"""
    
    def __init__(
        self,
        component: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        """
        Initialize health check result
        
        Args:
            component: Name of the component checked
            status: Health status
            message: Optional status message
            details: Optional additional details
            response_time_ms: Response time in milliseconds
        """
        self.component = component
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """
    Performs health checks on all system components.
    
    Checks:
    - PostgreSQL database connectivity
    - Redis connectivity
    - Vector store connectivity
    - Overall system health
    """
    
    def __init__(self):
        """Initialize HealthChecker"""
        self.settings = get_settings()
        logger.info("HealthChecker initialized")
    
    async def check_postgres(self) -> HealthCheckResult:
        """
        Check PostgreSQL database connectivity
        
        Returns:
            HealthCheckResult for PostgreSQL
        """
        start_time = datetime.utcnow()
        
        try:
            # Import here to avoid circular dependencies
            from app.database import db_pool
            
            # Use the connection pool's context manager
            with db_pool.get_cursor(commit=False) as cursor:
                # Simple query to check connectivity
                cursor.execute("SELECT 1 as health_check")
                result = cursor.fetchone()
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # RealDictCursor returns dict, regular cursor returns tuple
                if result:
                    # Check if it's a dict or tuple
                    check_value = result.get('health_check', None) if isinstance(result, dict) else result[0]
                    
                    if check_value == 1:
                        return HealthCheckResult(
                            component="postgres",
                            status=HealthStatus.HEALTHY,
                            message="PostgreSQL is healthy",
                            response_time_ms=response_time
                        )
                
                return HealthCheckResult(
                    component="postgres",
                    status=HealthStatus.UNHEALTHY,
                    message="PostgreSQL query returned unexpected result"
                )
        
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            alert_manager.alert_database_unavailable("postgres", str(e))
            
            return HealthCheckResult(
                component="postgres",
                status=HealthStatus.UNHEALTHY,
                message=f"PostgreSQL connection failed: {str(e)}"
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """
        Check Redis connectivity
        
        Returns:
            HealthCheckResult for Redis
        """
        start_time = datetime.utcnow()
        
        try:
            # Import here to avoid circular dependencies
            import redis
            
            redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Ping Redis
            result = redis_client.ping()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if result:
                # Get additional info
                info = redis_client.info()
                
                return HealthCheckResult(
                    component="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis is healthy",
                    details={
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory_human": info.get("used_memory_human", "unknown")
                    },
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed"
                )
        
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            alert_manager.alert_database_unavailable("redis", str(e))
            
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}"
            )
    
    async def check_vector_store(self) -> HealthCheckResult:
        """
        Check vector store connectivity
        
        Returns:
            HealthCheckResult for vector store
        """
        start_time = datetime.utcnow()
        
        try:
            # Import here to avoid circular dependencies
            from app.vector_store import VectorStoreClient
            
            vector_store = VectorStoreClient()
            
            # Check if client is initialized
            if vector_store.client is None:
                return HealthCheckResult(
                    component="vector_store",
                    status=HealthStatus.UNHEALTHY,
                    message="Vector store client not initialized"
                )
            
            # Try to get collection info
            try:
                collection_info = vector_store.client.get_collection(
                    collection_name=vector_store.collection_name
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return HealthCheckResult(
                    component="vector_store",
                    status=HealthStatus.HEALTHY,
                    message="Vector store is healthy",
                    details={
                        "collection": vector_store.collection_name,
                        "vectors_count": collection_info.vectors_count if hasattr(collection_info, 'vectors_count') else "unknown"
                    },
                    response_time_ms=response_time
                )
            
            except Exception as e:
                # Collection might not exist yet, which is okay
                if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                    return HealthCheckResult(
                        component="vector_store",
                        status=HealthStatus.DEGRADED,
                        message=f"Vector store connected but collection not found: {vector_store.collection_name}"
                    )
                else:
                    raise
        
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            alert_manager.alert_database_unavailable("vector_store", str(e))
            
            return HealthCheckResult(
                component="vector_store",
                status=HealthStatus.UNHEALTHY,
                message=f"Vector store connection failed: {str(e)}"
            )
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Check all components and return overall health status
        
        Returns:
            Dictionary with overall health status and component details
        """
        # Run all checks concurrently
        postgres_result, redis_result, vector_store_result = await asyncio.gather(
            self.check_postgres(),
            self.check_redis(),
            self.check_vector_store(),
            return_exceptions=True
        )
        
        # Handle exceptions from gather
        if isinstance(postgres_result, Exception):
            postgres_result = HealthCheckResult(
                component="postgres",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(postgres_result)}"
            )
        
        if isinstance(redis_result, Exception):
            redis_result = HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(redis_result)}"
            )
        
        if isinstance(vector_store_result, Exception):
            vector_store_result = HealthCheckResult(
                component="vector_store",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(vector_store_result)}"
            )
        
        # Determine overall status
        results = [postgres_result, redis_result, vector_store_result]
        
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in results if r.status == HealthStatus.DEGRADED)
        
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "postgres": postgres_result.to_dict(),
                "redis": redis_result.to_dict(),
                "vector_store": vector_store_result.to_dict()
            }
        }


# Global health checker instance
health_checker = HealthChecker()
