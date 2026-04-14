import re
import json
from pathlib import Path

def test_dockerfile_node_version_integrity():
    """
    Ensure the Node.js version in the Dockerfile is at least version 20,
    which is required by Vite 6+ to support global CustomEvent.
    """
    project_root = Path(__file__).resolve().parent.parent
    dockerfile_path = project_root / "Dockerfile"
    
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"
    
    content = dockerfile_path.read_text()
    
    # Looking for: FROM node:20-alpine AS frontend-builder
    node_match = re.search(r"FROM node:(\d+)", content)
    assert node_match, "Could not find Node.js version in Dockerfile"
    
    node_version = int(node_match.group(1))
    
    # Cross-check with package.json engines if present
    package_json_path = project_root / "src" / "famiglia_core" / "command_center" / "frontend" / "package.json"
    if package_json_path.exists():
        pkg_data = json.loads(package_json_path.read_text())
        engine_node = pkg_data.get("engines", {}).get("node", ">=20")
        min_version_match = re.search(r"(\d+)", engine_node)
        if min_version_match:
            min_required = int(min_version_match.group(1))
            assert node_version >= min_required, \
                f"Dockerfile Node version ({node_version}) is lower than package.json requirement ({min_required})"

    assert node_version >= 20, f"Node.js version in Dockerfile ({node_version}) must be at least 20 for Vite 6 support."

def test_dockerfile_python_version_integrity():
    """
    Ensure the Python version in the Dockerfile is at least 3.11.
    """
    project_root = Path(__file__).resolve().parent.parent
    dockerfile_path = project_root / "Dockerfile"
    content = dockerfile_path.read_text()
    
    # Looking for: FROM python:3.11-slim
    python_match = re.search(r"FROM python:(\d+\.\d+)", content)
    assert python_match, "Could not find Python version in Dockerfile"
    
    python_version = float(python_match.group(1))
    assert python_version >= 3.11, f"Python version in Dockerfile ({python_version}) must be at least 3.11 for async core support."

def test_dockerfile_port_consistency():
    """
    Ensure the Dockerfile exposes the correct ports for the unified stack.
    """
    project_root = Path(__file__).resolve().parent.parent
    dockerfile_path = project_root / "Dockerfile"
    content = dockerfile_path.read_text()
    
    assert re.search(r"EXPOSE.*\b80\b", content), "Dockerfile is missing EXPOSE 80 (Nginx Gateway)"
    assert re.search(r"EXPOSE.*\b8000\b", content), "Dockerfile is missing EXPOSE 8000 (API Backend)"
