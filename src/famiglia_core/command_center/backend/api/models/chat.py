from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    """Request model for agent chat."""
    message: str = Field(..., description="Message text to send to the agent")
    agent_id: str = Field("alfredo", description="Target agent ID")
    platform: str = Field("web", description="The platform where the message originates")
    platform_user_id: Optional[str] = Field(None, description="The user's ID on the originating platform")
    thread_id: Optional[str] = Field(None, description="Optional thread/conversation ID")
    parent_id: Optional[int] = Field(None, description="The ID of the parent message for threaded replies")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context/metadata")

class ChatResponse(BaseModel):
    """Standard JSON response for non-streaming chat."""
    agent_id: str
    message: str
    conversation_key: str
    status: str = "success"

class StreamChunk(BaseModel):
    """Model for a single chunk in an SSE stream."""
    type: str  # 'intermediate', 'final', 'error'
    content: str
    metadata: Optional[Dict[str, Any]] = None
