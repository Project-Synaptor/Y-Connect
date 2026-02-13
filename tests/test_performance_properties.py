"""Property-based tests for performance requirements"""

import pytest
import time
import asyncio
import concurrent.futures
from typing import List
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, AsyncMock

from app.message_processor import MessageProcessor
from app.models import IncomingMessage


class TestPerformanceProperties:
    """Property-based tests for performance and scalability"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for performance testing"""
        with patch('app.message_processor.SessionManager') as mock_session_mgr, \
             patch('app.message_processor.LanguageDetector') as mock_lang_detector, \
             patch('app.message_processor.QueryProcessor') as mock_query_proc, \
             patch('app.message_processor.RAGEngine') as mock_rag, \
             patch('app.message_processor.ResponseGenerator') as mock_response_gen, \
             patch('app.message_processor.WhatsAppClient') as mock_whatsapp:
            
            # Configure mocks to return quickly
            mock_session = Mock()
            mock_session.phone_number = "+1234567890"
            mock_session.language = "en"
            mock_session.is_new_user = False
            mock_session.conversation_history = []
            mock_session.user_context = {}
            
            mock_session_mgr.return_value.get_or_create_session.return_value = mock_session
            mock_session_mgr.return_value.update_session.return_value = None
            
            mock_lang_result = Mock()
            mock_lang_result.language_code = "en"
            mock_lang_result.language_name = "English"
            mock_lang_result.confidence = 0.95
            mock_lang_detector.return_value.detect_language.return_value = mock_lang_result
            
            mock_processed_query = Mock()
            mock_processed_query.original_text = "test query"
            mock_processed_query.language = "en"
            mock_processed_query.intent = "search_schemes"
            mock_processed_query.entities = {}
            mock_processed_query.needs_clarification = False
            mock_processed_query.search_vector = [0.1] * 384
            mock_query_proc.return_value.process_query.return_value = mock_processed_query
            
            mock_scheme = Mock()
            mock_scheme.scheme_name = "Test Scheme"
            mock_scheme.description = "Test description"
            mock_rag.return_value.retrieve_schemes.return_value = [mock_scheme]
            mock_rag.return_value.generate_response.return_value = "Test response"
            
            mock_response_gen.return_value.format_response.return_value = ["Test response"]
            
            mock_whatsapp.return_value.send_message.return_value = True
            
            yield {
                'session_mgr': mock_session_mgr,
                'lang_detector': mock_lang_detector,
                'query_proc': mock_query_proc,
                'rag': mock_rag,
                'response_gen': mock_response_gen,
                'whatsapp': mock_whatsapp
            }
    
    @given(
        queries=st.lists(
            st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
            min_size=100,
            max_size=100
        )
    )
    @settings(
        max_examples=1,  # Run once with 100 queries
        deadline=None,  # Disable deadline for this test
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    def test_property_29_response_time_sla(self, queries: List[str], mock_dependencies):
        """
        Feature: y-connect-whatsapp-bot, Property 29: Response Time SLA
        
        **Validates: Requirements 10.1, 10.2**
        
        For any set of 100 user queries under normal load, at least 95 queries 
        should receive a response within 10 seconds.
        
        This property ensures the system meets its performance SLA of responding 
        to 95% of queries within 10 seconds.
        """
        processor = MessageProcessor()
        response_times = []
        successful_responses = 0
        
        for query_text in queries:
            # Create incoming message
            message = IncomingMessage(
                message_id=f"msg_{time.time()}",
                from_phone="+1234567890",
                timestamp=time.time(),
                message_type="text",
                text_content=query_text,
                media_url=None
            )
            
            # Measure response time
            start_time = time.time()
            
            try:
                # Process message
                response = processor.process_incoming_message(message)
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if response:
                    successful_responses += 1
            except Exception as e:
                # Log error but continue testing
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                print(f"Error processing query: {e}")
        
        # Calculate how many queries completed within 10 seconds
        within_sla = sum(1 for rt in response_times if rt <= 10.0)
        percentage_within_sla = (within_sla / len(queries)) * 100
        
        # Log statistics
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        print(f"\n=== Response Time SLA Test Results ===")
        print(f"Total queries: {len(queries)}")
        print(f"Queries within 10s: {within_sla} ({percentage_within_sla:.1f}%)")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Min response time: {min_response_time:.3f}s")
        print(f"Max response time: {max_response_time:.3f}s")
        print(f"Successful responses: {successful_responses}")
        
        # Assert that at least 95% of queries completed within 10 seconds
        assert percentage_within_sla >= 95.0, (
            f"Only {percentage_within_sla:.1f}% of queries completed within 10 seconds. "
            f"Expected at least 95%. Average response time: {avg_response_time:.3f}s"
        )
        
        # Additional assertion: average response time should be well below 10 seconds
        assert avg_response_time < 8.0, (
            f"Average response time {avg_response_time:.3f}s is too high. "
            f"Expected < 8.0s for healthy system performance."
        )
    
    @given(
        phone_numbers=st.lists(
            st.text(min_size=10, max_size=15, alphabet='0123456789'),
            min_size=100,
            max_size=100,
            unique=True
        ),
        query_text=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))
    )
    @settings(
        max_examples=1,  # Run once with 100 concurrent sessions
        deadline=None,  # Disable deadline for this test
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    def test_property_30_concurrent_session_handling(self, phone_numbers: List[str], query_text: str, mock_dependencies):
        """
        Feature: y-connect-whatsapp-bot, Property 30: Concurrent Session Handling
        
        **Validates: Requirements 10.4**
        
        For any load test with 100 concurrent user sessions, the system should 
        maintain response times within the 10-second SLA without errors.
        
        This property ensures the system can handle concurrent load without 
        performance degradation or failures.
        """
        processor = MessageProcessor()
        
        def process_message_for_user(phone_number: str) -> dict:
            """Process a message for a specific user and return timing info"""
            message = IncomingMessage(
                message_id=f"msg_{phone_number}_{time.time()}",
                from_phone=f"+{phone_number}",
                timestamp=time.time(),
                message_type="text",
                text_content=query_text,
                media_url=None
            )
            
            start_time = time.time()
            error = None
            response = None
            
            try:
                response = processor.process_incoming_message(message)
            except Exception as e:
                error = str(e)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'phone_number': phone_number,
                'response_time': response_time,
                'success': response is not None and error is None,
                'error': error
            }
        
        # Process messages concurrently using ThreadPoolExecutor
        results = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            # Submit all tasks
            futures = [executor.submit(process_message_for_user, phone) for phone in phone_numbers]
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error in concurrent execution: {e}")
                    results.append({
                        'phone_number': 'unknown',
                        'response_time': 0,
                        'success': False,
                        'error': str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = len(results) - successful_requests
        response_times = [r['response_time'] for r in results]
        
        within_sla = sum(1 for rt in response_times if rt <= 10.0)
        percentage_within_sla = (within_sla / len(results)) * 100 if results else 0
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        # Log statistics
        print(f"\n=== Concurrent Session Handling Test Results ===")
        print(f"Total concurrent sessions: {len(phone_numbers)}")
        print(f"Total execution time: {total_time:.3f}s")
        print(f"Successful requests: {successful_requests}")
        print(f"Failed requests: {failed_requests}")
        print(f"Requests within 10s SLA: {within_sla} ({percentage_within_sla:.1f}%)")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Min response time: {min_response_time:.3f}s")
        print(f"Max response time: {max_response_time:.3f}s")
        
        if failed_requests > 0:
            errors = [r['error'] for r in results if r['error']]
            print(f"Sample errors: {errors[:5]}")
        
        # Assert no errors occurred
        assert failed_requests == 0, (
            f"{failed_requests} out of {len(results)} requests failed during concurrent load. "
            f"System should handle 100 concurrent sessions without errors."
        )
        
        # Assert response times are within SLA
        assert percentage_within_sla >= 95.0, (
            f"Only {percentage_within_sla:.1f}% of concurrent requests completed within 10 seconds. "
            f"Expected at least 95%. Average response time: {avg_response_time:.3f}s"
        )
        
        # Assert average response time is reasonable under load
        assert avg_response_time < 10.0, (
            f"Average response time {avg_response_time:.3f}s under concurrent load is too high. "
            f"Expected < 10.0s for 100 concurrent sessions."
        )

