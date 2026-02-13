#!/usr/bin/env python3
"""
Scheme Import Script for Y-Connect WhatsApp Bot

This script imports government schemes from JSON/CSV files into PostgreSQL
and generates embeddings for vector store indexing.

Usage:
    python scripts/import_schemes.py --file schemes.json --format json
    python scripts/import_schemes.py --file schemes.csv --format csv
    python scripts/import_schemes.py --directory data/schemes/ --format json
"""

import argparse
import json
import csv
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import db_pool, init_database
from app.models import Scheme, SchemeStatus, SchemeCategory, SchemeAuthority
from app.vector_store import VectorStoreClient, VectorDocument
from app.embedding_generator import get_embedding_generator
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchemeImporter:
    """Import schemes from files into database and vector store"""
    
    def __init__(self):
        """Initialize importer with database and vector store connections"""
        self.settings = get_settings()
        self.embedding_generator = get_embedding_generator()
        self.vector_store = VectorStoreClient(
            vector_size=self.embedding_generator.get_embedding_dimension()
        )
        
        # Ensure database schema exists
        init_database()
        
        # Ensure vector store collection exists
        try:
            self.vector_store.create_collection()
        except Exception as e:
            logger.warning(f"Could not create vector store collection: {e}")
    
    def parse_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse schemes from JSON file
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of scheme dictionaries
        """
        logger.info(f"Parsing JSON file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single scheme and array of schemes
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("JSON file must contain a scheme object or array of schemes")
    
    def parse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse schemes from CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of scheme dictionaries
        """
        logger.info(f"Parsing CSV file: {file_path}")
        
        schemes = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert CSV row to scheme format
                scheme = self._csv_row_to_scheme(row)
                schemes.append(scheme)
        
        return schemes
    
    def _csv_row_to_scheme(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert CSV row to scheme dictionary
        
        Args:
            row: CSV row as dictionary
            
        Returns:
            Scheme dictionary
        """
        # Parse JSON fields from CSV
        scheme = {
            'scheme_id': row.get('scheme_id', ''),
            'scheme_name': row.get('scheme_name', ''),
            'description': row.get('description', ''),
            'category': row.get('category', ''),
            'authority': row.get('authority', ''),
            'benefits': row.get('benefits', ''),
            'application_process': row.get('application_process', ''),
            'official_url': row.get('official_url', ''),
            'status': row.get('status', 'active'),
        }
        
        # Parse JSON fields
        if row.get('scheme_name_translations'):
            scheme['scheme_name_translations'] = json.loads(row['scheme_name_translations'])
        
        if row.get('description_translations'):
            scheme['description_translations'] = json.loads(row['description_translations'])
        
        if row.get('benefits_translations'):
            scheme['benefits_translations'] = json.loads(row['benefits_translations'])
        
        if row.get('application_process_translations'):
            scheme['application_process_translations'] = json.loads(row['application_process_translations'])
        
        if row.get('applicable_states'):
            scheme['applicable_states'] = json.loads(row['applicable_states'])
        
        if row.get('eligibility_criteria'):
            scheme['eligibility_criteria'] = json.loads(row['eligibility_criteria'])
        
        if row.get('helpline_numbers'):
            scheme['helpline_numbers'] = json.loads(row['helpline_numbers'])
        
        # Parse dates
        if row.get('start_date'):
            scheme['start_date'] = datetime.fromisoformat(row['start_date'])
        
        if row.get('end_date'):
            scheme['end_date'] = datetime.fromisoformat(row['end_date'])
        
        return scheme

    
    def validate_scheme(self, scheme_data: Dict[str, Any]) -> Optional[Scheme]:
        """
        Validate and convert scheme data to Scheme model
        
        Args:
            scheme_data: Raw scheme dictionary
            
        Returns:
            Validated Scheme object or None if validation fails
        """
        try:
            # Ensure required fields have defaults
            if 'scheme_name_translations' not in scheme_data:
                scheme_data['scheme_name_translations'] = {}
            if 'description_translations' not in scheme_data:
                scheme_data['description_translations'] = {}
            if 'benefits_translations' not in scheme_data:
                scheme_data['benefits_translations'] = {}
            if 'application_process_translations' not in scheme_data:
                scheme_data['application_process_translations'] = {}
            if 'applicable_states' not in scheme_data:
                scheme_data['applicable_states'] = ['ALL']
            if 'eligibility_criteria' not in scheme_data:
                scheme_data['eligibility_criteria'] = {}
            if 'helpline_numbers' not in scheme_data:
                scheme_data['helpline_numbers'] = []
            
            # Create Scheme object (validates data)
            scheme = Scheme(**scheme_data)
            return scheme
        
        except Exception as e:
            logger.error(f"Validation failed for scheme {scheme_data.get('scheme_id', 'unknown')}: {e}")
            return None
    
    def insert_scheme_to_db(self, scheme: Scheme) -> bool:
        """
        Insert scheme into PostgreSQL database
        
        Args:
            scheme: Validated Scheme object
            
        Returns:
            True if successful, False otherwise
        """
        insert_query = """
        INSERT INTO schemes (
            scheme_id, scheme_name, scheme_name_translations,
            description, description_translations,
            category, authority, applicable_states,
            eligibility_criteria, benefits, benefits_translations,
            application_process, application_process_translations,
            official_url, helpline_numbers, status,
            start_date, end_date, last_updated
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (scheme_id) DO UPDATE SET
            scheme_name = EXCLUDED.scheme_name,
            scheme_name_translations = EXCLUDED.scheme_name_translations,
            description = EXCLUDED.description,
            description_translations = EXCLUDED.description_translations,
            category = EXCLUDED.category,
            authority = EXCLUDED.authority,
            applicable_states = EXCLUDED.applicable_states,
            eligibility_criteria = EXCLUDED.eligibility_criteria,
            benefits = EXCLUDED.benefits,
            benefits_translations = EXCLUDED.benefits_translations,
            application_process = EXCLUDED.application_process,
            application_process_translations = EXCLUDED.application_process_translations,
            official_url = EXCLUDED.official_url,
            helpline_numbers = EXCLUDED.helpline_numbers,
            status = EXCLUDED.status,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            last_updated = NOW();
        """
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(insert_query, (
                    scheme.scheme_id,
                    scheme.scheme_name,
                    json.dumps(scheme.scheme_name_translations),
                    scheme.description,
                    json.dumps(scheme.description_translations),
                    scheme.category.value,
                    scheme.authority.value,
                    scheme.applicable_states,
                    json.dumps(scheme.eligibility_criteria),
                    scheme.benefits,
                    json.dumps(scheme.benefits_translations),
                    scheme.application_process,
                    json.dumps(scheme.application_process_translations),
                    scheme.official_url,
                    scheme.helpline_numbers,
                    scheme.status.value,
                    scheme.start_date,
                    scheme.end_date,
                    scheme.last_updated
                ))
            
            logger.info(f"Inserted/updated scheme: {scheme.scheme_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert scheme {scheme.scheme_id}: {e}")
            return False
    
    def generate_scheme_documents(self, scheme: Scheme) -> List[Dict[str, Any]]:
        """
        Generate document chunks for a scheme in all languages
        
        Args:
            scheme: Scheme object
            
        Returns:
            List of document dictionaries with text and metadata
        """
        documents = []
        
        # Supported languages
        languages = ['en', 'hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa']
        
        for lang in languages:
            # Get translated content or fall back to English
            scheme_name = scheme.scheme_name_translations.get(lang, scheme.scheme_name)
            description = scheme.description_translations.get(lang, scheme.description)
            benefits = scheme.benefits_translations.get(lang, scheme.benefits)
            application_process = scheme.application_process_translations.get(
                lang, scheme.application_process
            )
            
            # Create comprehensive document text
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
            
            # Chunk the document if it's too long
            chunks = self.embedding_generator.chunk_text(
                doc_text,
                chunk_size=512,
                overlap=50
            )
            
            # Create document for each chunk
            for idx, chunk in enumerate(chunks):
                doc_id = f"{scheme.scheme_id}_{lang}_chunk{idx}"
                
                documents.append({
                    'document_id': doc_id,
                    'scheme_id': scheme.scheme_id,
                    'language': lang,
                    'content': chunk,
                    'document_type': 'overview',
                    'metadata': {
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
    
    def insert_documents_to_db(self, documents: List[Dict[str, Any]]) -> int:
        """
        Insert scheme documents into PostgreSQL
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Number of documents inserted
        """
        insert_query = """
        INSERT INTO scheme_documents (
            document_id, scheme_id, language, content, document_type
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (document_id) DO UPDATE SET
            content = EXCLUDED.content,
            document_type = EXCLUDED.document_type;
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
    
    def generate_and_store_embeddings(self, documents: List[Dict[str, Any]]) -> int:
        """
        Generate embeddings and store in vector database
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Number of embeddings stored
        """
        if not documents:
            return 0
        
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        
        # Extract texts for batch embedding
        texts = [doc['content'] for doc in documents]
        
        # Generate embeddings in batch
        embeddings = self.embedding_generator.batch_generate_embeddings(
            texts,
            batch_size=32,
            show_progress=True
        )
        
        # Create VectorDocument objects
        vector_docs = []
        for doc, embedding in zip(documents, embeddings):
            vector_doc = VectorDocument(
                id=doc['document_id'],
                vector=embedding,
                metadata=doc['metadata'],
                text_chunk=doc['content']
            )
            vector_docs.append(vector_doc)
        
        # Upsert to vector store
        count = self.vector_store.upsert_documents(vector_docs)
        logger.info(f"Stored {count} embeddings in vector store")
        
        return count
    
    def import_scheme(self, scheme_data: Dict[str, Any]) -> bool:
        """
        Import a single scheme (validate, insert to DB, generate embeddings)
        
        Args:
            scheme_data: Raw scheme dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Validate scheme
        scheme = self.validate_scheme(scheme_data)
        if not scheme:
            return False
        
        # Insert to PostgreSQL
        if not self.insert_scheme_to_db(scheme):
            return False
        
        # Generate document chunks
        documents = self.generate_scheme_documents(scheme)
        
        # Insert documents to PostgreSQL
        self.insert_documents_to_db(documents)
        
        # Generate and store embeddings
        self.generate_and_store_embeddings(documents)
        
        return True
    
    def import_schemes_from_file(
        self,
        file_path: str,
        file_format: str = 'json'
    ) -> Dict[str, int]:
        """
        Import schemes from a file
        
        Args:
            file_path: Path to file
            file_format: File format ('json' or 'csv')
            
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Importing schemes from {file_path} (format: {file_format})")
        
        # Parse file
        if file_format == 'json':
            schemes_data = self.parse_json_file(file_path)
        elif file_format == 'csv':
            schemes_data = self.parse_csv_file(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Import each scheme
        total = len(schemes_data)
        success = 0
        failed = 0
        
        for scheme_data in schemes_data:
            if self.import_scheme(scheme_data):
                success += 1
            else:
                failed += 1
        
        stats = {
            'total': total,
            'success': success,
            'failed': failed
        }
        
        logger.info(f"Import complete: {success}/{total} schemes imported successfully")
        if failed > 0:
            logger.warning(f"{failed} schemes failed to import")
        
        return stats
    
    def import_schemes_from_directory(
        self,
        directory_path: str,
        file_format: str = 'json'
    ) -> Dict[str, int]:
        """
        Import schemes from all files in a directory
        
        Args:
            directory_path: Path to directory
            file_format: File format ('json' or 'csv')
            
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Importing schemes from directory: {directory_path}")
        
        # Get all files with matching extension
        extension = '.json' if file_format == 'json' else '.csv'
        directory = Path(directory_path)
        files = list(directory.glob(f"*{extension}"))
        
        if not files:
            logger.warning(f"No {extension} files found in {directory_path}")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        logger.info(f"Found {len(files)} {extension} files")
        
        # Import from each file
        total_stats = {'total': 0, 'success': 0, 'failed': 0}
        
        for file_path in files:
            stats = self.import_schemes_from_file(str(file_path), file_format)
            total_stats['total'] += stats['total']
            total_stats['success'] += stats['success']
            total_stats['failed'] += stats['failed']
        
        logger.info(
            f"Directory import complete: {total_stats['success']}/{total_stats['total']} "
            f"schemes imported successfully from {len(files)} files"
        )
        
        return total_stats


def main():
    """Main entry point for the import script"""
    parser = argparse.ArgumentParser(
        description='Import government schemes into Y-Connect database'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Path to scheme file (JSON or CSV)'
    )
    parser.add_argument(
        '--directory',
        type=str,
        help='Path to directory containing scheme files'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'csv'],
        default='json',
        help='File format (default: json)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.file and not args.directory:
        parser.error("Either --file or --directory must be specified")
    
    if args.file and args.directory:
        parser.error("Cannot specify both --file and --directory")
    
    try:
        # Create importer
        importer = SchemeImporter()
        
        # Import schemes
        if args.file:
            stats = importer.import_schemes_from_file(args.file, args.format)
        else:
            stats = importer.import_schemes_from_directory(args.directory, args.format)
        
        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total schemes: {stats['total']}")
        print(f"Successfully imported: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        print("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if stats['failed'] == 0 else 1)
    
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
