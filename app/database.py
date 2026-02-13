"""Database connection and schema management for Y-Connect WhatsApp Bot"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Generator
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabasePool:
    """PostgreSQL connection pool manager"""
    
    _instance: Optional['DatabasePool'] = None
    _pool: Optional[pool.ThreadedConnectionPool] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure single connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection pool if not already initialized"""
        # Don't auto-initialize to allow lazy loading
        pass
    
    def _initialize_pool(self) -> None:
        """Create PostgreSQL connection pool"""
        if self._initialized:
            return
        
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=settings.postgres_pool_size + settings.postgres_max_overflow,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                cursor_factory=RealDictCursor
            )
            self._initialized = True
            logger.info(
                f"PostgreSQL connection pool created: "
                f"{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            )
        except psycopg2.Error as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> Generator:
        """
        Get a connection from the pool
        
        Yields:
            psycopg2 connection object
            
        Raises:
            psycopg2.Error: If connection cannot be obtained
        """
        if not self._initialized:
            self._initialize_pool()
        
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit: bool = True) -> Generator:
        """
        Get a cursor from a pooled connection
        
        Args:
            commit: Whether to commit transaction on success
            
        Yields:
            psycopg2 cursor object
            
        Raises:
            psycopg2.Error: If cursor cannot be obtained
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"Database cursor error: {e}")
                raise
            finally:
                cursor.close()
    
    def close_all(self) -> None:
        """Close all connections in the pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("PostgreSQL connection pool closed")
            self._pool = None


# Global database pool instance
db_pool = DatabasePool()


def init_database() -> None:
    """
    Initialize database schema with tables and indexes
    
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
        with db_pool.get_cursor(commit=True) as cursor:
            # Create tables
            cursor.execute(create_schemes_table)
            logger.info("Schemes table created or already exists")
            
            cursor.execute(create_scheme_documents_table)
            logger.info("Scheme documents table created or already exists")
            
            # Create indexes
            for index_sql in create_indexes:
                cursor.execute(index_sql)
            logger.info("Database indexes created or already exist")
            
        logger.info("Database schema initialization completed successfully")
    except psycopg2.Error as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


def drop_all_tables() -> None:
    """
    Drop all tables (for testing/development only)
    
    WARNING: This will delete all data!
    """
    drop_tables = """
    DROP TABLE IF EXISTS scheme_documents CASCADE;
    DROP TABLE IF EXISTS schemes CASCADE;
    """
    
    try:
        with db_pool.get_cursor(commit=True) as cursor:
            cursor.execute(drop_tables)
        logger.warning("All database tables dropped")
    except psycopg2.Error as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def check_connection() -> bool:
    """
    Check if database connection is working
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with db_pool.get_cursor(commit=False) as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            return result is not None
    except psycopg2.Error as e:
        logger.error(f"Database connection check failed: {e}")
        return False
