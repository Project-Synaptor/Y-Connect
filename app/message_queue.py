"""Message queue system for handling overload scenarios"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import redis
from redis.exceptions import RedisError

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class QueuedMessage:
    """Represents a message in the queue"""
    message_id: str
    phone_number: str
    message_text: str
    language: str
    queued_at: float  # Unix timestamp
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        """Create from dictionary"""
        return cls(**data)
    
    def get_wait_time_seconds(self) -> float:
        """Calculate how long this message has been waiting"""
        return time.time() - self.queued_at


class MessageQueue:
    """
    Redis-based message queue for handling system overload
    
    Uses Redis lists for FIFO queue operations and tracks queue depth
    and estimated wait times.
    """
    
    QUEUE_KEY = "yconnect:message_queue"
    QUEUE_DEPTH_KEY = "yconnect:queue_depth"
    PROCESSING_TIME_KEY = "yconnect:avg_processing_time"
    
    def __init__(self):
        """Initialize message queue with Redis connection"""
        settings = get_settings()
        
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Message queue initialized with Redis")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis for message queue: {e}")
            raise
    
    def queue_message(self, message: QueuedMessage) -> bool:
        """
        Add a message to the queue
        
        Args:
            message: QueuedMessage to queue
            
        Returns:
            True if successfully queued, False otherwise
        """
        try:
            # Serialize message to JSON
            message_json = json.dumps(message.to_dict())
            
            # Push to queue (RPUSH adds to tail, LPOP removes from head = FIFO)
            self.redis_client.rpush(self.QUEUE_KEY, message_json)
            
            # Increment queue depth counter
            self.redis_client.incr(self.QUEUE_DEPTH_KEY)
            
            logger.info(
                f"Message queued for phone {message.phone_number}",
                extra={
                    "message_id": message.message_id,
                    "queue_depth": self.get_queue_depth()
                }
            )
            
            return True
            
        except RedisError as e:
            logger.error(f"Failed to queue message: {e}")
            return False
    
    def dequeue_message(self) -> Optional[QueuedMessage]:
        """
        Remove and return the next message from the queue
        
        Returns:
            QueuedMessage if available, None if queue is empty
        """
        try:
            # Pop from head of queue (FIFO)
            message_json = self.redis_client.lpop(self.QUEUE_KEY)
            
            if message_json is None:
                return None
            
            # Deserialize message
            message_data = json.loads(message_json)
            message = QueuedMessage.from_dict(message_data)
            
            # Decrement queue depth counter
            current_depth = self.redis_client.decr(self.QUEUE_DEPTH_KEY)
            
            # Ensure depth doesn't go negative
            if current_depth < 0:
                self.redis_client.set(self.QUEUE_DEPTH_KEY, 0)
            
            logger.info(
                f"Message dequeued for phone {message.phone_number}",
                extra={
                    "message_id": message.message_id,
                    "wait_time_seconds": message.get_wait_time_seconds(),
                    "queue_depth": max(0, current_depth)
                }
            )
            
            return message
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to dequeue message: {e}")
            return None
    
    def get_queue_depth(self) -> int:
        """
        Get the current number of messages in the queue
        
        Returns:
            Number of messages waiting in queue
        """
        try:
            depth = self.redis_client.get(self.QUEUE_DEPTH_KEY)
            return int(depth) if depth else 0
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to get queue depth: {e}")
            # Fallback to list length
            try:
                return self.redis_client.llen(self.QUEUE_KEY)
            except RedisError:
                return 0
    
    def get_estimated_wait_time(self) -> int:
        """
        Calculate estimated wait time for new messages
        
        Returns:
            Estimated wait time in seconds
        """
        try:
            queue_depth = self.get_queue_depth()
            
            if queue_depth == 0:
                return 0
            
            # Get average processing time (default to 8 seconds per requirement 10.2)
            avg_time_str = self.redis_client.get(self.PROCESSING_TIME_KEY)
            avg_processing_time = float(avg_time_str) if avg_time_str else 8.0
            
            # Estimate: queue_depth * avg_processing_time
            estimated_wait = int(queue_depth * avg_processing_time)
            
            return estimated_wait
            
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to calculate estimated wait time: {e}")
            # Conservative estimate
            return self.get_queue_depth() * 10
    
    def update_avg_processing_time(self, processing_time: float) -> None:
        """
        Update the rolling average processing time
        
        Uses exponential moving average with alpha=0.3
        
        Args:
            processing_time: Time taken to process a message in seconds
        """
        try:
            current_avg_str = self.redis_client.get(self.PROCESSING_TIME_KEY)
            
            if current_avg_str is None:
                # First measurement
                new_avg = processing_time
            else:
                # Exponential moving average: new_avg = alpha * new + (1-alpha) * old
                current_avg = float(current_avg_str)
                alpha = 0.3
                new_avg = alpha * processing_time + (1 - alpha) * current_avg
            
            self.redis_client.set(self.PROCESSING_TIME_KEY, str(new_avg))
            
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to update average processing time: {e}")
    
    def process_queued_messages(self, max_messages: int = 10) -> Dict[str, int]:
        """
        Process messages from the queue
        
        This method should be called by a background worker to process
        queued messages when system load decreases.
        
        Args:
            max_messages: Maximum number of messages to process in this batch
            
        Returns:
            Dictionary with counts: {"processed": int, "failed": int, "remaining": int}
        """
        processed_count = 0
        failed_count = 0
        
        logger.info(f"Starting to process queued messages (max: {max_messages})")
        
        for _ in range(max_messages):
            message = self.dequeue_message()
            
            if message is None:
                # Queue is empty
                break
            
            try:
                # Import here to avoid circular dependency
                from app.webhook_handler import WebhookHandler
                
                # Create webhook handler instance
                handler = WebhookHandler()
                
                # Process the message
                start_time = time.time()
                
                # Simulate webhook payload structure
                payload = {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "id": message.message_id,
                                    "from": message.phone_number,
                                    "text": {"body": message.message_text},
                                    "type": "text"
                                }]
                            }
                        }]
                    }]
                }
                
                # Process message (this is async, but we'll handle it)
                import asyncio
                asyncio.run(handler.handle_message(payload))
                
                processing_time = time.time() - start_time
                self.update_avg_processing_time(processing_time)
                
                processed_count += 1
                
                logger.info(
                    f"Queued message processed successfully",
                    extra={
                        "message_id": message.message_id,
                        "processing_time": processing_time
                    }
                )
                
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Failed to process queued message: {e}",
                    extra={"message_id": message.message_id}
                )
        
        remaining = self.get_queue_depth()
        
        logger.info(
            f"Batch processing complete",
            extra={
                "processed": processed_count,
                "failed": failed_count,
                "remaining": remaining
            }
        )
        
        return {
            "processed": processed_count,
            "failed": failed_count,
            "remaining": remaining
        }
    
    def clear_queue(self) -> int:
        """
        Clear all messages from the queue (for testing/maintenance)
        
        Returns:
            Number of messages cleared
        """
        try:
            count = self.redis_client.llen(self.QUEUE_KEY)
            self.redis_client.delete(self.QUEUE_KEY)
            self.redis_client.set(self.QUEUE_DEPTH_KEY, 0)
            
            logger.warning(f"Queue cleared: {count} messages removed")
            return count
            
        except RedisError as e:
            logger.error(f"Failed to clear queue: {e}")
            return 0
