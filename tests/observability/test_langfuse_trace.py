import os
import sys

# Force debug on if not set
os.environ["LANGFUSE_DEBUG"] = "true"

from src.observability.langfuse_util import langfuse_manager

print("Initializing callback handler...")
callback = langfuse_manager.get_callback_handler()

if not callback:
    print("Callback is None. Is Langfuse enabled?")
    sys.exit(1)

print("Testing direct trace via callback's langfuse client...")
try:
    if hasattr(callback, "langfuse"):
        trace = callback.langfuse.trace(
            name="test-trace-direct",
            metadata={"test": "true"}
        )
        print(f"Created trace: {trace.id}")
        
        callback.langfuse.flush()
        print("Flushed successfully!")
    else:
        print("Callback has no langfuse attribute.")
except Exception as e:
    print(f"Error creating/flushing trace: {e}")
