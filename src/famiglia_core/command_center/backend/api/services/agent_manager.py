from typing import Dict, Any, Optional
from famiglia_core.agents.alfredo import Alfredo
from famiglia_core.agents.vito import Vito
from famiglia_core.agents.riccado import Riccado
from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.tommy import Tommy
from famiglia_core.agents.bella import Bella
from famiglia_core.agents.kowalski import Kowalski

class AgentManager:
    """Manager for agent instances to avoid multiple instantiations."""
    
    def __init__(self):
        self._agents: Dict[str, Any] = {}
        self._agent_classes = {
            "alfredo": Alfredo,
            "vito": Vito,
            "riccado": Riccado,
            "rossini": Rossini,
            "tommy": Tommy,
            "bella": Bella,
            "kowalski": Kowalski,
        }

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get or create an agent instance by its ID."""
        agent_id = agent_id.lower()
        if agent_id in self._agents:
            return self._agents[agent_id]
        
        agent_cls = self._agent_classes.get(agent_id)
        if agent_cls:
            print(f"[AgentManager] Initializing agent: {agent_id}")
            instance = agent_cls()
            self._agents[agent_id] = instance
            return instance
            
        return None

    def list_agents(self) -> list:
        """List all available agent IDs."""
        return list(self._agent_classes.keys())

agent_manager = AgentManager()
