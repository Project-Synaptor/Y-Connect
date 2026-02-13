"""Repository for scheme database operations"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

import psycopg2
from psycopg2 import sql

from app.database import db_pool
from app.models import Scheme, SchemeStatus, SchemeCategory, SchemeAuthority
from app.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class SchemeRepository:
    """Repository for managing scheme data in PostgreSQL"""
    
    @staticmethod
    def get_scheme_by_id(scheme_id: str) -> Optional[Scheme]:
        """
        Retrieve a scheme by its ID (with caching)
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            Scheme object if found, None otherwise
        """
        # Try to get from cache first
        try:
            cached_data = cache_manager.get_cached_scheme(scheme_id)
            if cached_data:
                # Reconstruct Scheme object from cached data
                return Scheme(**cached_data)
        except Exception as e:
            logger.warning(f"Error retrieving scheme from cache: {e}")
        
        # Cache miss - fetch from database
        query = """
        SELECT 
            scheme_id, scheme_name, scheme_name_translations,
            description, description_translations,
            category, authority, applicable_states,
            eligibility_criteria, benefits, benefits_translations,
            application_process, application_process_translations,
            official_url, helpline_numbers, status,
            start_date, end_date, last_updated
        FROM schemes
        WHERE scheme_id = %s;
        """
        
        try:
            with db_pool.get_cursor(commit=False) as cursor:
                cursor.execute(query, (scheme_id,))
                row = cursor.fetchone()
                
                if row:
                    scheme = SchemeRepository._row_to_scheme(row)
                    
                    # Cache the scheme for future requests
                    try:
                        scheme_dict = scheme.model_dump()
                        # Convert date/datetime objects to ISO format for JSON serialization
                        if scheme_dict.get('start_date'):
                            scheme_dict['start_date'] = scheme_dict['start_date'].isoformat()
                        if scheme_dict.get('end_date'):
                            scheme_dict['end_date'] = scheme_dict['end_date'].isoformat()
                        if scheme_dict.get('last_updated'):
                            scheme_dict['last_updated'] = scheme_dict['last_updated'].isoformat()
                        
                        cache_manager.cache_scheme(scheme_id, scheme_dict)
                    except Exception as e:
                        logger.warning(f"Error caching scheme {scheme_id}: {e}")
                    
                    return scheme
                return None
        except psycopg2.Error as e:
            logger.error(f"Error retrieving scheme {scheme_id}: {e}")
            raise
    
    @staticmethod
    def search_schemes(
        category: Optional[str] = None,
        status: Optional[str] = None,
        state: Optional[str] = None,
        authority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Scheme]:
        """
        Search schemes with filtering support
        
        Args:
            category: Filter by scheme category
            status: Filter by scheme status (active, expired, upcoming)
            state: Filter by applicable state (or 'ALL')
            authority: Filter by authority (central, state)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching Scheme objects
        """
        # Build dynamic query with filters
        query_parts = ["""
        SELECT 
            scheme_id, scheme_name, scheme_name_translations,
            description, description_translations,
            category, authority, applicable_states,
            eligibility_criteria, benefits, benefits_translations,
            application_process, application_process_translations,
            official_url, helpline_numbers, status,
            start_date, end_date, last_updated
        FROM schemes
        WHERE 1=1
        """]
        
        params = []
        
        if category:
            query_parts.append("AND category = %s")
            params.append(category)
        
        if status:
            query_parts.append("AND status = %s")
            params.append(status)
        
        if state:
            # Check if state is in applicable_states array or if 'ALL' is in array
            query_parts.append("AND (%s = ANY(applicable_states) OR 'ALL' = ANY(applicable_states))")
            params.append(state.upper())
        
        if authority:
            query_parts.append("AND authority = %s")
            params.append(authority)
        
        query_parts.append("ORDER BY last_updated DESC")
        query_parts.append("LIMIT %s OFFSET %s")
        params.extend([limit, offset])
        
        query = " ".join(query_parts)
        
        try:
            with db_pool.get_cursor(commit=False) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [SchemeRepository._row_to_scheme(row) for row in rows]
        except psycopg2.Error as e:
            logger.error(f"Error searching schemes: {e}")
            raise
    
    @staticmethod
    def get_scheme_translations(scheme_id: str, language: str) -> Optional[Dict[str, str]]:
        """
        Get localized content for a scheme
        
        Args:
            scheme_id: Unique scheme identifier
            language: Language code (hi, en, ta, etc.)
            
        Returns:
            Dictionary with translated fields or None if scheme not found
        """
        query = """
        SELECT 
            scheme_name, scheme_name_translations,
            description, description_translations,
            benefits, benefits_translations,
            application_process, application_process_translations
        FROM schemes
        WHERE scheme_id = %s;
        """
        
        try:
            with db_pool.get_cursor(commit=False) as cursor:
                cursor.execute(query, (scheme_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Extract translations or fall back to English
                translations = {
                    'scheme_name': row['scheme_name_translations'].get(
                        language, row['scheme_name']
                    ) if row['scheme_name_translations'] else row['scheme_name'],
                    'description': row['description_translations'].get(
                        language, row['description']
                    ) if row['description_translations'] else row['description'],
                    'benefits': row['benefits_translations'].get(
                        language, row['benefits']
                    ) if row['benefits_translations'] else row['benefits'],
                    'application_process': row['application_process_translations'].get(
                        language, row['application_process']
                    ) if row['application_process_translations'] else row['application_process'],
                }
                
                return translations
        except psycopg2.Error as e:
            logger.error(f"Error retrieving translations for scheme {scheme_id}: {e}")
            raise
    
    @staticmethod
    def insert_scheme(scheme: Scheme) -> bool:
        """
        Insert a new scheme into the database
        
        Args:
            scheme: Scheme object to insert
            
        Returns:
            True if insertion successful, False otherwise
        """
        query = """
        INSERT INTO schemes (
            scheme_id, scheme_name, scheme_name_translations,
            description, description_translations,
            category, authority, applicable_states,
            eligibility_criteria, benefits, benefits_translations,
            application_process, application_process_translations,
            official_url, helpline_numbers, status,
            start_date, end_date, last_updated
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
        """
        
        params = (
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
        )
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(query, params)
                logger.info(f"Scheme {scheme.scheme_id} inserted successfully")
                return True
        except psycopg2.IntegrityError as e:
            logger.error(f"Scheme {scheme.scheme_id} already exists: {e}")
            return False
        except psycopg2.Error as e:
            logger.error(f"Error inserting scheme {scheme.scheme_id}: {e}")
            raise
    
    @staticmethod
    def update_scheme(scheme_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing scheme (invalidates cache)
        
        Args:
            scheme_id: Unique scheme identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if update successful, False if scheme not found
        """
        if not updates:
            logger.warning(f"No updates provided for scheme {scheme_id}")
            return False
        
        # Build dynamic update query
        set_clauses = []
        params = []
        
        # Map of allowed update fields to their handling
        allowed_fields = {
            'scheme_name', 'scheme_name_translations', 'description',
            'description_translations', 'category', 'authority',
            'applicable_states', 'eligibility_criteria', 'benefits',
            'benefits_translations', 'application_process',
            'application_process_translations', 'official_url',
            'helpline_numbers', 'status', 'start_date', 'end_date'
        }
        
        for field, value in updates.items():
            if field not in allowed_fields:
                logger.warning(f"Ignoring invalid update field: {field}")
                continue
            
            # Handle JSONB fields
            if field in ['scheme_name_translations', 'description_translations',
                        'benefits_translations', 'application_process_translations',
                        'eligibility_criteria']:
                value = json.dumps(value) if isinstance(value, dict) else value
            
            set_clauses.append(f"{field} = %s")
            params.append(value)
        
        if not set_clauses:
            logger.warning(f"No valid update fields for scheme {scheme_id}")
            return False
        
        # Always update last_updated timestamp
        set_clauses.append("last_updated = %s")
        params.append(datetime.utcnow())
        
        # Add scheme_id for WHERE clause
        params.append(scheme_id)
        
        query = f"""
        UPDATE schemes
        SET {', '.join(set_clauses)}
        WHERE scheme_id = %s;
        """
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(query, params)
                
                if cursor.rowcount == 0:
                    logger.warning(f"Scheme {scheme_id} not found for update")
                    return False
                
                # Invalidate cache after successful update
                try:
                    cache_manager.invalidate_scheme(scheme_id)
                except Exception as e:
                    logger.warning(f"Error invalidating cache for scheme {scheme_id}: {e}")
                
                logger.info(f"Scheme {scheme_id} updated successfully")
                return True
        except psycopg2.Error as e:
            logger.error(f"Error updating scheme {scheme_id}: {e}")
            raise
    
    @staticmethod
    def delete_scheme(scheme_id: str) -> bool:
        """
        Delete a scheme from the database
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            True if deletion successful, False if scheme not found
        """
        query = "DELETE FROM schemes WHERE scheme_id = %s;"
        
        try:
            with db_pool.get_cursor(commit=True) as cursor:
                cursor.execute(query, (scheme_id,))
                
                if cursor.rowcount == 0:
                    logger.warning(f"Scheme {scheme_id} not found for deletion")
                    return False
                
                logger.info(f"Scheme {scheme_id} deleted successfully")
                return True
        except psycopg2.Error as e:
            logger.error(f"Error deleting scheme {scheme_id}: {e}")
            raise
    
    @staticmethod
    def _row_to_scheme(row: Dict[str, Any]) -> Scheme:
        """
        Convert database row to Scheme object
        
        Args:
            row: Database row as dictionary
            
        Returns:
            Scheme object
        """
        return Scheme(
            scheme_id=row['scheme_id'],
            scheme_name=row['scheme_name'],
            scheme_name_translations=row['scheme_name_translations'] or {},
            description=row['description'],
            description_translations=row['description_translations'] or {},
            category=SchemeCategory(row['category']),
            authority=SchemeAuthority(row['authority']),
            applicable_states=row['applicable_states'],
            eligibility_criteria=row['eligibility_criteria'] or {},
            benefits=row['benefits'],
            benefits_translations=row['benefits_translations'] or {},
            application_process=row['application_process'],
            application_process_translations=row['application_process_translations'] or {},
            official_url=row['official_url'],
            helpline_numbers=row['helpline_numbers'] or [],
            status=SchemeStatus(row['status']),
            start_date=row['start_date'],
            end_date=row['end_date'],
            last_updated=row['last_updated']
        )
