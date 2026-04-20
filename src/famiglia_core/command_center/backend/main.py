"""
La Passione Commanding Center API - Entry Point Wrapper
This file serves as a wrapper for the consolidated API located in the api/ nested folder.
"""
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the app from the nested api package
from famiglia_core.command_center.backend.api.main import app

if __name__ == "__main__":
    import uvicorn
    # The Docker setup usually calls this file.
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True, forwarded_allow_ips="*")
