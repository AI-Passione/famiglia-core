import os
import sys
from typing import Optional

# [Monkeypatch for LangChain 0.3 <-> Langfuse v2.x compatibility]
# Langfuse v2's CallbackHandler tries to import `AgentAction` from `langchain.schema.agent`
# which was moved to `langchain_core.agents` in LangChain 0.3.
try:
    import types
    import langchain_core.agents
    import langchain_core.callbacks
    import langchain_core.documents
    import langchain_core.messages
    
    # Create spoofed package structure
    sys.modules['langchain.schema'] = types.ModuleType('langchain.schema')
    sys.modules['langchain.schema.agent'] = langchain_core.agents
    sys.modules['langchain.schema.document'] = langchain_core.documents
    sys.modules['langchain.schema.messages'] = langchain_core.messages
    
    sys.modules['langchain.callbacks'] = types.ModuleType('langchain.callbacks')
    sys.modules['langchain.callbacks.base'] = langchain_core.callbacks
except ImportError:
    pass

from langfuse import Langfuse
from langfuse.callback import CallbackHandler

class LangfuseManager:
    _instance: Optional['LangfuseManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LangfuseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
        
        self.enabled = bool(self.public_key and self.secret_key)
        
        if self.enabled:
            print(f"[Langfuse] Initializing client (Host: {self.host})")
            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
        else:
            print("[Langfuse] Disabled (Missing API keys)")
            self.client = None
            
        self._initialized = True

    def get_callback_handler(self) -> Optional[CallbackHandler]:
        if not self.enabled:
            return None
        return CallbackHandler()
        
    def flush(self):
        if self.client:
            self.client.flush()

langfuse_manager = LangfuseManager()
