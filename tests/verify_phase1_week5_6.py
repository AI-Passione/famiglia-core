import time
import json
from src.agents.riccado import Riccado
from src.agents.rossini import Rossini
from src.agents.tommy import Tommy
from src.command_center.backend.slack.client import slack_queue, PRIORITY_CRITICAL, PRIORITY_MEDIUM

class MockRedis:
    def __init__(self):
        self.queues = {}
    def rpush(self, key, value):
        if key not in self.queues: self.queues[key] = []
        self.queues[key].append(value)
    def lpop(self, key):
        if key in self.queues and self.queues[key]:
            return self.queues[key].pop(0)
        return None
    def from_url(self, url): return self

def test_agents():
    print("--- Testing Agent Personalities ---")
    riccado = Riccado()
    rossini = Rossini()
    tommy = Tommy()
    
    # Riccado
    print(f"Riccado personality: {riccado.personality[:100]}...")
    riccado.deploy("database")
    
    # Rossini
    print(f"Rossini personality: {rossini.personality[:100]}...")
    rossini.analyze_newsletter("AI is everywhere.")
    
    # Tommy
    print(f"Tommy personality: {tommy.personality[:100]}...")
    tommy.execute_task("Book a flight")

def test_slack_batching():
    print("\n--- Testing Slack Batching with Mock Redis ---")
    # Replace real redis with mock
    slack_queue.redis = MockRedis()
    
    # Start worker in mock mode (no slack token)
    slack_queue.start_worker()
    
    # Critical message (should be immediate)
    print("Enqueuing CRITICAL message...")
    slack_queue.enqueue_message("Vito", "#alerts", "FRAUD DETECTED!", priority=PRIORITY_CRITICAL)
    
    # Medium messages (should be batched)
    print("Enqueuing MEDIUM messages (batching)...")
    slack_queue.enqueue_message("Rossini", "#research", "Insight 1", priority=PRIORITY_MEDIUM)
    slack_queue.enqueue_message("Rossini", "#research", "Insight 2", priority=PRIORITY_MEDIUM)
    
    print("Waiting 35s for batch to flush (Interval is 30s)...")
    time.sleep(35)
    
    slack_queue.stop_worker()

if __name__ == "__main__":
    test_agents()
    test_slack_batching()
