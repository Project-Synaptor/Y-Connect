"""Load monitoring and detection for queue management"""

import time
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
import redis
from redis.exceptions import RedisError

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LoadMetrics:
    """Current system load metrics"""
    active_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    is_overloaded: bool
    timestamp: float


class LoadMonitor:
    """
    Monitors system load and detects overload conditions
    
    Tracks active request count and response time percentiles to determine
    when the system should start queuing requests.
    """
    
    # Redis keys
    ACTIVE_REQUESTS_KEY = "yconnect:active_requests"
    RESPONSE_TIMES_KEY = "yconnect:response_times"
    LOAD_METRICS_KEY = "yconnect:load_metrics"
    
    # Thresholds (from requirement 10.4: handle 100 concurrent sessions)
    MAX_CONCURRENT_REQUESTS = 100
    MAX_RESPONSE_TIME_P95 = 10.0  # 10 seconds per requirement 10.1
    
    # Response time window (keep last 100 measurements)
    RESPONSE_TIME_WINDOW = 100
    
    def __init__(self):
        """Initialize load monitor with Redis connection"""
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
            
            # Initialize active requests counter
            if not self.redis_client.exists(self.ACTIVE_REQUESTS_KEY):
                self.redis_client.set(self.ACTIVE_REQUESTS_KEY, 0)
            
            logger.info("Load monitor initialized")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis for load monitoring: {e}")
            raise
    
    def increment_active_requests(self) -> int:
        """
        Increment the active request counter
        
        Returns:
            Current number of active requests
        """
        try:
            count = self.redis_client.incr(self.ACTIVE_REQUESTS_KEY)
            return count
        except RedisError as e:
            logger.error(f"Failed to increment active requests: {e}")
            return 0
    
    def decrement_active_requests(self) -> int:
        """
        Decrement the active request counter
        
        Returns:
            Current number of active requests
        """
        try:
            count = self.redis_client.decr(self.ACTIVE_REQUESTS_KEY)
            
            # Ensure count doesn't go negative
            if count < 0:
                self.redis_client.set(self.ACTIVE_REQUESTS_KEY, 0)
                return 0
            
            return count
            
        except RedisError as e:
            logger.error(f"Failed to decrement active requests: {e}")
            return 0
    
    def get_active_requests(self) -> int:
        """
        Get the current number of active requests
        
        Returns:
            Number of active requests
        """
        try:
            count = self.redis_client.get(self.ACTIVE_REQUESTS_KEY)
            return int(count) if count else 0
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to get active requests: {e}")
            return 0
    
    def record_response_time(self, response_time: float) -> None:
        """
        Record a response time measurement
        
        Maintains a sliding window of recent response times for percentile calculation.
        
        Args:
            response_time: Response time in seconds
        """
        try:
            # Add to list with timestamp
            entry = f"{time.time()}:{response_time}"
            self.redis_client.rpush(self.RESPONSE_TIMES_KEY, entry)
            
            # Trim to keep only last RESPONSE_TIME_WINDOW entries
            self.redis_client.ltrim(
                self.RESPONSE_TIMES_KEY,
                -self.RESPONSE_TIME_WINDOW,
                -1
            )
            
        except RedisError as e:
            logger.error(f"Failed to record response time: {e}")
    
    def get_response_times(self) -> List[float]:
        """
        Get recent response times from the sliding window
        
        Returns:
            List of response times in seconds
        """
        try:
            entries = self.redis_client.lrange(self.RESPONSE_TIMES_KEY, 0, -1)
            
            # Parse entries (format: "timestamp:response_time")
            response_times = []
            for entry in entries:
                try:
                    _, response_time_str = entry.split(":")
                    response_times.append(float(response_time_str))
                except (ValueError, IndexError):
                    continue
            
            return response_times
            
        except RedisError as e:
            logger.error(f"Failed to get response times: {e}")
            return []
    
    def calculate_percentile(self, values: List[float], percentile: float) -> float:
        """
        Calculate percentile from a list of values
        
        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        
        # Handle edge case
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    def get_load_metrics(self) -> LoadMetrics:
        """
        Get current load metrics
        
        Returns:
            LoadMetrics object with current system load information
        """
        active_requests = self.get_active_requests()
        response_times = self.get_response_times()
        
        # Calculate response time metrics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = self.calculate_percentile(response_times, 95)
            p99_response_time = self.calculate_percentile(response_times, 99)
        else:
            avg_response_time = 0.0
            p95_response_time = 0.0
            p99_response_time = 0.0
        
        # Determine if system is overloaded
        is_overloaded = (
            active_requests >= self.MAX_CONCURRENT_REQUESTS or
            p95_response_time >= self.MAX_RESPONSE_TIME_P95
        )
        
        metrics = LoadMetrics(
            active_requests=active_requests,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            is_overloaded=is_overloaded,
            timestamp=time.time()
        )
        
        # Log if overloaded
        if is_overloaded:
            logger.warning(
                "System overload detected",
                extra={
                    "active_requests": active_requests,
                    "max_concurrent": self.MAX_CONCURRENT_REQUESTS,
                    "p95_response_time": p95_response_time,
                    "max_response_time": self.MAX_RESPONSE_TIME_P95
                }
            )
        
        return metrics
    
    def is_overloaded(self) -> bool:
        """
        Check if system is currently overloaded
        
        Returns:
            True if system should start queuing requests
        """
        metrics = self.get_load_metrics()
        return metrics.is_overloaded
    
    def get_wait_time_message(self, estimated_wait_seconds: int, language: str = "en") -> str:
        """
        Generate a wait time notification message in the user's language
        
        Args:
            estimated_wait_seconds: Estimated wait time in seconds
            language: Language code (en, hi, ta, etc.)
            
        Returns:
            Localized wait time message
        """
        # Convert seconds to minutes for user-friendly display
        wait_minutes = max(1, estimated_wait_seconds // 60)
        
        # Messages in different languages
        messages = {
            "en": f"⏳ We're experiencing high traffic. Your message has been queued. Estimated wait time: {wait_minutes} minute(s). Thank you for your patience!",
            "hi": f"⏳ हम उच्च ट्रैफ़िक का अनुभव कर रहे हैं। आपका संदेश कतार में है। अनुमानित प्रतीक्षा समय: {wait_minutes} मिनट। आपके धैर्य के लिए धन्यवाद!",
            "ta": f"⏳ அதிக போக்குவரத்தை அனுபவித்து வருகிறோம். உங்கள் செய்தி வரிசையில் உள்ளது. மதிப்பிடப்பட்ட காத்திருப்பு நேரம்: {wait_minutes} நிமிடம். உங்கள் பொறுமைக்கு நன்றி!",
            "te": f"⏳ మేము అధిక ట్రాఫిక్‌ను ఎదుర్కొంటున్నాము. మీ సందేశం క్యూలో ఉంది. అంచనా వేసిన నిరీక్షణ సమయం: {wait_minutes} నిమిషం. మీ సహనానికి ధన్యవాదాలు!",
            "bn": f"⏳ আমরা উচ্চ ট্রাফিক অনুভব করছি। আপনার বার্তা সারিতে রয়েছে। আনুমানিক অপেক্ষার সময়: {wait_minutes} মিনিট। আপনার ধৈর্যের জন্য ধন্যবাদ!",
            "mr": f"⏳ आम्ही उच्च रहदारीचा अनुभव घेत आहोत। तुमचा संदेश रांगेत आहे. अंदाजे प्रतीक्षा वेळ: {wait_minutes} मिनिटे. तुमच्या संयमाबद्दल धन्यवाद!",
            "gu": f"⏳ અમે ઉચ્ચ ટ્રાફિકનો અનુભવ કરી રહ્યા છીએ. તમારો સંદેશ કતારમાં છે. અંદાજિત રાહ જોવાનો સમય: {wait_minutes} મિનિટ. તમારી ધીરજ માટે આભાર!",
            "kn": f"⏳ ನಾವು ಹೆಚ್ಚಿನ ಟ್ರಾಫಿಕ್ ಅನ್ನು ಅನುಭವಿಸುತ್ತಿದ್ದೇವೆ. ನಿಮ್ಮ ಸಂದೇಶವು ಸರತಿಯಲ್ಲಿದೆ. ಅಂದಾಜು ಕಾಯುವ ಸಮಯ: {wait_minutes} ನಿಮಿಷ. ನಿಮ್ಮ ತಾಳ್ಮೆಗೆ ಧನ್ಯವಾದಗಳು!",
            "ml": f"⏳ ഞങ്ങൾ ഉയർന്ന ട്രാഫിക് അനുഭവിക്കുന്നു. നിങ്ങളുടെ സന്ദേശം ക്യൂവിലാണ്. കണക്കാക്കിയ കാത്തിരിപ്പ് സമയം: {wait_minutes} മിനിറ്റ്. നിങ്ങളുടെ ക്ഷമയ്ക്ക് നന്ദി!",
            "pa": f"⏳ ਅਸੀਂ ਉੱਚ ਟ੍ਰੈਫਿਕ ਦਾ ਅਨੁਭਵ ਕਰ ਰਹੇ ਹਾਂ। ਤੁਹਾਡਾ ਸੁਨੇਹਾ ਕਤਾਰ ਵਿੱਚ ਹੈ। ਅਨੁਮਾਨਿਤ ਉਡੀਕ ਸਮਾਂ: {wait_minutes} ਮਿੰਟ। ਤੁਹਾਡੇ ਧੀਰਜ ਲਈ ਧੰਨਵਾਦ!"
        }
        
        # Default to English if language not supported
        return messages.get(language, messages["en"])
    
    def reset_metrics(self) -> None:
        """
        Reset all load metrics (for testing/maintenance)
        """
        try:
            self.redis_client.set(self.ACTIVE_REQUESTS_KEY, 0)
            self.redis_client.delete(self.RESPONSE_TIMES_KEY)
            logger.info("Load metrics reset")
        except RedisError as e:
            logger.error(f"Failed to reset metrics: {e}")
