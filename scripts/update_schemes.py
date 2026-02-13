#!/usr/bin/env python3
"""
Scheme Update Script for Y-Connect WhatsApp Bot

This script updates existing government schemes in PostgreSQL and regenerates
embeddings in the vector store.

Usage:
    python scripts/update_schemes.py --scheme-id PM-KISAN --file updated_scheme.json
    python scripts/update_schemes.py --scheme-id PM-KISAN --field status --value expired
    python scripts/update_schemes.py --all --file bulk_updates.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import db_pool, init_database
from app.models import Scheme
from app.vector_store import VectorStoreClient, VectorDocument
from app.embedding_generator import get_embedding_generator
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchemeUpdater:
    """Update existing schemes in database and vector store"""
    
    def __init__(self):
        """Initialize updater with database and vector store connections"""
        self.settings = get_settings()
        self.embedding_generator = get_embedding_generator()
        self.vector_store = VectorStoreClient(
            vector_size=self.embedding_generator.get_embedding_dimension()
        )
        
        # Ensure database schema exists
        init_database()
    
    def get_scheme_from_db(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve scheme from database
        
        Args:
            scheme_id: Scheme identifier
            
        Returns:
            Scheme dictionary or None if not found
        """
        query = "SELECT * FROM schemes WHERE scheme_id = %s;"
        
        try:
            with db_pool.get_cursor(commit=False) as cursor:
                cursor.execute(query, (scheme_id,))
                result = cursor.fetchone()
                
                if result:
                    # Convert RealDictRow to regular dict
                    return dict(result)
                return None
        
        except Exception as e:
            logger.error(f"Failed to retrieve scheme {scheme_id}: {e}")
            return None
    
    def update_scheme_in_db(
        self,
        scheme_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update scheme fields in database
        
        Args:
            scheme_id: Scheme identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        if not updates:
            logger.warning("No updates provided")
            return False
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            set_clauses.append(f"{field} = %s")
            # Convert dict/list to JSON for JSONB fields
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value))
            else:
                values.append(value)
        
        # Always update last_updated timestamp
        set_clauses.append("last_updated = NOW()")
        
        query = f"""
        UPDATE schemes
        SET {', '.join(set_clauses)}
        WHERE scheme_id = %s;
        """
        
        values.append(scheme_id)
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    logger.warning(f"No scheme found with ID: {scheme_id}")
                    return False
                
                logger.info(f"Updated scheme {scheme_id} with {len(updates)} fields")
                return True
        
        except Exception as e:
            logger.error(f"Failed to update scheme {scheme_id}: {e}")
            return False
    
    def delete_scheme_documents(self, scheme_id: str) -> int:
        """
        Delete all documents for a scheme from database
        
        Args:
            scheme_id: Scheme identifier
            
        Returns:
            Number of documents deleted
        """
        query = "DELETE FROM scheme_documents WHERE scheme_id = %s;"
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(query, (scheme_id,))
                count = cursor.rowcount
                logger.info(f"Deleted {count} documents for scheme {scheme_id}")
                return count
        
        except Exception as e:
            logger.error(f"Failed to delete documents for scheme {scheme_id}: {e}")
            return 0
    
    def delete_scheme_embeddings(self, scheme_id: str) -> None:
        """
        Delete all embeddings for a scheme from vector store
        
        Args:
            scheme_id: Scheme identifier
        """
        try:
            # Delete by filter (scheme_id in metadata)
            self.vector_store.delete_by_filter({'scheme_id': scheme_id})
            logger.info(f"Deleted embeddings for scheme {scheme_id}")
        
        except Exception as e:
            logger.error(f"Failed to delete embeddings for scheme {scheme_id}: {e}")
    
    def regenerate_documents_and_embeddings(self, scheme_id: str) -> bool:
        """
        Regenerate documents and embeddings for a scheme
        
        Args:
            scheme_id: Scheme identifier
            
        Returns:
            True if successful, False otherwise
        """
        # Get updated scheme from database
        scheme_data = self.get_scheme_from_db(scheme_id)
        if not scheme_data:
            logger.error(f"Scheme {scheme_id} not found in database")
            return False
        
        # Convert to Scheme model
        try:
            # Convert datetime strings to datetime objects if needed
            if isinstance(scheme_data.get('start_date'), str):
                scheme_data['start_date'] = datetime.fromisoformat(scheme_data['start_date'])
            if isinstance(scheme_data.get('end_date'), str):
                scheme_data['end_date'] = datetime.fromisoformat(scheme_data['end_date'])
            if isinstance(scheme_data.get('last_updated'), str):
                scheme_data['last_updated'] = datetime.fromisoformat(scheme_data['last_updated'])
            if isinstance(scheme_data.get('created_at'), str):
                scheme_data['created_at'] = datetime.fromisoformat(scheme_data['created_at'])
            
            scheme = Scheme(**scheme_data)
        except Exception as e:
            logger.error(f"Failed to create Scheme model: {e}")
            return False
        
        # Delete old documents and embeddings
        self.delete_scheme_documents(scheme_id)
        self.delete_scheme_embeddings(scheme_id)
        
        # Generate new documents
        documents = self._generate_scheme_documents(scheme)
        
        # Insert documents to database
        self._insert_documents_to_db(documents)
        
        # Generate and store embeddings
        self._generate_and_store_embeddings(documents)
        
        logger.info(f"Regenerated documents and embeddings for scheme {scheme_id}")
        return True
    
    def _generate_scheme_documents(self, scheme: Scheme) -> List[Dict[str, Any]]:
        """
        Generate document chunks for a scheme in all languages
        
        Args:
            scheme: Scheme object
            
        Returns:
            List of document dictionaries
        """
        documents = []
        languages = ['en', 'hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa']
        
        for lang in languages:
            scheme_name = scheme.scheme_name_translations.get(lang, scheme.scheme_name)
            description = scheme.description_translations.get(lang, scheme.description)
            benefits = scheme.benefits_translations.get(lang, scheme.benefits)
            application_process = scheme.application_process_translations.get(
                lang, scheme.application_process
            )
            
            doc_text = f"""
Scheme: {scheme_name}

Description: {description}

Category: {scheme.category.value}
Authority: {scheme.authority.value}
Applicable States: {', '.join(scheme.applicable_states)}

Benefits: {benefits}

Application Process: {application_process}

Official URL: {scheme.official_url}
Status: {scheme.status.value}
            """.strip()
            
            chunks = self.embedding_generator.chunk_text(
                doc_text,
                chunk_size=512,
                overlap=50
            )
            
            for idx, chunk in enumerate(chunks):
                doc_id = f"{scheme.scheme_id}_{lang}_chunk{idx}"
                
                documents.append({
                    'document_id': doc_id,
                    'scheme_id': scheme.scheme_id,
                    'language': lang,
                    'content': chunk,
                    'document_type': 'overview',
                    'metadata': {
                        'scheme_id': scheme.scheme_id,
                        'scheme_name': scheme_name,
                        'scheme_name_local': scheme_name,
                        'category': scheme.category.value,
                        'authority': scheme.authority.value,
                        'state': scheme.applicable_states[0] if scheme.applicable_states else 'ALL',
                        'status': scheme.status.value,
                        'last_updated': scheme.last_updated.isoformat(),
                        'language': lang
                    }
                })
        
        return documents
    
    def _insert_documents_to_db(self, documents: List[Dict[str, Any]]) -> int:
        """Insert documents to database"""
        insert_query = """
        INSERT INTO scheme_documents (
            document_id, scheme_id, language, content, document_type
        ) VALUES (%s, %s, %s, %s, %s);
        """
        
        count = 0
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                for doc in documents:
                    cursor.execute(insert_query, (
                        doc['document_id'],
                        doc['scheme_id'],
                        doc['language'],
                        doc['content'],
                        doc['document_type']
                    ))
                    count += 1
            
            logger.info(f"Inserted {count} documents to database")
            return count
        
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
            return count
    
    def _generate_and_store_embeddings(self, documents: List[Dict[str, Any]]) -> int:
        """Generate and store embeddings"""
        if not documents:
            return 0
        
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        
        texts = [doc['content'] for doc in documents]
        embeddings = self.embedding_generator.batch_generate_embeddings(
            texts,
            batch_size=32,
            show_progress=True
        )
        
        vector_docs = []
        for doc, embedding in zip(documents, embeddings):
            vector_doc = VectorDocument(
                id=doc['document_id'],
                vector=embedding,
                metadata=doc['metadata'],
                text_chunk=doc['content']
            )
            vector_docs.append(vector_doc)
        
        count = self.vector_store.upsert_documents(vector_docs)
        logger.info(f"Stored {count} embeddings in vector store")
        
        return count
    
    def update_scheme(
        self,
        scheme_id: str,
        updates: Dict[str, Any],
        regenerate_embeddings: bool = True
    ) -> bool:
        """
        Update a scheme and optionally regenerate embeddings
        
        Args:
            scheme_id: Scheme identifier
            updates: Dictionary of fields to update
            regenerate_embeddings: Whether to regenerate embeddings
            
        Returns:
            True if successful, False otherwise
        """
        # Update scheme in database
        if not self.update_scheme_in_db(scheme_id, updates):
            return False
        
        # Regenerate embeddings if requested
        if regenerate_embeddings:
            if not self.regenerate_documents_and_embeddings(scheme_id):
                logger.warning(
                    f"Scheme {scheme_id} updated but embedding regeneration failed"
                )
                return False
        
        return True
    
    def bulk_update_schemes(
        self,
        updates_list: List[Dict[str, Any]],
        regenerate_embeddings: bool = True
    ) -> Dict[str, int]:
        """
        Update multiple schemes from a list
        
        Args:
            updates_list: List of update dictionaries with 'scheme_id' and 'updates' keys
            regenerate_embeddings: Whether to regenerate embeddings
            
        Returns:
            Dictionary with update statistics
        """
        total = len(updates_list)
        success = 0
        failed = 0
        
        for item in updates_list:
            scheme_id = item.get('scheme_id')
            updates = item.get('updates', {})
            
            if not scheme_id:
                logger.warning("Skipping item without scheme_id")
                failed += 1
                continue
            
            if self.update_scheme(scheme_id, updates, regenerate_embeddings):
                success += 1
            else:
                failed += 1
        
        stats = {
            'total': total,
            'success': success,
            'failed': failed
        }
        
        logger.info(f"Bulk update complete: {success}/{total} schemes updated successfully")
        if failed > 0:
            logger.warning(f"{failed} schemes failed to update")
        
        return stats


