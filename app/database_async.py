"""Async database connection and operations for Y-Connect WhatsApp Bot"""

import asyncpg
from asyncpg import Pool
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator, List, Dict, Any
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AsyncDatabasePool:
    """Async PostgreSQL connection pool manager using asyncpg"""
    
    _instance: Optional['AsyncDatabasePool'] = None
    _pool: Optional[Pool] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure single connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection pool if not already initialized"""
        pass
    
    async def _initialize_pool(self) -> None:
        """Create async PostgreSQL connection pool"""
        if self._initialized:
            return
        
        try:
            self._pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                min_size=1,
                max_size=settings.postgres_pool_size + settings.postgres_max_overflow,
                command_timeout=60
            )
            self._initialized = True
            logger.info(
                f"Async PostgreSQL connection pool created: "
                f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            )
        except Exception as e:
            logger.error(f"Failed to create async PostgreSQL connection pool: {e}")
            raise
    
    async def ensure_initialized(self) -> None:
        """Ensure pool is initialized"""
        if not self._initialized:
            await self._initialize_pool()
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator:
        """
        Acquire a connection from the pool
        
        Yields:
            asyncpg connection object
        """
        await self.ensure_initialized()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        async with self._pool.acquire() as conn:
            yield conn
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and fetch all results
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of records as dictionaries
        """
        await self.ensure_initialized()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error executing fetch query: {e}")
            raise
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Execute a SELECT query and fetch one result
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Single record as dictionary or None
        """
        await self.ensure_initialized()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error executing fetchrow query: {e}")
            raise
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute an INSERT, UPDATE, or DELETE query
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Status string from the query execution
        """
        await self.ensure_initialized()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *args)
                return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """
        Execute a query multiple times with different parameters
        
        Args:
            query: SQL query string
            args_list: List of parameter tuples
        """
        await self.ensure_initialized()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(query, args_list)
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
            raise
    
    async def close(self) -> None:
        """Close all connections in the pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Async PostgreSQL connection pool closed")
            self._pool = None
            self._initialized = False
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            await self.ensure_initialized()
            result = await self.fetchrow("SELECT 1 as test;")
            return result is not None
        except Exception as e:
            logger.error(f"Async database connection check failed: {e}")
            return False


# Global async database pool instance
async_db_pool = AsyncDatabasePool()


async def init_database_async() -> None:
    """
    Initialize database schema with tables and indexes (async version)
    
    Creates:
        - schemes table with all required fields
        - scheme_documents table for RAG content
        - indexes for performance optimization
    """
    create_schemes_table = """
    CREATE TABLE IF NOT EXISTS schemes (
        scheme_id VARCHAR(100) PRIMARY KEY,
        scheme_name VARCHAR(500) NOT NULL,
        scheme_name_translations JSONB DEFAULT '{}',
        description TEXT NOT NULL,
        description_translations JSONB DEFAULT '{}',
        category VARCHAR(100) NOT NULL,
        authority VARCHAR(100) NOT NULL,
        applicable_states TEXT[] NOT NULL,
        eligibility_criteria JSONB DEFAULT '{}',
        benefits TEXT NOT NULL,
        benefits_translations JSONB DEFAULT '{}',
        application_process TEXT NOT NULL,
        application_process_translations JSONB DEFAULT '{}',
        official_url VARCHAR(500) NOT NULL,
        helpline_numbers TEXT[] DEFAULT '{}',
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        start_date DATE,
        end_date DATE,
        last_updated TIMESTAMP DEFAULT NOW(),
        source_document_url VARCHAR(500),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    create_scheme_documents_table = """
    CREATE TABLE IF NOT EXISTS scheme_documents (
        document_id VARCHAR(100) PRIMARY KEY,
        scheme_id VARCHAR(100) NOT NULL REFERENCES schemes(scheme_id) ON DELETE CASCADE,
        language VARCHAR(10) NOT NULL,
        content TEXT NOT NULL,
        document_type VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);",
        "CREATE INDEX IF NOT EXISTS idx_schemes_status ON schemes(status);",
        "CREATE INDEX IF NOT EXISTS idx_schemes_states ON schemes USING GIN(applicable_states);",
        "CREATE INDEX IF NOT EXISTS idx_scheme_documents_scheme_id ON scheme_documents(scheme_id);",
        "CREATE INDEX IF NOT EXISTS idx_scheme_documents_language ON scheme_documents(language);",
    ]
    
    try:
        await async_db_pool.execute(create_schemes_table)
        logger.info("Schemes table created or already exists (async)")
        
        await async_db_pool.execute(create_scheme_documents_table)
        logger.info("Scheme documents table created or already exists (async)")
        
        for index_sql in create_indexes:
            await async_db_pool.execute(index_sql)
        logger.info("Database indexes created or already exist (async)")
        
        logger.info("Async database schema initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize async database schema: {e}")
        raise
