import time
import json
import os
import redis
import threading
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Callable

# Queue Priorities
PRIORITY_CRITICAL = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

# Batching Intervals (seconds)
BATCH_INTERVALS = {
    PRIORITY_MEDIUM: 30,
    PRIORITY_LOW: 300  # 5 minutes
}

class CommsQueue:
    """Base class for platform-specific (Slack/Mattermost) Redis-backed priority queues."""
    
    def __init__(self, platform: str, redis_url: Optional[str] = None):
        self.platform = platform.lower()
        if not redis_url:
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{host}:{port}"
            
        self.redis = redis.from_url(redis_url)
        
        # Keys
        self.incoming_queue_key = f"{self.platform}:incoming:queue"
        self.outgoing_queue_base = f"{self.platform}:queue:"
        
        self.running = False
        self.worker_thread = None
        
        # Rate limiting and batching (to be managed by children if needed, or here)
        self.last_sent: Dict[str, float] = {}
        self.MIN_INTERVAL = 1.0  # Renamed for compatibility
        self.batches: Dict[tuple, List[dict]] = defaultdict(list)  # Use defaultdict
        self.last_batch_time: Dict[tuple, float] = {}

    def enqueue_message(self, agent: str, channel: str, message: str, priority: int = PRIORITY_MEDIUM, **extra):
        """Puts a message in the priority outgoing queue."""
        payload = {
            "agent": agent,
            "channel": channel,
            "message": message,
            "priority": priority,
            "timestamp": time.time(),
            **extra
        }
        queue_key = f"{self.outgoing_queue_base}{priority}"
        self.redis.rpush(queue_key, json.dumps(payload))

    def _dequeue_next(self) -> Optional[Tuple[str, dict]]:
        """Pops the highest priority message available. Renamed to match client expectations."""
        for priority in [PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]:
            queue_key = f"{self.outgoing_queue_base}{priority}"
            data = self.redis.lpop(queue_key)
            if data:
                return queue_key, json.loads(data)
        return None

    def enqueue_incoming(self, payload: dict):
        """Puts an incoming event in the queue for background processing."""
        self.redis.rpush(self.incoming_queue_key, json.dumps(payload))
        
    def dequeue_incoming(self) -> Optional[dict]:
        """Pops an incoming event from the queue."""
        data = self.redis.lpop(self.incoming_queue_key)
        if data:
            return json.loads(data)
        return None

    def _rate_limit(self, channel: str):
        now = time.time()
        last = self.last_sent.get(channel, 0.0)
        wait_time = self.MIN_INTERVAL - (now - last)
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_sent[channel] = time.time()

    def start_worker(self, target_func: Callable):
        """Starts the background worker thread."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=target_func, daemon=True)
        self.worker_thread.start()

    def stop_worker(self):
        """Stops the background worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
