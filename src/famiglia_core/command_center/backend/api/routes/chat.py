import os
import json
import uuid
import asyncio
from typing import Optional, List, Dict, Any, Callable, Annotated
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse

from famiglia_core.command_center.backend.api.models.chat import ChatRequest, ChatResponse, StreamChunk
from famiglia_core.command_center.backend.api.services.agent_manager import agent_manager
from famiglia_core.command_center.backend.api.services.user_service import user_service

router = APIRouter(prefix="/chat", tags=["chat"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.getcwd(), "data/incoming_files")))
os.makedirs(UPLOAD_DIR, exist_ok=True)

def build_conversation_key(platform: str, channel: str, thread: str, user: str) -> str:
    """Consistency check with Slack conversation key format."""
    return f"{platform}:{channel or 'web'}:{thread or 'direct'}:{user or 'unknown'}"

@router.post("/", response_model=ChatResponse)
async def chat_standard(request: ChatRequest):
    """Deliver a message to an agent and wait for the final response."""
    agent_obj = agent_manager.get_agent(request.agent_id)
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found.")

    # 1. Resolve User Identity
    user_info = None
    if request.platform_user_id:
        user_info = user_service.get_user_by_platform_id(request.platform, request.platform_user_id)
    
    if not user_info:
        user_info = user_service.get_don() or {"id": 1, "full_name": "Don Jimmy"}

    sender_name = user_info.get("full_name", "Don Jimmy")
    sender_context = f"{sender_name} ({request.platform_user_id or 'web_user'})"

    # 2. Build Conversation Key
    conversation_key = build_conversation_key(
        platform=request.platform,
        channel=request.metadata.get("channel_id", "web-dashboard"),
        thread=request.thread_id or "new-thread",
        user=request.platform_user_id or str(user_info.get("id", "0"))
    )

    # 3. Call Agent
    try:
        response = agent_obj.complete_task(
            request.message,
            sender=sender_context,
            conversation_key=conversation_key
        )
        return ChatResponse(
            agent_id=request.agent_id,
            message=response,
            conversation_key=conversation_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream")
async def chat_stream(
    message: str = Query(...),
    agent_id: str = Query("alfredo"),
    platform: str = Query("web"),
    platform_user_id: Optional[str] = Query(None),
    thread_id: Optional[str] = Query(None)
):
    """Stream agent thinking process and final response via SSE."""
    agent_obj = agent_manager.get_agent(agent_id)
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    user_info = user_service.get_user_by_platform_id(platform, platform_user_id) if platform_user_id else user_service.get_don()
    sender_name = user_info.get("full_name", "Don Jimmy") if user_info else "Don Jimmy"
    sender_context = f"{sender_name} ({platform_user_id or 'web_user'})"

    conversation_key = build_conversation_key(
        platform=platform,
        channel="web-dashboard",
        thread=thread_id or str(uuid.uuid4()),
        user=platform_user_id or "0"
    )

    async def event_generator():
        queue = asyncio.Queue()

        def on_intermediate(text: str):
            # Put intermediate chunks in the queue
            asyncio.run_coroutine_threadsafe(
                queue.put(StreamChunk(type="intermediate", content=text).json()),
                asyncio.get_event_loop()
            )

        # Start agent task in a separate thread to prevent blocking
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(
            None, 
            agent_obj.complete_task, 
            message, 
            sender_context, 
            conversation_key, 
            on_intermediate
        )

        # Yield from queue until task is done
        while not task.done() or not queue.empty():
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield f"data: {chunk}\n\n"
            except asyncio.TimeoutError:
                continue

        # Final result
        try:
            final_response = await task
            yield f"data: {StreamChunk(type='final', content=final_response).json()}\n\n"
        except Exception as e:
            yield f"data: {StreamChunk(type='error', content=str(e)).json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/upload")
async def upload_file(
    request: Request,
    agent_id: str = Query("alfredo")
):
    """Upload a file to be processed by an agent."""
    try:
        form = await request.form()
        file = form.get("file")
        if not file or not isinstance(file, UploadFile):
            raise HTTPException(status_code=400, detail="Missing 'file' field in multipart form")

        # Guarantee uniqueness
        file_id = str(uuid.uuid4())[:8]
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        return {
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "message": f"File '{file.filename}' uploaded for {agent_id}. Mention it in your next chat message."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