def main():
    """Main entry point for the update script"""
    parser = argparse.ArgumentParser(
        description='Update government schemes in Y-Connect database'
    )
    parser.add_argument(
        '--scheme-id',
        type=str,
        help='Scheme ID to update'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Path to JSON file with updates'
    )
    parser.add_argument(
        '--field',
        type=str,
        help='Single field to update (use with --value)'
    )
    parser.add_argument(
        '--value',
        type=str,
        help='Value for single field update (use with --field)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Update all schemes from file (file must contain list of updates)'
    )
    parser.add_argument(
        '--no-embeddings',
        action='store_true',
        help='Skip embedding regeneration (faster but may cause stale results)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.scheme_id and not args.all:
        parser.error("Either --scheme-id or --all must be specified")
    
    if args.field and not args.value:
        parser.error("--value must be specified when using --field")
    
    if args.value and not args.field:
        parser.error("--field must be specified when using --value")
    
    try:
        updater = SchemeUpdater()
        regenerate = not args.no_embeddings
        
        if args.all:
            # Bulk update from file
            if not args.file:
                parser.error("--file must be specified when using --all")
            
            with open(args.file, 'r', encoding='utf-8') as f:
                updates_list = json.load(f)
            
            if not isinstance(updates_list, list):
                raise ValueError("File must contain a list of update objects")
            
            stats = updater.bulk_update_schemes(updates_list, regenerate)
            
            print("\n" + "="*60)
            print("BULK UPDATE SUMMARY")
            print("="*60)
            print(f"Total schemes: {stats['total']}")
            print(f"Successfully updated: {stats['success']}")
            print(f"Failed: {stats['failed']}")
            print("="*60)
            
            sys.exit(0 if stats['failed'] == 0 else 1)
        
        else:
            # Single scheme update
            if args.file:
                # Load updates from file
                with open(args.file, 'r', encoding='utf-8') as f:
                    updates = json.load(f)
            elif args.field and args.value:
                # Single field update
                # Try to parse value as JSON, otherwise use as string
                try:
                    value = json.loads(args.value)
                except json.JSONDecodeError:
                    value = args.value
                
                updates = {args.field: value}
            else:
                parser.error("Either --file or both --field and --value must be specified")
            
            success = updater.update_scheme(args.scheme_id, updates, regenerate)
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            print(f"Scheme ID: {args.scheme_id}")
            print(f"Status: {'SUCCESS' if success else 'FAILED'}")
            print(f"Fields updated: {len(updates)}")
            print(f"Embeddings regenerated: {'Yes' if regenerate else 'No'}")
            print("="*60)
            
            sys.exit(0 if success else 1)
    
    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
