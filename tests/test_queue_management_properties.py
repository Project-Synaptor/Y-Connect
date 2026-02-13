"""Property-based tests for queue management and overload handling"""

import pytest
import time
import asyncio
from typing import List
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock

from app.message_queue import MessageQueue, QueuedMessage
from app.load_monitor import LoadMonitor


class TestQueueManagementProperties:
    """Property-based tests for overload queue management"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing"""
        with patch('app.message_queue.redis.Redis') as mock_redis_class, \
             patch('app.load_monitor.redis.Redis') as mock_redis_class2:
            
            # Create a mock Redis client
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            
            # Mock queue operations
            mock_client.rpush.return_value = 1
            mock_client.lpop.return_value = None
            mock_client.llen.return_value = 0
            mock_client.get.return_value = None
            mock_client.set.return_value = True
            mock_client.incr.return_value = 1
            mock_client.decr.return_value = 0
            mock_client.exists.return_value = False
            mock_client.lrange.return_value = []
            mock_client.ltrim.return_value = True
            mock_client.delete.return_value = 1
            
            # Return the same mock for both patches
            mock_redis_class.return_value = mock_client
            mock_redis_class2.return_value = mock_client
            
            yield mock_client
    
    @given(
        num_messages=st.integers(min_value=1, max_value=50),
        phone_numbers=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Nd',)),
                min_size=10,
                max_size=15
            ),
            min_size=1,
            max_size=50
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_31_overload_queue_management(
        self,
        mock_redis,
        num_messages,
        phone_numbers
    ):
        """
        Feature: y-connect-whatsapp-bot, Property 31: Overload Queue Management
        
        For any request received when system load exceeds capacity, the request
        should be queued and the user should receive a message indicating
        expected wait time.
        
        Validates: Requirements 10.5
        """
        # Ensure we have enough phone numbers
        if len(phone_numbers) < num_messages:
            phone_numbers = phone_numbers * ((num_messages // len(phone_numbers)) + 1)
        phone_numbers = phone_numbers[:num_messages]
        
        # Initialize queue and load monitor
        message_queue = MessageQueue()
        load_monitor = LoadMonitor()
        
        # Configure mock to simulate queue operations
        queued_messages = []
        
        def mock_rpush(key, value):
            if key == MessageQueue.QUEUE_KEY:
                queued_messages.append(value)
            return len(queued_messages)
        
        def mock_lpop(key):
            if key == MessageQueue.QUEUE_KEY and queued_messages:
                return queued_messages.pop(0)
            return None
        
        def mock_llen(key):
            if key == MessageQueue.QUEUE_KEY:
                return len(queued_messages)
            return 0
        
        queue_depth = [0]
        
        def mock_incr(key):
            if key == MessageQueue.QUEUE_DEPTH_KEY:
                queue_depth[0] += 1
            elif key == LoadMonitor.ACTIVE_REQUESTS_KEY:
                return queue_depth[0]
            return queue_depth[0]
        
        def mock_decr(key):
            if key == MessageQueue.QUEUE_DEPTH_KEY:
                queue_depth[0] = max(0, queue_depth[0] - 1)
            elif key == LoadMonitor.ACTIVE_REQUESTS_KEY:
                queue_depth[0] = max(0, queue_depth[0] - 1)
            return queue_depth[0]
        
        def mock_get(key):
            if key == MessageQueue.QUEUE_DEPTH_KEY:
                return str(queue_depth[0])
            elif key == LoadMonitor.ACTIVE_REQUESTS_KEY:
                return str(queue_depth[0])
            elif key == MessageQueue.PROCESSING_TIME_KEY:
                return "8.0"
            return None
        
        mock_redis.rpush.side_effect = mock_rpush
        mock_redis.lpop.side_effect = mock_lpop
        mock_redis.llen.side_effect = mock_llen
        mock_redis.incr.side_effect = mock_incr
        mock_redis.decr.side_effect = mock_decr
        mock_redis.get.side_effect = mock_get
        
        # Property 31: Queue messages when overloaded
        messages_to_queue = []
        for i in range(num_messages):
            msg = QueuedMessage(
                message_id=f"msg_{i}",
                phone_number=phone_numbers[i],
                message_text=f"Test message {i}",
                language="en",
                queued_at=time.time()
            )
            messages_to_queue.append(msg)
        
        # Queue all messages
        for msg in messages_to_queue:
            result = message_queue.queue_message(msg)
            assert result is True, "Message should be queued successfully"
        
        # Verify queue depth matches number of queued messages
        depth = message_queue.get_queue_depth()
        assert depth == num_messages, \
            f"Queue depth should be {num_messages}, got {depth}"
        
        # Verify estimated wait time is calculated
        wait_time = message_queue.get_estimated_wait_time()
        assert wait_time > 0, "Estimated wait time should be positive when queue has messages"
        
        # Verify wait time is reasonable (queue_depth * avg_processing_time)
        expected_min_wait = num_messages * 5  # Minimum 5 seconds per message
        expected_max_wait = num_messages * 15  # Maximum 15 seconds per message
        assert expected_min_wait <= wait_time <= expected_max_wait, \
            f"Wait time {wait_time}s should be between {expected_min_wait}s and {expected_max_wait}s"
        
        # Verify wait time message is generated for all supported languages
        languages = ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
        for lang in languages:
            wait_msg = load_monitor.get_wait_time_message(wait_time, lang)
            assert wait_msg is not None, f"Wait message should be generated for {lang}"
            assert len(wait_msg) > 0, f"Wait message should not be empty for {lang}"
            assert "⏳" in wait_msg, f"Wait message should contain waiting emoji for {lang}"
        
        # Verify messages can be dequeued in FIFO order
        dequeued_messages = []
        for _ in range(num_messages):
            msg = message_queue.dequeue_message()
            if msg:
                dequeued_messages.append(msg)
        
        # Verify all messages were dequeued
        assert len(dequeued_messages) == num_messages, \
            f"Should dequeue {num_messages} messages, got {len(dequeued_messages)}"
        
        # Verify FIFO order (first queued = first dequeued)
        for i, msg in enumerate(dequeued_messages):
            assert msg.message_id == f"msg_{i}", \
                f"Message {i} should be dequeued in FIFO order"
        
        # Verify queue is empty after dequeuing all messages
        final_depth = message_queue.get_queue_depth()
        assert final_depth == 0, f"Queue should be empty after dequeuing all messages, got {final_depth}"
    
    @given(
        active_requests=st.integers(min_value=0, max_value=200),
        response_times=st.lists(
            st.floats(min_value=0.1, max_value=20.0),
            min_size=1,
            max_size=100
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_load_detection_triggers_queuing(
        self,
        mock_redis,
        active_requests,
        response_times
    ):
        """
        Test that load detection correctly identifies overload conditions
        and triggers queuing behavior.
        
        Validates: Requirements 10.4, 10.5
        """
        # Initialize load monitor
        load_monitor = LoadMonitor()
        
        # Configure mock to track active requests
        active_count = [active_requests]
        
        def mock_get(key):
            if key == LoadMonitor.ACTIVE_REQUESTS_KEY:
                return str(active_count[0])
            return None
        
        def mock_lrange(key, start, end):
            if key == LoadMonitor.RESPONSE_TIMES_KEY:
                # Return response times as "timestamp:time" format
                return [f"{time.time()}:{rt}" for rt in response_times[:100]]
            return []
        
        mock_redis.get.side_effect = mock_get
        mock_redis.lrange.side_effect = mock_lrange
        
        # Get load metrics
        metrics = load_monitor.get_load_metrics()
        
        # Verify metrics are calculated
        assert metrics.active_requests == active_requests
        assert metrics.avg_response_time >= 0
        assert metrics.p95_response_time >= 0
        assert metrics.p99_response_time >= 0
        
        # Verify overload detection logic
        # System is overloaded if:
        # 1. Active requests >= 100 (MAX_CONCURRENT_REQUESTS)
        # 2. OR p95 response time >= 10 seconds (MAX_RESPONSE_TIME_P95)
        
        p95_time = load_monitor.calculate_percentile(response_times, 95)
        
        expected_overload = (
            active_requests >= LoadMonitor.MAX_CONCURRENT_REQUESTS or
            p95_time >= LoadMonitor.MAX_RESPONSE_TIME_P95
        )
        
        assert metrics.is_overloaded == expected_overload, \
            f"Overload detection mismatch: expected {expected_overload}, got {metrics.is_overloaded}"
        
        # Verify is_overloaded() method returns same result
        is_overloaded = load_monitor.is_overloaded()
        assert is_overloaded == expected_overload, \
            f"is_overloaded() should return {expected_overload}, got {is_overloaded}"
    
    @given(
        queue_depth=st.integers(min_value=0, max_value=100),
        avg_processing_time=st.floats(min_value=1.0, max_value=15.0)
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_wait_time_estimation_accuracy(
        self,
        mock_redis,
        queue_depth,
        avg_processing_time
    ):
        """
        Test that estimated wait time is calculated accurately based on
        queue depth and average processing time.
        
        Validates: Requirements 10.5
        """
        # Initialize message queue
        message_queue = MessageQueue()
        
        # Configure mock to return queue depth and processing time
        def mock_get(key):
            if key == MessageQueue.QUEUE_DEPTH_KEY:
                return str(queue_depth)
            elif key == MessageQueue.PROCESSING_TIME_KEY:
                return str(avg_processing_time)
            return None
        
        mock_redis.get.side_effect = mock_get
        
        # Get estimated wait time
        wait_time = message_queue.get_estimated_wait_time()
        
        # Verify wait time calculation
        if queue_depth == 0:
            assert wait_time == 0, "Wait time should be 0 when queue is empty"
        else:
            expected_wait = int(queue_depth * avg_processing_time)
            assert wait_time == expected_wait, \
                f"Wait time should be {expected_wait}s (depth={queue_depth} * time={avg_processing_time}), got {wait_time}s"
