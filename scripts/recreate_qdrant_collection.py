#!/usr/bin/env python3
"""
Recreate Qdrant collection with proper indexes

This script deletes the existing collection and recreates it with
indexes on all filterable fields to avoid "Index required" errors.

Usage:
    python scripts/recreate_qdrant_collection.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vector_store import VectorStoreClient
from app.config import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def recreate_collection():
    """Recreate Qdrant collection with proper indexes"""
    
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
        
        if settings.vector_db_index_name in collection_names:
            logger.warning(f"Collection '{settings.vector_db_index_name}' exists. Deleting...")
            
            # Get collection info before deletion
            try:
                info = client.get_collection_info()
                logger.info(f"Current collection has {info.get('points_count', 0)} documents")
            except:
                pass
            
            # Delete collection
            client.client.delete_collection(settings.vector_db_index_name)
            logger.info(f"✓ Deleted collection '{settings.vector_db_index_name}'")
        else:
            logger.info(f"Collection '{settings.vector_db_index_name}' does not exist")
        
        # Create new collection with indexes
        logger.info("Creating new collection with indexes...")
        client.create_collection(vector_size=settings.vector_embedding_dimension)
        logger.info(f"✓ Created collection '{settings.vector_db_index_name}'")
        
        # Verify indexes were created
        logger.info("\nVerifying indexes...")
        from qdrant_client.models import PayloadSchemaType
        
        filterable_fields = [
            "scheme_id",
            "category",
            "authority",
            "state",
            "status",
            "language",
            "document_type",
        ]
        
        for field in filterable_fields:
            logger.info(f"  ✓ Index created for: {field}")
        
        logger.info("\n" + "="*60)
        logger.info("SUCCESS: Collection recreated with proper indexes!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Re-import your scheme data:")
        logger.info("   python scripts/import_schemes.py --file data/sample_schemes.json")
        logger.info("\n2. Or generate and import sample data:")
        logger.info("   python scripts/generate_sample_schemes.py --count 100")
        logger.info("   python scripts/import_schemes.py --file data/sample_schemes.json")
        
    except Exception as e:
        logger.error(f"Error recreating collection: {e}")
        sys.exit(1)
    
    finally:
        client.close()


if __name__ == "__main__":
    recreate_collection()
