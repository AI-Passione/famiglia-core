from src.agents.kowalski import Kowalski
from src.agents.vito import Vito
from src.db.audit import audit_logger
import os

def test_kowalski():
    print("\n--- Testing Kowalski ---")
    k = Kowalski()
    # Mocking LLM client for testing if needed, but let's see if it works with real client (env vars needed)
    try:
        response = k.analyze_data("Stock market trends for Feb 2026", "Identify volatility patterns")
        print(f"Kowalski Response: {response}")
    except Exception as e:
        print(f"Kowalski error (likely missing API key): {e}")

def test_vito_audit():
    print("\n--- Testing Vito Audit ---")
    v = Vito()
    try:
        # This should trigger audit logging
        v.review_expense(150.0, "New espresso machine for the office")
        print("Vito expense review triggered.")
    except Exception as e:
        print(f"Audit error (likely DB connection): {e}")

if __name__ == "__main__":
    # Ensure env vars are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    test_kowalski()
    test_vito_audit()
