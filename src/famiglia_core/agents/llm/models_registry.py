"""
src/llm/models_registry.py
--------------------------
Single source of truth for all registered local Ollama model tags and task routing.
All definitions live in models.json — edit that file to add or change models.
Uses only stdlib json, no external dependencies.
"""
import json
import os
from typing import Dict, List

_HERE = os.path.dirname(__file__)
_DEFAULT_CONFIG = os.path.join(_HERE, "models.json")
_CUSTOM_CONFIG = os.getenv("FAMIGLIA_MODELS_CONFIG")

_config_path = _CUSTOM_CONFIG if _CUSTOM_CONFIG and os.path.exists(_CUSTOM_CONFIG) else _DEFAULT_CONFIG

if _CUSTOM_CONFIG and _CUSTOM_CONFIG != _DEFAULT_CONFIG:
    if os.path.exists(_CUSTOM_CONFIG):
        print(f"[Registry] Loading custom model configuration from {_CUSTOM_CONFIG}")
    else:
        print(f"[Registry] WARNING: Custom config {_CUSTOM_CONFIG} not found. Falling back to default.")

with open(_config_path) as _f:
    _cfg = json.load(_f)

# ---------------------------------------------------------------------------
# Model tag constants
# ---------------------------------------------------------------------------

GEMMA4_E2B:       str = _cfg["models"]["gemma4_e2b"]["tag"]        # "gemma4:e2b"
DEEPSEEK_R1_7B:  str = _cfg["models"]["deepseek_r1_7b"]["tag"]   # "deepseek-r1:7b"
QWEN25_CODER_7B: str = _cfg["models"]["qwen2_5_coder_7b"]["tag"] # "qwen2.5-coder:7b"
QWEN2_5_3B:      str = _cfg["models"]["qwen2_5_3b"]["tag"]      # "qwen2.5:3b-instruct-q4_0"
QWEN2_5_3B_INSTR: str = _cfg["models"]["qwen2_5_3b_instruct_q4_k_m"]["tag"]
MISTRAL_7B:      str = _cfg["models"]["mistral_7b"]["tag"]      # "mistral:7b"

# ---------------------------------------------------------------------------
# Task routing  (CHAT / SEARCH / COMPLEX / CODING / TOOLS → model tag)
# ---------------------------------------------------------------------------

TASK_ROUTING: Dict[str, str] = _cfg["tasks"]

# ---------------------------------------------------------------------------
# Defaults  (consumed by LLMClient and startup checks)
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_MODEL:          str = _cfg["defaults"]["ollama_fallback"]    # "gemma4:e2b"
DEFAULT_OLLAMA_FALLBACK_MODEL: str = _cfg["defaults"]["ollama_fallback_key"] # "ollama-gemma4"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_models() -> List[Dict]:
    """Return every registered model entry (key + metadata)."""
    return [{"key": k, **v} for k, v in _cfg["models"].items()]

def get_model_config_by_tag(tag: str) -> Dict:
    """Find model configuration by its Ollama tag (e.g. 'gemma4:e2b')."""
    for entry in _cfg["models"].values():
        if entry.get("tag") == tag:
            return entry
    return {}

