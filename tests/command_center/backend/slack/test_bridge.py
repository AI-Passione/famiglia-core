
import requests
import time

def simulate_slack_event():
    url = "http://localhost:8000/api/v1/connections/slack/events/alfredo"
    
    # 1. Simulate Challenge
    challenge_payload = {
        "token": "verification_token",
        "challenge": "test_challenge_123",
        "type": "url_verification"
    }
    print("Testing URL Verification Challenge...")
    resp = requests.post(url, json=challenge_payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    # 2. Simulate App Mention
    mention_payload = {
        "token": "verification_token",
        "team_id": "T12345678",
        "api_app_id": "A12345678",
        "event": {
            "type": "app_mention",
            "user": "U12345678",
            "text": "<@U_BOT_ID> Hello Alfredo, are you there?",
            "ts": f"{time.time()}",
            "channel": "C12345678",
            "event_ts": f"{time.time()}"
        },
        "type": "event_callback",
        "event_id": "Ev12345678",
        "event_time": int(time.time())
    }
    
    print("\nTesting App Mention Event...")
    resp = requests.post(url, json=mention_payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")

if __name__ == "__main__":
    # Running this inside the container or against localhost:8000
    # Since I'm on the host, I'll try localhost:8000
    try:
        simulate_slack_event()
    except Exception as e:
        print(f"Error connecting to API: {e}")
