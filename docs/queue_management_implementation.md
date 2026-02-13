# Queue Management Implementation

## Overview

This document describes the implementation of task 18: Queue management for overload scenarios. The implementation ensures that when system load exceeds capacity, requests are queued and users receive wait time notifications.

## Components

### 1. MessageQueue (`app/message_queue.py`)

Redis-based FIFO queue for handling message overflow during high load.

**Key Features:**
- Queue messages with metadata (phone number, message text, language, timestamp)
- Track queue depth in real-time
- Calculate estimated wait times based on queue depth and average processing time
- Process queued messages in FIFO order
- Update rolling average processing time using exponential moving average

**Key Methods:**
- `queue_message(message)`: Add message to queue
- `dequeue_message()`: Remove and return next message (FIFO)
- `get_queue_depth()`: Get current queue size
- `get_estimated_wait_time()`: Calculate wait time in seconds
- `process_queued_messages(max_messages)`: Process batch of queued messages

### 2. LoadMonitor (`app/load_monitor.py`)

Monitors system load and detects overload conditions based on active requests and response times.

**Key Features:**
- Track active request count
- Record response times in sliding window (last 100 measurements)
- Calculate response time percentiles (p95, p99)
- Detect overload conditions based on thresholds
- Generate wait time notifications in 10 Indian languages

**Thresholds:**
- Max concurrent requests: 100 (per requirement 10.4)
- Max p95 response time: 10 seconds (per requirement 10.1)

**Key Methods:**
- `increment_active_requests()`: Track new request
- `decrement_active_requests()`: Track completed request
- `record_response_time(time)`: Record response time measurement
- `get_load_metrics()`: Get current load metrics
- `is_overloaded()`: Check if system should queue requests
- `get_wait_time_message(wait_seconds, language)`: Generate localized wait notification

### 3. WebhookHandler Integration

The webhook handler now integrates load monitoring and queue management:

**Flow:**
1. Increment active requests counter
2. Check if system is overloaded
3. If overloaded:
   - Queue the message
   - Calculate estimated wait time
   - Send wait notification to user
   - Return queued status
4. If not overloaded:
   - Process message normally
   - Record response time
5. Decrement active requests counter

## Requirements Validation

### Requirement 10.5: Performance and Scalability

✅ **Acceptance Criterion 5:** "WHEN system load exceeds capacity, THE Y-Connect_Bot SHALL queue requests and inform users of expected wait time"

**Implementation:**
- Load detection based on concurrent requests (≥100) or response time (p95 ≥10s)
- Redis-based FIFO queue for overflow messages
- Wait time calculation: `queue_depth × avg_processing_time`
- Multi-language wait notifications sent to users

## Property Tests

### Property 31: Overload Queue Management

**Test Coverage:**
1. Messages are queued successfully when system is overloaded
2. Queue depth is tracked accurately
3. Estimated wait time is calculated correctly
4. Wait time messages are generated in all 10 supported languages
5. Messages are dequeued in FIFO order
6. Queue is empty after all messages are processed

**Additional Tests:**
- Load detection triggers queuing at correct thresholds
- Wait time estimation accuracy based on queue depth and processing time

## Usage Example

```python
from app.load_monitor import LoadMonitor
from app.message_queue import MessageQueue, QueuedMessage
import time

# Initialize components
load_monitor = LoadMonitor()
message_queue = MessageQueue()

# Track request
load_monitor.increment_active_requests()
start_time = time.time()

# Check if overloaded
if load_monitor.is_overloaded():
    # Queue the message
    msg = QueuedMessage(
        message_id="msg123",
        phone_number="+1234567890",
        message_text="Show me farmer schemes",
        language="en",
        queued_at=time.time()
    )
    message_queue.queue_message(msg)
    
    # Get wait time and notify user
    wait_time = message_queue.get_estimated_wait_time()
    wait_msg = load_monitor.get_wait_time_message(wait_time, "en")
    # Send wait_msg to user via WhatsApp
else:
    # Process normally
    pass

# Record response time
response_time = time.time() - start_time
load_monitor.record_response_time(response_time)
load_monitor.decrement_active_requests()
```

## Background Worker (Future Enhancement)

For production deployment, implement a background worker to process queued messages:

```python
import asyncio
from app.message_queue import MessageQueue

async def queue_worker():
    """Background worker to process queued messages"""
    queue = MessageQueue()
    
    while True:
        # Process up to 10 messages per batch
        results = queue.process_queued_messages(max_messages=10)
        
        if results["remaining"] == 0:
            # Queue is empty, wait before checking again
            await asyncio.sleep(5)
        else:
            # More messages to process, continue immediately
            await asyncio.sleep(0.1)
```

## Configuration

The implementation uses existing Redis configuration from `app/config.py`:
- `redis_host`: Redis server hostname
- `redis_port`: Redis server port
- `redis_db`: Redis database number

No additional configuration required.

## Testing

Run property tests:
```bash
pytest tests/test_queue_management_properties.py -v
```

All tests pass with 100 examples per property.

## Performance Characteristics

- **Queue operations**: O(1) for enqueue/dequeue (Redis RPUSH/LPOP)
- **Queue depth**: O(1) lookup (Redis counter)
- **Wait time calculation**: O(1) (simple multiplication)
- **Load metrics**: O(n) where n = response time window size (100)
- **Memory**: O(m) where m = queue depth (messages stored in Redis)

## Multi-Language Support

Wait time notifications are available in 10 Indian languages:
- English (en)
- Hindi (hi)
- Tamil (ta)
- Telugu (te)
- Bengali (bn)
- Marathi (mr)
- Gujarati (gu)
- Kannada (kn)
- Malayalam (ml)
- Punjabi (pa)

Each message includes:
- ⏳ Waiting emoji
- Explanation of high traffic
- Estimated wait time in minutes
- Thank you message for patience
