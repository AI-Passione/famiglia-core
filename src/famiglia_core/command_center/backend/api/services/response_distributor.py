import logging
from typing import Optional, Dict, Any

from famiglia_core.db.agents.context_store import context_store
from famiglia_core.command_center.backend.comms.slack.client import slack_queue
from famiglia_core.command_center.backend.comms.mattermost.client import mattermost_queue

logger = logging.getLogger(__name__)

class ResponseDistributor:
    """Unified service for agent response dispatching."""
    
    def dispatch(
        self,
        agent_id: str,
        text: str,
        conversation_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Routes the agent's response to the primary Directive Terminal (persistence)
        and mirrors it to external comms if available.
        """
        metadata = metadata or {}
        
        # 1. PRIMARY: Directive Terminal (DB Persistence)
        # This makes it visible in the Web Dashboard conversation history.
        try:
            context_store.log_message(
                role="agent",
                conversation_key=conversation_key,
                agent_name=agent_id,
                content=text,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"[Distributor] Failed to log to DB: {e}")

        # 2. SECONDARY: Slack (Mirror)
        # Only if metadata contains slack_channel
        slack_channel = metadata.get("slack_channel")
        if slack_channel:
            # Check if slack is actually configured
            # We look at agent_tokens or clients in slack_queue
            if slack_queue.clients:
                try:
                    slack_queue.enqueue_message(
                        agent=agent_id,
                        channel=slack_channel,
                        message=text,
                        thread_ts=metadata.get("slack_thread_ts"),
                        priority=metadata.get("priority", 2)
                    )
                except Exception as e:
                    logger.error(f"[Distributor] Failed to enqueue to Slack: {e}")

        # 3. SECONDARY: Mattermost (Mirror)
        mm_channel = metadata.get("mattermost_channel")
        if mm_channel:
            if mattermost_queue.drivers:
                try:
                    mattermost_queue.enqueue_message(
                        agent=agent_id,
                        channel=mm_channel,
                        message=text,
                        priority=metadata.get("priority", 2),
                        root_id=metadata.get("mattermost_root_id")
                    )
                except Exception as e:
                    logger.error(f"[Distributor] Failed to enqueue to Mattermost: {e}")

response_distributor = ResponseDistributor()
