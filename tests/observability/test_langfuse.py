import os
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

def test_langfuse():
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST")
    
    print(f"Testing Langfuse with:")
    print(f"  Public Key: {public_key}")
    print(f"  Host: {host}")
    
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    # Try manual trace
    print("Creating manual trace...")
    trace = langfuse.trace(name="Test Trace from Assistant")
    print(f"Trace created: {trace.id}")
    
    # Flush
    print("Flushing...")
    langfuse.flush()
    print("Done. Please check the dashboard.")

if __name__ == "__main__":
    test_langfuse()
