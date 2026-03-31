import subprocess
import sys
import os

def start_backend():
    """Start the FastAPI backend with uvicorn."""
    cmd = [
        "uvicorn", 
        "famiglia_core.command_center.backend.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def smoke_test():
    """Run the LLM smoke tests."""
    cmd = ["pytest", "tests/test_llm.py", "-m", "smoke"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def init_db():
    """Initialize the database."""
    from famiglia_core.db.init_db import init_db as run_init
    run_init()

if __name__ == "__main__":
    # This allow running the file directly if needed
    if len(sys.argv) > 1:
        if sys.argv[1] == "start-backend":
            start_backend()
        elif sys.argv[1] == "smoke-test":
            smoke_test()
        elif sys.argv[1] == "init-db":
            init_db()
