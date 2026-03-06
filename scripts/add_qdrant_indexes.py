#!/usr/bin/env python3
"""
Add indexes to existing Qdrant collection without deleting data

This script adds indexes to an existing collection, preserving all data.
Use this if you already have scheme data and don't want to re-import.

Usage:
    python scripts/add_qdrant_indexes.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vector_store import VectorStoreClient
from app.config import get_settings
from qdrant_client.models import PayloadSchemaType
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def add_indexes():
    """Add indexes to existing Qdrant collection"""
    
    settings = get_settings()
    
    logger.info("Connecting to Qdrant...")
    client = VectorStoreClient(
        url=settings.vector_db_url,
        api_key=settings.vector_db_api_key,
        collection_name=settings.vector_db_index_name,
        vector_size=settings.vector_embedding_dimension
    )
    
    try:
        # Check if collection exists
        collections = client.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if settings.vector_db_index_name not in collection_names:
            logger.error(f"Collection '{settings.vector_db_index_name}' does not exist!")
            logger.info("Create it first with: python scripts/recreate_qdrant_collection.py")
            sys.exit(1)
        
        # Get current collection info
        info = client.get_collection_info()
        logger.info(f"Collection '{settings.vector_db_index_name}' has {info.get('points_count', 0)} documents")
        
        # Add indexes for filterable fields
        filterable_fields = [
            "scheme_id",
            "category",
            "authority",
            "state",
            "status",
            "language",
            "document_type",
        ]
        
        logger.info(f"\nAdding indexes to {len(filterable_fields)} fields...")
        
        success_count = 0
        failed_count = 0
        
        for field in filterable_fields:
            try:
                client.client.create_payload_index(
                    collection_name=settings.vector_db_index_name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD
                )
                logger.info(f"  ✓ Created index for: {field}")
                success_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"  ✓ Index already exists for: {field}")
                    success_count += 1
                else:
                    logger.warning(f"  ✗ Could not create index for {field}: {e}")
                    failed_count += 1
        
        logger.info("\n" + "="*60)
        logger.info(f"SUCCESS: Added {success_count}/{len(filterable_fields)} indexes")
        if failed_count > 0:
            logger.warning(f"Failed: {failed_count} indexes")
        logger.info("="*60)
        
        logger.info("\nNext steps:")
        logger.info("1. Restart your application:")
        logger.info("   docker-compose restart app")
        logger.info("\n2. Re-enable status filter in app/rag_engine.py:")
        logger.info("   Uncomment: filters['status'] = SchemeStatus.ACTIVE.value")
        logger.info("\n3. Test filtering:")
        logger.info("   python -c \"from app.scheme_vector_store import SchemeVectorStore; store = SchemeVectorStore(); print(store.search_schemes('farmer schemes', filters={'status': 'active'}))\"")
        
    except Exception as e:
        logger.error(f"Error adding indexes: {e}")
        sys.exit(1)
    
    finally:
        client.close()


if __name__ == "__main__":
    add_indexes()
