import os
import json
import uuid
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse

from famiglia_core.command_center.backend.api.models.chat import ChatRequest, ChatResponse, StreamChunk
from famiglia_core.command_center.backend.api.services.agent_manager import agent_manager
from famiglia_core.command_center.backend.api.services.user_service import user_service
from famiglia_core.db.agents.context_store import context_store

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

    conversation_key = build_conversation_key(
        platform=request.platform,
        channel=request.metadata.get("channel_id", "web-dashboard"),
        thread=request.thread_id or "new-thread",
        user=request.platform_user_id or "0"
    )

    # 3. Resolve Metadata for Distribution
    metadata = {
        "platform": request.platform,
        "thread_id": request.thread_id,
        "user_id": request.platform_user_id or "0",
        "channel": request.metadata.get("channel_id", "web-dashboard")
    }

    # 4. Log User Message for Web Dashboard persistence
    context_store.log_message(
        agent_name=request.agent_id,
        conversation_key=conversation_key,
        role="user",
        content=request.message,
        sender=sender_context,
        metadata=metadata,
        parent_id=request.parent_id
    )

    # 5. Call Agent
    try:
        response = agent_obj.complete_task(
            request.message,
            sender=sender_context,
            conversation_key=conversation_key,
            metadata=metadata
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
    thread_id: Optional[str] = Query(None),
    parent_id: Optional[int] = Query(None)
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

    # 1. Log User Message for Web Dashboard persistence
    context_store.log_message(
        agent_name=agent_id,
        conversation_key=conversation_key,
        role="user",
        content=message,
        sender=sender_context,
        metadata={
            "platform": platform,
            "thread_id": thread_id,
            "user_id": platform_user_id or "0",
            "channel": "web-dashboard"
        },
        parent_id=parent_id
    )

    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_intermediate(text: str):
            # Put intermediate chunks in the queue thread-safely
            loop.call_soon_threadsafe(
                asyncio.run_coroutine_threadsafe,
                queue.put(StreamChunk(type="intermediate", content=text).model_dump_json()),
                loop
            )

        # Prepare metadata
        metadata = {
            "platform": platform,
            "thread_id": thread_id,
            "user_id": platform_user_id or "0",
            "channel": "web-dashboard"
        }

        # Start agent task in a separate thread to prevent blocking
        task = loop.run_in_executor(
            None, 
            agent_obj.complete_task, 
            message, 
            sender_context, 
            conversation_key, 
            on_intermediate,
            metadata
        )

        # Yield from queue until task is done
        while not task.done() or not queue.empty():
            try:
                # Use a small timeout to keep checking task status
                chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield f"data: {chunk}\n\n"
            except asyncio.TimeoutError:
                continue

        # Final result
        try:
            final_response = await task
            yield f"data: {StreamChunk(type='final', content=final_response).model_dump_json()}\n\n"
        except Exception as e:
            yield f"data: {StreamChunk(type='error', content=str(e)).model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/upload")
async def upload_file(
    request: Request,
    agent_id: str = Query("alfredo")
):
    """Upload a file to be processed by an agent."""
    try:
        # Get filename from headers or default
        filename_header = request.headers.get("x-filename", "uploaded_file.txt")
        
        # Guarantee uniqueness
        file_id = str(uuid.uuid4())[:8]
        filename = f"{file_id}_{filename_header}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Stream the body directly to disk to bypass Starlette's multipart parser
        with open(file_path, "wb") as f:
            async for chunk in request.stream():
                f.write(chunk)
            
        return {
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "message": f"File '{filename_header}' uploaded for {agent_id}. Mention it in your next chat message."
        }
    except Exception as e:
        # Log the error for diagnostics
        print(f"[API] Stream upload error for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/conversations")
async def list_conversations(limit: int = Query(20), offset: int = Query(0)):
    """List recent agent conversations."""
    conversations = context_store.list_conversations(limit=limit, offset=offset)
    # Serialize datetimes for JSON response
    for conv in conversations:
        if conv.get("updated_at"):
            conv["updated_at"] = conv["updated_at"].isoformat()
    return conversations

@router.get("/notifications")
async def get_global_notifications(limit: int = Query(20)):
    """Fetch recent alerts from both the app_notifications table and mission chat messages."""
    # 1. Fetch from the new dedicated table
    app_notifs = context_store.get_app_notifications(limit=limit)
    formatted_notifs = []
    for n in app_notifs:
        n_id = n.get("id")
        n_type = n.get("type") or "info"
        formatted_notifs.append({
            "id": f"app-{n_id}",
            "db_id": n_id,
            "source": n.get("source"),
            "agent_name": n.get("agent_name"),
            "title": n.get("title"),
            "content": n.get("message"),
            "type": n_type,
            "created_at": n.get("created_at").isoformat() if n.get("created_at") else None,
            "metadata": n.get("metadata") or {},
            "task_id": n.get("task_id"),
            "is_app_notif": True
        })

    # 2. Fetch from agent messages (Dual-Stream support for mission metadata)
    messages = context_store.get_global_recent_agent_messages(limit=limit)
    legacy_notifs = []
    for msg in messages:
        # We only care about messages that have mission metadata for the "Bell"
        meta = msg.get("metadata")
        if isinstance(meta, str):
            try: meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError): meta = {}
        
        if meta and meta.get("type") in ("mission_dispatch", "mission_completion"):
            created = msg.get("created_at")
            legacy_notifs.append({
                "id": f"msg-{msg['id']}",
                "db_id": msg["id"],
                "source": "agent",
                "agent_name": msg.get("sender"),
                "title": "Mission Accomplished" if meta.get("type") == "mission_completion" else "Mission Dispatched",
                "content": msg.get("content"),
                "type": "success" if meta.get("status") == "completed" else "info",
                "created_at": created.isoformat() if created else None,
                "metadata": meta,
                "task_id": meta.get("task_id"),
                "is_app_notif": False
            })
    
    # Merge and sort by time
    combined = sorted(formatted_notifs + legacy_notifs, key=lambda x: x["created_at"] or "", reverse=True)
    return combined[:limit]

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    """Mark a notification as read in the app_notifications table."""
    success = context_store.mark_app_notification_as_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}

@router.get("/history")
async def get_chat_history(
    platform: str = Query("web"),
    channel: str = Query("web-dashboard"),
    thread_id: str = Query(...),
    platform_user_id: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Retrieve history for a specific thread/channel from agent_messages."""
    conversation_key = build_conversation_key(
        platform=platform,
        channel=channel,
        thread=thread_id,
        user=platform_user_id or "0"
    )
    
    messages = context_store.get_recent_messages(conversation_key, limit=limit)
    # Ensure datetimes are ISO
    for msg in messages:
        if msg.get("created_at"):
            msg["created_at"] = msg["created_at"].isoformat()
    
    return messages

@router.get("/thread")
async def get_thread_history(
    parent_id: int = Query(...)
):
    """Retrieve history for a specific thread from agent_messages."""
    messages = context_store.get_thread_messages(parent_id)
    # Ensure datetimes are ISO
    for msg in messages:
        if msg.get("created_at"):
            msg["created_at"] = msg["created_at"].isoformat()
    
    return messages
